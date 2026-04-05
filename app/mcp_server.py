"""
mcp_server.py — MCP Agent Discovery for UK Data API
=====================================================
Drop this file into your app/ folder. It adds 3 endpoints:

    /mcp/sse          — SSE transport for MCP clients (Claude, Cursor, etc.)
    /mcp/messages     — JSON-RPC message handler
    /mcp/config       — Static config for directory listings
    /.well-known/mcp.json — Standard discovery endpoint

All 24 of your API endpoints become MCP "tools" that agents can call.

Usage in main.py:
    from app.mcp_server import mount_mcp
    mount_mcp(app)
"""

from __future__ import annotations

import json
import logging
import asyncio
import uuid
from typing import Any

from fastapi import FastAPI, Request
from starlette.responses import StreamingResponse, JSONResponse

logger = logging.getLogger("mcp_server")

BASE_URL = "https://web-production-18a32.up.railway.app"

# ── All 24 endpoints as MCP tools ────────────────────────────────

TOOLS = [
    # ── Property Data (8) ─────────────────────────────────────────
    {
        "name": "get_sold_prices",
        "description": "HM Land Registry sold prices for a UK postcode. Returns address, price paid, date, property type, tenure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string", "description": "UK postcode e.g. SW1A 1AA"},
                "limit": {"type": "integer", "description": "Max results (1-50)", "default": 10}
            },
            "required": ["postcode"]
        },
        "endpoint": "/sold-prices",
        "price": "$0.001"
    },
    {
        "name": "get_yield_estimate",
        "description": "Rental yield estimates for a UK postcode area. Returns average rents, gross/net yields, price-to-rent ratios.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string", "description": "UK postcode"},
                "bedrooms": {"type": "integer", "description": "Number of bedrooms"}
            },
            "required": ["postcode"]
        },
        "endpoint": "/yield-estimate",
        "price": "$0.001"
    },
    {
        "name": "calculate_stamp_duty",
        "description": "UK Stamp Duty Land Tax calculator. Supports first-time buyer relief, additional property surcharge, non-UK resident surcharge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "price": {"type": "number", "description": "Purchase price in GBP"},
                "first_time_buyer": {"type": "boolean", "default": False},
                "additional_property": {"type": "boolean", "default": False}
            },
            "required": ["price"]
        },
        "endpoint": "/stamp-duty",
        "price": "$0.001"
    },
    {
        "name": "get_epc_rating",
        "description": "Energy Performance Certificate ratings for properties near a UK postcode.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string", "description": "UK postcode"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["postcode"]
        },
        "endpoint": "/epc-rating",
        "price": "$0.001"
    },
    {
        "name": "get_crime_stats",
        "description": "Police-recorded crime statistics for a UK postcode area. Returns crime categories, counts, trends.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string", "description": "UK postcode"},
                "months": {"type": "integer", "description": "Months of data", "default": 3}
            },
            "required": ["postcode"]
        },
        "endpoint": "/crime-stats",
        "price": "$0.001"
    },
    {
        "name": "get_flood_risk",
        "description": "Flood risk assessment for a UK postcode. Returns risk levels for rivers, seas, surface water, reservoirs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string", "description": "UK postcode"}
            },
            "required": ["postcode"]
        },
        "endpoint": "/flood-risk",
        "price": "$0.001"
    },
    {
        "name": "get_planning_applications",
        "description": "Planning applications near a UK postcode. Returns application details, status, decisions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string", "description": "UK postcode"},
                "radius_km": {"type": "number", "default": 0.5}
            },
            "required": ["postcode"]
        },
        "endpoint": "/planning-applications",
        "price": "$0.001"
    },
    {
        "name": "get_council_tax",
        "description": "Council tax band and rates for a UK postcode area.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string", "description": "UK postcode"}
            },
            "required": ["postcode"]
        },
        "endpoint": "/council-tax",
        "price": "$0.001"
    },

    # ── Weather Data (4) ──────────────────────────────────────────
    {
        "name": "get_current_weather",
        "description": "Current weather conditions for a UK location. Temperature, humidity, wind, conditions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or UK postcode"}
            },
            "required": ["location"]
        },
        "endpoint": "/current-weather",
        "price": "$0.001"
    },
    {
        "name": "get_weather_forecast",
        "description": "Weather forecast for a UK location. Multi-day forecast with temperature, rain probability, wind.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or UK postcode"},
                "days": {"type": "integer", "description": "Forecast days (1-14)", "default": 7}
            },
            "required": ["location"]
        },
        "endpoint": "/weather-forecast",
        "price": "$0.001"
    },
    {
        "name": "get_historical_weather",
        "description": "Historical weather data for a UK location. Past temperature, rainfall, sunshine hours.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or UK postcode"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"}
            },
            "required": ["location", "date"]
        },
        "endpoint": "/historical-weather",
        "price": "$0.002"
    },
    {
        "name": "get_air_quality",
        "description": "Air quality index for a UK location. PM2.5, PM10, NO2, O3 levels and health advice.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or UK postcode"}
            },
            "required": ["location"]
        },
        "endpoint": "/air-quality",
        "price": "$0.001"
    },

    # ── Companies House (4) ───────────────────────────────────────
    {
        "name": "search_companies",
        "description": "Search UK companies by name. Returns company number, status, registered address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Company name to search"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        },
        "endpoint": "/company-search",
        "price": "$0.001"
    },
    {
        "name": "get_company_profile",
        "description": "Full company profile from Companies House. Registration details, SIC codes, accounts status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "company_number": {"type": "string", "description": "8-digit Companies House number"}
            },
            "required": ["company_number"]
        },
        "endpoint": "/company-profile",
        "price": "$0.001"
    },
    {
        "name": "get_company_officers",
        "description": "Company officers (directors, secretaries). Names, roles, appointment dates, nationality.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "company_number": {"type": "string", "description": "8-digit Companies House number"}
            },
            "required": ["company_number"]
        },
        "endpoint": "/officers",
        "price": "$0.001"
    },
    {
        "name": "get_company_filings",
        "description": "Company filing history. Annual returns, accounts, confirmation statements.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "company_number": {"type": "string", "description": "8-digit Companies House number"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["company_number"]
        },
        "endpoint": "/filings",
        "price": "$0.001"
    },

    # ── Vehicle / DVLA (4) ────────────────────────────────────────
    {
        "name": "get_vehicle_info",
        "description": "Vehicle details from DVLA. Make, model, colour, fuel type, engine size, year.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "registration": {"type": "string", "description": "UK vehicle registration e.g. AB12CDE"}
            },
            "required": ["registration"]
        },
        "endpoint": "/vehicle-info",
        "price": "$0.001"
    },
    {
        "name": "get_mot_history",
        "description": "Full MOT test history. Pass/fail, mileage, advisory items, failure reasons.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "registration": {"type": "string", "description": "UK vehicle registration"}
            },
            "required": ["registration"]
        },
        "endpoint": "/mot-history",
        "price": "$0.002"
    },
    {
        "name": "get_tax_status",
        "description": "Vehicle tax status. Taxed/SORN, tax due date, tax band.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "registration": {"type": "string", "description": "UK vehicle registration"}
            },
            "required": ["registration"]
        },
        "endpoint": "/tax-status",
        "price": "$0.001"
    },
    {
        "name": "get_vehicle_emissions",
        "description": "Vehicle emissions data. CO2 g/km, Euro standard, fuel consumption, ULEZ compliance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "registration": {"type": "string", "description": "UK vehicle registration"}
            },
            "required": ["registration"]
        },
        "endpoint": "/emissions",
        "price": "$0.001"
    },

    # ── Finance / Economics (4) ───────────────────────────────────
    {
        "name": "get_interest_rates",
        "description": "Bank of England base rate. Current rate, historical changes, next decision date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_history": {"type": "boolean", "default": False}
            },
            "required": []
        },
        "endpoint": "/interest-rates",
        "price": "$0.001"
    },
    {
        "name": "get_exchange_rates",
        "description": "GBP exchange rates against major currencies. Live and historical rates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "currency": {"type": "string", "description": "Target currency code e.g. USD, EUR"},
                "date": {"type": "string", "description": "Historical date YYYY-MM-DD (optional)"}
            },
            "required": []
        },
        "endpoint": "/exchange-rates",
        "price": "$0.001"
    },
    {
        "name": "get_inflation",
        "description": "UK CPI inflation data. Current rate, historical trend, RPI comparison.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "months": {"type": "integer", "description": "Months of history", "default": 12}
            },
            "required": []
        },
        "endpoint": "/inflation",
        "price": "$0.001"
    },
    {
        "name": "calculate_mortgage",
        "description": "Mortgage calculator. Monthly payments, total cost, amortisation schedule.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "property_price": {"type": "number", "description": "Property price in GBP"},
                "deposit": {"type": "number", "description": "Deposit in GBP"},
                "interest_rate": {"type": "number", "description": "Annual interest rate %", "default": 4.5},
                "term_years": {"type": "integer", "description": "Mortgage term in years", "default": 25}
            },
            "required": ["property_price", "deposit"]
        },
        "endpoint": "/mortgage-calculator",
        "price": "$0.001"
    },
]


# ══════════════════════════════════════════════════════════════════
# MCP SSE Protocol
# ══════════════════════════════════════════════════════════════════

class MCPSession:
    """Single MCP client session."""

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.queue: asyncio.Queue = asyncio.Queue()

    def _server_info(self) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "uk-data-api", "version": "2.0.0"},
        }

    async def handle(self, msg: dict) -> dict | None:
        method = msg.get("method")
        mid = msg.get("id")

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": mid, "result": self._server_info()}

        if method == "notifications/initialized":
            return None

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "tools": [
                        {
                            "name": t["name"],
                            "description": f"{t['description']} [x402: {t['price']}/call]",
                            "inputSchema": t["inputSchema"],
                        }
                        for t in TOOLS
                    ]
                },
            }

        if method == "tools/call":
            name = msg.get("params", {}).get("name")
            args = msg.get("params", {}).get("arguments", {})
            tool = next((t for t in TOOLS if t["name"] == name), None)

            if not tool:
                return {
                    "jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                }

            import httpx
            url = f"{BASE_URL}{tool['endpoint']}"
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(url, json=args)

                if resp.status_code == 402:
                    return {
                        "jsonrpc": "2.0", "id": mid,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({
                                    "status": "payment_required",
                                    "price": tool["price"],
                                    "x402": resp.json(),
                                    "message": f"Payment of {tool['price']} USDC required. Use x402 protocol.",
                                }, indent=2),
                            }],
                        },
                    }

                return {
                    "jsonrpc": "2.0", "id": mid,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(resp.json(), indent=2)}],
                    },
                }
            except Exception as e:
                logger.error(f"MCP tool call error: {e}")
                return {
                    "jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32603, "message": str(e)},
                }

        return {
            "jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }


# ── Session store ─────────────────────────────────────────────────
_sessions: dict[str, MCPSession] = {}


# ══════════════════════════════════════════════════════════════════
# Mount on FastAPI app
# ══════════════════════════════════════════════════════════════════

def mount_mcp(app: FastAPI):
    """Add MCP endpoints to an existing FastAPI app. Call after routes are registered."""

    @app.get("/mcp/sse", include_in_schema=False)
    async def mcp_sse(request: Request):
        session = MCPSession()
        _sessions[session.session_id] = session

        async def stream():
            endpoint = f"{BASE_URL}/mcp/messages?session_id={session.session_id}"
            yield f"event: endpoint\ndata: {endpoint}\n\n"
            try:
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        msg = await asyncio.wait_for(session.queue.get(), timeout=30)
                        yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            finally:
                _sessions.pop(session.session_id, None)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    @app.post("/mcp/messages", include_in_schema=False)
    async def mcp_messages(request: Request, session_id: str):
        session = _sessions.get(session_id)
        if not session:
            return JSONResponse({"error": "Session not found"}, status_code=404)
        body = await request.json()
        response = await session.handle(body)
        if response:
            await session.queue.put(response)
        return JSONResponse({"ok": True})

    @app.get("/mcp/config", include_in_schema=False)
    async def mcp_config():
        return {
            "name": "uk-data-api",
            "version": "2.0.0",
            "description": "24 UK data endpoints — property, weather, companies, vehicles, finance. Paid via x402.",
            "transport": {"type": "sse", "url": f"{BASE_URL}/mcp/sse"},
            "payment": {"protocol": "x402", "network": "base-sepolia", "asset": "USDC"},
            "tools_count": len(TOOLS),
            "tools": [{"name": t["name"], "description": t["description"], "price": t["price"]} for t in TOOLS],
        }

    @app.get("/.well-known/mcp.json", include_in_schema=False)
    async def well_known_mcp():
        return {
            "mcpServers": {
                "uk-data-api": {
                    "url": f"{BASE_URL}/mcp/sse",
                    "transport": "sse",
                    "description": "UK Data API — 24 endpoints paid via x402",
                }
            }
        }

    logger.info("MCP mounted: /mcp/sse, /mcp/messages, /mcp/config, /.well-known/mcp.json")
