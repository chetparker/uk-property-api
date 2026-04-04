"""
payment.py — x402 Payment Protocol Middleware (FIXED for v2)
"""

import httpx
import logging
import json
import base64

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import get_settings

logger = logging.getLogger(__name__)

USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

FREE_ENDPOINTS = {
    "/", "/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico",
}


class X402PaymentMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        path = request.url.path.rstrip("/") or "/"

        if path in FREE_ENDPOINTS:
            return await call_next(request)

        payment_header = (
            request.headers.get("X-PAYMENT")
            or request.headers.get("PAYMENT-SIGNATURE")
        )

        if not payment_header:
            logger.info(f"402 Payment Required for {request.method} {path}")
            return _build_402_response(settings, request)

        is_valid = await _verify_payment(
            payment_header=payment_header,
            settings=settings,
            request=request,
        )

        if not is_valid:
            logger.warning(f"Invalid payment for {request.method} {path}")
            return JSONResponse(
                status_code=402,
                content={"error": "payment_invalid", "detail": "Payment verification failed."},
            )

        logger.info(f"Payment verified for {request.method} {path}")
        return await call_next(request)


def _build_402_response(settings, request: Request) -> JSONResponse:
    price_usd = float(settings.price_per_request)
    amount = str(int(price_usd * 1_000_000))

    body = {
        "x402Version": 2,
        "error": "Payment required",
        "resource": {"url": str(request.url)},
        "accepts": [
            {
                "scheme": "exact",
                "network": "eip155:84532",
                "asset": USDC_BASE_SEPOLIA,
                "amount": amount,
                "payTo": settings.payment_wallet_address,
                "maxTimeoutSeconds": 300,
                "extra": {
                    "name": "USDC",
                    "version": "2",
                },
            }
        ],
    }

    encoded = base64.b64encode(json.dumps(body).encode()).decode()

    return JSONResponse(
        status_code=402,
        content=body,
        headers={"PAYMENT-REQUIRED": encoded},
    )



def _decode_payload(payment_header: str) -> dict:
    """Decode base64 payment payload to dict for facilitator."""
    try:
        decoded = json.loads(base64.b64decode(payment_header))
        return decoded
    except Exception:
        return {"raw": payment_header}


async def _verify_payment(payment_header: str, settings, request: Request) -> bool:
    facilitator_url = settings.x402_facilitator_url

    if not facilitator_url:
        logger.warning("No facilitator URL — accepting all payments (dev mode)")
        return True

    price_usd = float(settings.price_per_request)
    amount = str(int(price_usd * 1_000_000))

    payment_requirements = {
        "scheme": "exact",
        "network": "eip155:84532",
        "asset": USDC_BASE_SEPOLIA,
        "amount": amount,
        "payTo": settings.payment_wallet_address,
        "maxTimeoutSeconds": 300,
        "extra": {"name": "USDC", "version": "2"},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{facilitator_url}/verify",
                json={
                    "paymentPayload": _decode_payload(payment_header),
                    "paymentRequirements": payment_requirements,
                },
            )

            if response.status_code == 200:
                result = response.json()
                is_valid = result.get("valid", False) or result.get("isValid", False)
                if is_valid:
                    logger.info(f"Payment verified: {result}")
                return is_valid
            else:
                logger.error(f"Facilitator returned {response.status_code}: {response.text}")
                return False

    except httpx.TimeoutException:
        logger.error("Payment verification timed out")
        return False
    except Exception as e:
        logger.error(f"Payment verification failed: {e}")
        return False
