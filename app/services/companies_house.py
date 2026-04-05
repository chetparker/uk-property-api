"""UK company data from Companies House (free API key required)."""
import httpx
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
BASE_URL = "https://api.company-information.service.gov.uk"


def _auth():
    settings = get_settings()
    key = getattr(settings, "companies_house_api_key", "")
    return (key, "") if key else None


async def search_companies(query: str, limit: int = 10) -> dict:
    auth = _auth()
    if not auth:
        return {"query": query, "total_results": 1, "results": [{"company_number": "00000001", "title": f"EXAMPLE {query.upper()} LTD", "company_status": "active", "date_of_creation": "2020-01-15", "address": "1 Example Street, London"}], "note": "Mock data - set COMPANIES_HOUSE_API_KEY"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/search/companies", params={"q": query, "items_per_page": min(limit, 50)}, auth=auth)
        resp.raise_for_status()
        data = resp.json()
    return {"query": query, "total_results": data.get("total_results", 0),
            "results": [{"company_number": i.get("company_number"), "title": i.get("title"), "company_status": i.get("company_status"), "date_of_creation": i.get("date_of_creation"), "address": i.get("address_snippet")} for i in data.get("items", [])]}


async def get_company_profile(company_number: str) -> dict:
    auth = _auth()
    if not auth:
        return {"company_number": company_number, "company_name": "EXAMPLE LTD", "company_status": "active", "sic_codes": ["62012"], "note": "Mock data - set COMPANIES_HOUSE_API_KEY"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/company/{company_number}", auth=auth)
        resp.raise_for_status()
        d = resp.json()
    return {"company_number": d.get("company_number"), "company_name": d.get("company_name"), "company_status": d.get("company_status"),
            "type": d.get("type"), "date_of_creation": d.get("date_of_creation"), "registered_office": d.get("registered_office_address"),
            "sic_codes": d.get("sic_codes", []), "has_charges": d.get("has_charges"), "has_insolvency_history": d.get("has_insolvency_history")}


async def get_officers(company_number: str) -> dict:
    auth = _auth()
    if not auth:
        return {"company_number": company_number, "total_results": 1, "officers": [{"name": "SMITH, John", "officer_role": "director", "appointed_on": "2020-01-15"}], "note": "Mock data"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/company/{company_number}/officers", auth=auth)
        resp.raise_for_status()
        data = resp.json()
    return {"company_number": company_number, "total_results": data.get("total_results", 0),
            "officers": [{"name": i.get("name"), "officer_role": i.get("officer_role"), "appointed_on": i.get("appointed_on"), "resigned_on": i.get("resigned_on")} for i in data.get("items", [])]}


async def get_filing_history(company_number: str, limit: int = 20) -> dict:
    auth = _auth()
    if not auth:
        return {"company_number": company_number, "total_count": 1, "filings": [{"date": "2024-01-15", "type": "AA", "category": "accounts"}], "note": "Mock data"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/company/{company_number}/filing-history", params={"items_per_page": min(limit, 50)}, auth=auth)
        resp.raise_for_status()
        data = resp.json()
    return {"company_number": company_number, "total_count": data.get("total_count", 0),
            "filings": [{"date": i.get("date"), "type": i.get("type"), "category": i.get("category"), "description": i.get("description")} for i in data.get("items", [])]}
