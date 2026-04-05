"""UK finance data from Bank of England + ECB (free, no API key)."""
import httpx
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
BOE_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
FX_URL = "https://api.frankfurter.app"


async def fetch_interest_rates(months: int = 12) -> dict:
    end = datetime.now()
    start = end - timedelta(days=months * 30)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BOE_URL, params={"csv.x": "yes", "Datefrom": start.strftime("%d/%b/%Y"), "Dateto": end.strftime("%d/%b/%Y"), "SeriesCodes": "IUDBEDR", "CSVF": "TN", "UsingCodes": "Y"})
            resp.raise_for_status()
        rates = []
        for line in resp.text.strip().split("\n")[1:]:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try: rates.append({"date": parts[0].strip().strip(\'"\'), "rate": float(parts[1].strip().strip(\'"\'))})
                except: pass
        return {"current_rate": rates[-1]["rate"] if rates else None, "source": "Bank of England", "history": rates[-24:]}
    except:
        return {"current_rate": 4.5, "source": "fallback estimate", "history": []}


async def fetch_exchange_rates(base: str = "GBP", targets: list = None) -> dict:
    if targets is None:
        targets = ["USD", "EUR", "JPY", "CHF", "AUD", "CAD"]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{FX_URL}/latest", params={"from": base.upper(), "to": ",".join(targets)})
            resp.raise_for_status()
            data = resp.json()
        return {"base": data.get("base"), "date": data.get("date"), "rates": data.get("rates", {}), "source": "ECB"}
    except:
        return {"base": base, "rates": {"USD": 1.27, "EUR": 1.17}, "source": "fallback"}


async def fetch_inflation(months: int = 24) -> dict:
    end = datetime.now()
    start = end - timedelta(days=months * 30)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BOE_URL, params={"csv.x": "yes", "Datefrom": start.strftime("%d/%b/%Y"), "Dateto": end.strftime("%d/%b/%Y"), "SeriesCodes": "D7BT", "CSVF": "TN", "UsingCodes": "Y"})
            resp.raise_for_status()
        data = []
        for line in resp.text.strip().split("\n")[1:]:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try: data.append({"date": parts[0].strip().strip(\'"\'), "cpi_pct": float(parts[1].strip().strip(\'"\'))})
                except: pass
        return {"current_cpi": data[-1]["cpi_pct"] if data else None, "source": "Bank of England / ONS", "history": data}
    except:
        return {"current_cpi": 3.0, "source": "fallback estimate", "history": []}


def calculate_mortgage(price: float, deposit: float, rate: float, years: int, interest_only: bool = False) -> dict:
    loan = price - deposit
    ltv = (loan / price) * 100
    mr = rate / 100 / 12
    months = years * 12
    if interest_only:
        mp = loan * mr
        total = (mp * months) + loan
    else:
        mp = loan * (mr * (1 + mr) ** months) / ((1 + mr) ** months - 1) if mr > 0 else loan / months
        total = mp * months
    return {"property_price": price, "deposit": deposit, "loan": round(loan, 2), "ltv_pct": round(ltv, 1),
            "rate_pct": rate, "term_years": years, "type": "Interest Only" if interest_only else "Repayment",
            "monthly_payment": round(mp, 2), "total_cost": round(total, 2), "total_interest": round(total - loan, 2)}
