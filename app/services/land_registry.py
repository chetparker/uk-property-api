"""
land_registry.py — HM Land Registry SPARQL Client
===================================================
Fetches sold-price data from the HM Land Registry's public Linked Data API.

WHAT IS SPARQL?
    SPARQL (pronounced "sparkle") is a query language for databases that store
    data as "triples" (subject → predicate → object). It's like SQL but for
    the Semantic Web. The Land Registry publishes all England & Wales property
    transactions in this format, free to query.

ENDPOINT:
    https://landregistry.data.gov.uk/landregistry/query

HOW THIS WORKS:
    1. We build a SPARQL query that filters by postcode.
    2. We POST it to the Land Registry's public endpoint.
    3. We parse the JSON results into our Pydantic models.

IMPORTANT NOTES:
    - This API is FREE and public. No API key needed.
    - It can be slow (2–5 seconds) — that's why we cache results in Redis.
    - The data covers England & Wales only (not Scotland or N. Ireland).
    - Data lags about 2–3 months behind actual sales.
"""

import httpx
import logging
from app.models.schemas import SoldPriceRecord

# Set up a logger for this file. Messages will appear in your Railway logs.
logger = logging.getLogger(__name__)

# The Land Registry's public SPARQL endpoint.
LAND_REGISTRY_ENDPOINT = "https://landregistry.data.gov.uk/landregistry/query"


def _build_sparql_query(postcode: str, limit: int) -> str:
    """
    Build a SPARQL query to find recent sold prices for a postcode.

    The query selects:
        - Full address (street, locality, town)
        - Sale price
        - Transaction date
        - Property type (Detached, Semi-Detached, Terraced, Flat)
        - Whether it was a new build

    Results are ordered by date (newest first).

    Args:
        postcode: UK postcode, e.g. "SW1A 1AA"
        limit:    Max number of results to return

    Returns:
        A SPARQL query string ready to send to the API.
    """

    # Normalise the postcode: uppercase, strip extra spaces.
    clean_postcode = postcode.strip().upper()

    return f"""
    PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
    PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>

    SELECT ?address ?price ?date ?propertyType ?newBuild
    WHERE {{
        ?txn lrppi:pricePaid ?price ;
             lrppi:transactionDate ?date ;
             lrppi:propertyAddress ?addr ;
             lrppi:propertyType ?propertyType ;
             lrppi:newBuild ?newBuild .

        ?addr lrcommon:postcode "{clean_postcode}" .

        # Build a readable address from the parts.
        ?addr lrcommon:paon ?paon .
        OPTIONAL {{ ?addr lrcommon:saon ?saon . }}
        OPTIONAL {{ ?addr lrcommon:street ?street . }}
        OPTIONAL {{ ?addr lrcommon:town ?town . }}

        BIND(
            CONCAT(
                IF(BOUND(?saon), CONCAT(?saon, ", "), ""),
                ?paon,
                IF(BOUND(?street), CONCAT(", ", ?street), ""),
                IF(BOUND(?town), CONCAT(", ", ?town), "")
            ) AS ?address
        )
    }}
    ORDER BY DESC(?date)
    LIMIT {limit}
    """


def _parse_property_type(uri: str) -> str:
    """
    Convert a Land Registry property type URI to a human-readable string.

    Example:
        "http://landregistry.data.gov.uk/def/common/semi-detached"
        → "Semi-Detached"
    """
    # The type is the last segment of the URI.
    type_slug = uri.rsplit("/", 1)[-1] if "/" in uri else uri

    # Map known slugs to readable labels.
    type_map = {
        "detached": "Detached",
        "semi-detached": "Semi-Detached",
        "terraced": "Terraced",
        "flat-maisonette": "Flat",
    }
    return type_map.get(type_slug, type_slug.replace("-", " ").title())


async def fetch_sold_prices(postcode: str, limit: int = 10) -> list[SoldPriceRecord]:
    """
    Fetch sold-price records from HM Land Registry.

    This is an async function — it doesn't block the server while waiting
    for the Land Registry to respond.

    Args:
        postcode: UK postcode to search.
        limit:    Maximum results (default 10).

    Returns:
        A list of SoldPriceRecord objects.

    Raises:
        httpx.HTTPStatusError: If the Land Registry returns an error.
        Exception: On network failures or unexpected issues.
    """
    query = _build_sparql_query(postcode, limit)

    logger.info(f"Querying Land Registry for postcode: {postcode} (limit={limit})")

    # Use httpx for async HTTP requests (like requests, but non-blocking).
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            LAND_REGISTRY_ENDPOINT,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()   # Raises an exception for 4xx/5xx codes.

    data = response.json()
    bindings = data.get("results", {}).get("bindings", [])

    logger.info(f"Land Registry returned {len(bindings)} results for {postcode}")

    # Convert each SPARQL result row into our Pydantic model.
    records = []
    for row in bindings:
        try:
            records.append(SoldPriceRecord(
                address=row["address"]["value"],
                price=int(float(row["price"]["value"])),
                date=row["date"]["value"][:10],          # "2024-03-15T00:00:00" → "2024-03-15"
                property_type=_parse_property_type(row["propertyType"]["value"]),
                new_build=row["newBuild"]["value"].lower() == "true",
            ))
        except (KeyError, ValueError) as e:
            # If one record is malformed, skip it instead of crashing.
            logger.warning(f"Skipping malformed record: {e}")
            continue

    return records
