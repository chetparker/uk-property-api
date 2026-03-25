# UK Property Data API — Production Version

## What This Is

A paid API that lets AI agents (and humans) look up UK property data:

| Endpoint | What It Does | Data Source |
|---|---|---|
| `/sold-prices` | Recent sale prices for a postcode | HM Land Registry (free, public) |
| `/yield-estimate` | Estimated rental yield for a postcode | VOA council tax / rental data |
| `/stamp-duty` | UK Stamp Duty (SDLT) calculation | HMRC rules coded in Python |

Payments are handled by the **x402 protocol** — an HTTP-native payment standard
where AI agents pay per-request using crypto wallets.

## How the Code Is Organised

```
uk-property-api/
│
├── app/                        # All application code lives here
│   ├── main.py                 # The "front door" — starts the server
│   ├── config.py               # All settings (read from environment variables)
│   │
│   ├── routes/                 # One file per endpoint (URL path)
│   │   ├── sold_prices.py      # /sold-prices
│   │   ├── yield_estimate.py   # /yield-estimate
│   │   └── stamp_duty.py       # /stamp-duty
│   │
│   ├── services/               # Business logic (the "brains")
│   │   ├── land_registry.py    # Talks to Land Registry SPARQL API
│   │   ├── voa_rental.py       # Rental yield calculations
│   │   └── sdlt.py             # Stamp duty maths
│   │
│   ├── middleware/              # Code that runs BEFORE your endpoints
│   │   ├── payment.py          # x402 payment verification
│   │   ├── rate_limiter.py     # Stops one wallet spamming requests
│   │   └── cache.py            # Redis caching (saves repeat lookups)
│   │
│   └── models/                 # Data shapes (what requests/responses look like)
│       └── schemas.py          # Pydantic validation models
│
├── tests/                      # Automated tests
│   ├── test_sdlt.py            # Stamp duty calculation tests
│   └── test_yield.py           # Yield estimate tests
│
├── Makefile                    # Shortcuts: `make dev`, `make test`, `make deploy`
├── requirements.txt            # Python packages to install
├── Procfile                    # Tells Railway how to start the app
├── railway.toml                # Railway-specific settings
└── .env.example                # Template for your secret settings
```

## Quick Start (Local Development)

```bash
# 1. Install Python 3.11+ then:
make install

# 2. Copy the example env file and fill in your values
cp .env.example .env

# 3. Start the server locally
make dev

# 4. Open the docs in your browser
#    http://localhost:8000/docs
```

## Deploy to Railway

```bash
# 1. Install Railway CLI: https://docs.railway.app/guides/cli
# 2. Login and link your project
railway login
railway link

# 3. Add a Redis plugin in the Railway dashboard
#    (click "New" → "Database" → "Redis")

# 4. Set your environment variables in Railway dashboard:
#    X402_FACILITATOR_URL, PAYMENT_WALLET_ADDRESS, etc.

# 5. Deploy
make deploy
```

## Running Tests

```bash
make test
```

## Environment Variables You Need

| Variable | What It Is | Example |
|---|---|---|
| `REDIS_URL` | Redis connection string | `redis://default:xxx@host:6379` |
| `X402_FACILITATOR_URL` | x402 payment facilitator | `https://x402.org/facilitator` |
| `PAYMENT_WALLET_ADDRESS` | Your wallet (receives payments) | `0xYourAddress...` |
| `RATE_LIMIT_PER_MINUTE` | Max requests per wallet per minute | `30` |
| `CACHE_TTL_SECONDS` | How long to cache results | `3600` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
