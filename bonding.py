"""
Fetch bonding‑curve percentage from Moralis' PumpFun endpoint.
"""

import httpx
from pumpfun_sniper.config import settings

async def bonding_pct(mint: str) -> float | None:
 if not settings.MORALIS_KEY:
 return None
 url = f"https://solana-gateway.moralis.com/pumpfun/bonding/{mint}"
 async with httpx.AsyncClient(timeout=10) as cli:
 r = await cli.get(url, headers={"X-API-Key": settings.MORALIS_KEY})
 r.raise_for_status()
 return r.json().get("bonding_curve_pct")