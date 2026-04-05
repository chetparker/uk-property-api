"""Company data endpoints."""
import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from app.services.companies_house import search_companies, get_company_profile, get_officers, get_filing_history

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Company Data"])

class SearchRequest(BaseModel):
    query: str = Field(..., examples=["Tesco"])
    limit: int = Field(default=10, ge=1, le=50)

class CompanyRequest(BaseModel):
    company_number: str = Field(..., examples=["00445790"])

class FilingsRequest(BaseModel):
    company_number: str = Field(..., examples=["00445790"])
    limit: int = Field(default=20, ge=1, le=50)

@router.post("/company-search", summary="Search UK companies by name")
async def company_search(body: SearchRequest):
    try: return await search_companies(body.query, body.limit)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/company-profile", summary="Full company profile")
async def company_profile(body: CompanyRequest):
    try: return await get_company_profile(body.company_number)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/officers", summary="Company officers and directors")
async def company_officers(body: CompanyRequest):
    try: return await get_officers(body.company_number)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@router.post("/filings", summary="Company filing history")
async def company_filings(body: FilingsRequest):
    try: return await get_filing_history(body.company_number, body.limit)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
