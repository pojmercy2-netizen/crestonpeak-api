import time
import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

# In-memory cache: avoid hitting CoinGecko more than once per 30 seconds
_cache: dict = {"price": 0, "change24h": 0, "fetched_at": 0}
CACHE_TTL = 30  # seconds

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
)


@router.get("/btc-price")
async def get_btc_price():
    """Proxy CoinGecko BTC price with server-side caching to avoid CORS and rate limits."""
    now = time.time()

    # Return cached value if still fresh
    if now - _cache["fetched_at"] < CACHE_TTL and _cache["price"] > 0:
        return JSONResponse(
            content={"price": _cache["price"], "change24h": _cache["change24h"]},
            headers={"Cache-Control": "public, max-age=30"},
        )

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(COINGECKO_URL)

        if resp.status_code == 200:
            data = resp.json()
            price = data.get("bitcoin", {}).get("usd", 0)
            change24h = data.get("bitcoin", {}).get("usd_24h_change", 0)
            _cache["price"] = price
            _cache["change24h"] = change24h
            _cache["fetched_at"] = now
            return JSONResponse(
                content={"price": price, "change24h": change24h},
                headers={"Cache-Control": "public, max-age=30"},
            )
        else:
            # Rate limited or error — serve stale cache if available
            return JSONResponse(
                content={"price": _cache["price"], "change24h": _cache["change24h"]},
                headers={"Cache-Control": "public, max-age=10"},
            )

    except Exception:
        # Network failure — serve stale cache
        return JSONResponse(
            content={"price": _cache["price"], "change24h": _cache["change24h"]},
            status_code=200,
        )
