"""
main.py — Application Entry Point
====================================
This is the "front door" of the application. It:
    1. Creates the FastAPI app with OpenAPI docs.
    2. Wires up middleware (payment, error handling).
    3. Registers all route files.
    4. Sets up Redis on startup and tears it down on shutdown.
    5. Adds a /health endpoint for monitoring.

TO RUN LOCALLY:
    uvicorn app.main:app --reload --port 8000

    Then open http://localhost:8000/docs in your browser.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.payment import X402PaymentMiddleware
from app.middleware.cache import init_redis, close_redis, get_redis
from app.models.schemas import HealthResponse

# Import all routers (one per endpoint file).
from app.routes.sold_prices import router as sold_prices_router
from app.routes.yield_estimate import router as yield_router
from app.routes.stamp_duty import router as stamp_duty_router
from app.routes.epc import router as epc_router
from app.routes.crime import router as crime_router
from app.routes.flood_risk import router as flood_risk_router
from app.routes.planning import router as planning_router
from app.routes.council_tax import router as council_tax_router
# New domain routers
from app.routes.weather import router as weather_router
from app.routes.companies import router as companies_router
from app.routes.vehicle import router as vehicle_router
from app.routes.finance import router as finance_router



# =============================================================================
# Logging Setup
# =============================================================================
# Configure Python's logging so all our logger.info() / logger.error() calls
# actually print somewhere (stdout → Railway logs).

def setup_logging():
    """Configure structured logging for the application."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,                  # Railway reads stdout for logs.
    )
    # Quieten noisy libraries.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan (startup & shutdown)
# =============================================================================
# This replaces the old @app.on_event("startup") pattern.
# Code before `yield` runs on startup; code after runs on shutdown.

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle: connect to Redis on startup, disconnect on shutdown."""
    logger.info("Starting UK Data API...")
    await init_redis()
    logger.info("Startup complete — API is ready")
    yield                                   # App is running and serving requests.
    logger.info("Shutting down...")
    await close_redis()
    logger.info("Shutdown complete")


# =============================================================================
# Create the FastAPI Application
# =============================================================================

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    lifespan=lifespan,

    # These URLs control where the interactive docs are served.
    docs_url="/docs",                       # Swagger UI
    redoc_url="/redoc",                     # ReDoc (alternative docs UI)
    openapi_url="/openapi.json",            # Raw OpenAPI schema (for AI agents)

    # Extra metadata shown in /docs.
    contact={
        "name": "UK Property Data API",
        "url": "https://github.com/chetparker/uk-property-api",
    },
    license_info={
        "name": "MIT",
    },

    # Tag descriptions (shown as section headers in /docs).
    openapi_tags=[
        {
            "name": "Property Data",
            "description": (
                "Core endpoints for UK property data. All endpoints require "
                "x402 payment via the X-PAYMENT header."
            ),
        },
        {
            "name": "System",
            "description": "Health checks and status endpoints (free, no payment needed).",
        },
    ],
)


# =============================================================================
# Middleware (runs on every request, in reverse order of registration)
# =============================================================================

# CORS — allow any origin (needed if a web frontend calls your API).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                    # In production, restrict this to your domains.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# x402 Payment — checks for payment on paid endpoints.
app.add_middleware(X402PaymentMiddleware)


# =============================================================================
# Global Error Handler
# =============================================================================
# Catches any unhandled exception so the API returns a clean JSON error
# instead of an ugly HTML stack trace.

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler — returns a clean JSON error."""
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": (
                "An unexpected error occurred. This has been logged. "
                "Please try again or contact support."
            ),
        },
    )


# =============================================================================
# Register Routes
# =============================================================================
# Each router file defines its own paths. We include them all here.

app.include_router(sold_prices_router)
app.include_router(yield_router)
app.include_router(stamp_duty_router)
app.include_router(epc_router)
app.include_router(crime_router)
app.include_router(flood_risk_router)
app.include_router(planning_router)
app.include_router(council_tax_router)
app.include_router(weather_router)
app.include_router(companies_router)
app.include_router(vehicle_router)
app.include_router(finance_router)

from app.mcp_server import mount_mcp
mount_mcp(app)
from app.mcp_server import mount_server_card
mount_server_card(app)


# =============================================================================
# System Endpoints (free, no payment required)
# =============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root URL — redirect humans to the docs."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get('/.well-known/x402.json', include_in_schema=False)
async def well_known_x402():
    return {
        'x402Version': 2,
        'service': {
            'name': 'UK Property Data API',
            'description': 'Land Registry sold prices, rental yields, stamp duty, EPC, crime, flood risk, planning, council tax',
            'version': '1.0.0',
            'homepage': 'https://github.com/chetparker/uk-property-api',
        },
        'payment': {
            'payTo': settings.payment_wallet_address,
            'network': 'eip155:8453',
            'scheme': 'exact',
            'asset': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            'facilitator': 'https://api.cdp.coinbase.com/platform/v2/x402',
        },
        'endpoints': [
            {'method': 'POST', 'path': '/sold-prices', 'price': '0.001', 'description': 'HM Land Registry sold prices'},
            {'method': 'POST', 'path': '/yield-estimate', 'price': '0.001', 'description': 'Rental yield estimates'},
            {'method': 'POST', 'path': '/stamp-duty', 'price': '0.001', 'description': 'SDLT calculator'},
            {'method': 'POST', 'path': '/epc-rating', 'price': '0.001', 'description': 'EPC energy ratings'},
            {'method': 'POST', 'path': '/crime-stats', 'price': '0.001', 'description': 'Crime statistics'},
            {'method': 'POST', 'path': '/flood-risk', 'price': '0.001', 'description': 'Flood risk assessment'},
            {'method': 'POST', 'path': '/planning-applications', 'price': '0.001', 'description': 'Planning applications'},
            {'method': 'POST', 'path': '/council-tax', 'price': '0.001', 'description': 'Council tax data'},
            {'method': 'POST', 'path': '/current-weather', 'price': '0.001', 'description': 'Current weather conditions'},
            {'method': 'POST', 'path': '/weather-forecast', 'price': '0.001', 'description': 'Weather forecast'},
            {'method': 'POST', 'path': '/historical-weather', 'price': '0.002', 'description': 'Historical weather'},
            {'method': 'POST', 'path': '/air-quality', 'price': '0.001', 'description': 'Air quality index'},
            {'method': 'POST', 'path': '/company-search', 'price': '0.001', 'description': 'Search UK companies'},
            {'method': 'POST', 'path': '/company-profile', 'price': '0.001', 'description': 'Company profile'},
            {'method': 'POST', 'path': '/officers', 'price': '0.001', 'description': 'Company officers'},
            {'method': 'POST', 'path': '/filings', 'price': '0.001', 'description': 'Filing history'},
            {'method': 'POST', 'path': '/vehicle-info', 'price': '0.001', 'description': 'Vehicle details'},
            {'method': 'POST', 'path': '/mot-history', 'price': '0.002', 'description': 'MOT test history'},
            {'method': 'POST', 'path': '/tax-status', 'price': '0.001', 'description': 'Vehicle tax status'},
            {'method': 'POST', 'path': '/emissions', 'price': '0.001', 'description': 'Vehicle emissions'},
            {'method': 'POST', 'path': '/interest-rates', 'price': '0.001', 'description': 'BoE base rate'},
            {'method': 'POST', 'path': '/exchange-rates', 'price': '0.001', 'description': 'Exchange rates'},
            {'method': 'POST', 'path': '/inflation', 'price': '0.001', 'description': 'UK CPI inflation'},
            {'method': 'POST', 'path': '/mortgage-calculator', 'price': '0.001', 'description': 'Mortgage calculator'},
        ],
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check",
    description="Returns the API status and whether Redis is connected. Use for uptime monitoring.",
)
async def health_check():
    """Check if the API and its dependencies are healthy."""
    redis_ok = False
    redis_client = get_redis()
    if redis_client:
        try:
            await redis_client.ping()
            redis_ok = True
        except Exception:
            redis_ok = False

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        redis_connected=redis_ok,
    )
