"""
payment.py — x402 Payment Protocol Middleware
===============================================
Implements the x402 HTTP payment protocol. This is the mechanism that lets
AI agents pay for API calls using crypto wallets.

WHAT IS x402?
    HTTP status code 402 means "Payment Required". The x402 protocol builds
    on this: when a client makes a request without paying, the server returns
    a 402 response that says "here's how to pay me". The client's wallet
    software then makes the payment and retries the request with proof
    of payment in the headers.

    Flow:
        1. Agent calls GET /sold-prices?postcode=SW1A+1AA (no payment)
        2. Server returns 402 with payment instructions:
           {
             "x402Version": 1,
             "accepts": [{
               "scheme": "exact",
               "network": "base-sepolia",
               "maxAmountRequired": "1000000",
               "resource": "https://yourapi.com/sold-prices",
               "payTo": "0xYourWallet",
               "extra": { "facilitatorUrl": "https://x402.org/facilitator" }
             }]
           }
        3. Agent's wallet pays and retries with X-PAYMENT header.
        4. Server verifies payment with the facilitator and returns data.

WHO VERIFIES PAYMENTS?
    The "facilitator" is a trusted third-party service that confirms the
    payment was made on-chain. We POST the payment proof to them and they
    tell us if it's valid.

PAID vs FREE ENDPOINTS:
    - FREE: /health, /docs, /openapi.json (so agents can discover the API)
    - PAID: /sold-prices, /yield-estimate, /stamp-duty
"""

import httpx
import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import get_settings

logger = logging.getLogger(__name__)

# Endpoints that don't require payment (anyone can access these).
FREE_ENDPOINTS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
}


class X402PaymentMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that intercepts every request and checks for payment.

    Middleware runs BEFORE your endpoint code. Think of it as a bouncer at
    the door — it checks your "ticket" (payment proof) before letting you
    into the "club" (the API endpoint).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process each incoming request:
            1. If it's a free endpoint → let it through.
            2. If it has a valid X-PAYMENT header → verify and let through.
            3. If not → return 402 Payment Required with instructions.
        """
        settings = get_settings()

        # --- Step 1: Check if this endpoint is free ---
        path = request.url.path.rstrip("/") or "/"
        if path in FREE_ENDPOINTS:
            return await call_next(request)

        # --- Step 2: Check for payment header ---
        payment_header = request.headers.get("X-PAYMENT")

        if not payment_header:
            # No payment — tell the client how to pay.
            logger.info(f"402 Payment Required for {request.method} {path}")
            return _build_402_response(settings, request)

        # --- Step 3: Verify the payment with the facilitator ---
        is_valid = await _verify_payment(
            payment_header=payment_header,
            facilitator_url=settings.x402_facilitator_url,
            request=request,
        )

        if not is_valid:
            logger.warning(f"Invalid payment for {request.method} {path}")
            return JSONResponse(
                status_code=402,
                content={
                    "error": "payment_invalid",
                    "detail": "Payment verification failed. Check your payment and retry.",
                },
            )

        # Payment is valid — let the request through to the endpoint.
        logger.info(f"Payment verified for {request.method} {path}")
        return await call_next(request)


def _build_402_response(settings, request: Request) -> JSONResponse:
    """
    Build the x402-compliant 402 response that tells the client how to pay.

    This response body follows the x402 specification, so any x402-compatible
    wallet (like those built into AI agents) can parse it and make payment
    automatically.
    """
    return JSONResponse(
        status_code=402,
        content={
            "x402Version": 1,
            "accepts": [
                {
                    "scheme": "exact",
                    "network": "base-sepolia",
                    "maxAmountRequired": settings.price_per_request,
                    "resource": str(request.url),
                    "payTo": settings.payment_wallet_address,
                    "extra": {
                        "name": "UK Property Data API",
                        "description": (
                            f"Access to {request.url.path} endpoint. "
                            f"Price: ${settings.price_per_request} per request."
                        ),
                        "facilitatorUrl": settings.x402_facilitator_url,
                    },
                }
            ],
        },
        headers={
            # The X-PAYMENT-REQUIRED header is part of the x402 spec.
            "X-PAYMENT-REQUIRED": "true",
        },
    )


async def _verify_payment(
    payment_header: str,
    facilitator_url: str,
    request: Request,
) -> bool:
    """
    Verify a payment token with the x402 facilitator service.

    The facilitator checks on-chain that the payment was actually made.

    Args:
        payment_header:  The X-PAYMENT header value from the client.
        facilitator_url: URL of the x402 facilitator service.
        request:         The original request (for context).

    Returns:
        True if the payment is valid, False otherwise.
    """
    # If no facilitator URL is configured, skip verification (dev mode).
    if not facilitator_url:
        logger.warning("No facilitator URL configured — accepting all payments (dev mode)")
        return True

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{facilitator_url}/verify",
                json={
                    "payment": payment_header,
                    "resource": str(request.url),
                },
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("valid", False)
            else:
                logger.error(
                    f"Facilitator returned {response.status_code}: {response.text}"
                )
                return False

    except httpx.TimeoutException:
        logger.error("Payment verification timed out")
        return False
    except Exception as e:
        logger.error(f"Payment verification failed: {e}")
        return False
