"""
Batched price polling (≤40 tokens per HTTP call) via Birdeye REST endpoint.
"""

import httpx
from pumpfun_sniper.config import settings

ENDPOINT = "https://public-api.birdeye.so/defi/price_volume/multi"

async def get_prices(mints: list[str]) -> dict[str, float]:
 if not mints:
 return {}
 prices: dict[str, float] = {}
 async with httpx.AsyncClient(timeout=10) as cli:
 for i in range(0, len(mints), 40):
 chunk = mints[i : i + 40]
 params = [("network", "solana")] + [("address", m) for m in chunk]
 r = await cli.get(ENDPOINT, params=params,
 headers={"X-API-KEY": settings.BIRDEYE_KEY})
 r.raise_for_status()
 data = r.json()["data"]
 prices.update({row["address"]: row["price_usd"] for row in data})
 return prices