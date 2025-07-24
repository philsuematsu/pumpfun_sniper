"""
Thin async wrapper around RugCheck.xyz public API plus threshold comparison.
"""

import httpx, asyncio
from pumpfun_sniper.config import settings
from pumpfun_sniper.db import log

THRESHOLDS = {
 "holders": 50,
 "lp_locked_pct": 70,
 "creator_balance_pct": 10,
 "market_cap_usd": 2000,
}

async def fetch(mint: str) -> dict:
 url = f"https://api.rugcheck.xyz/v1/token/{mint}"
 async with httpx.AsyncClient(timeout=10) as cli:
 r = await cli.get(url, headers={"Authorization": f"Bearer {settings.RUGCHECK_KEY}"})
 r.raise_for_status()
 return r.json()

def is_good(tok: dict) -> bool:
 try:
 return (
 tok["holders"] >= THRESHOLDS["holders"]
 and tok["lp_locked_pct"] >= THRESHOLDS["lp_locked_pct"]
 and tok["creator_balance_pct"] <= THRESHOLDS["creator_balance_pct"]
 and tok["market_cap_usd"] >= THRESHOLDS["market_cap_usd"]
 )
 except (KeyError, TypeError):
 return False

async def wait_until_good(mint: str, timeout_sec: int) -> bool:
 """Poll RugCheck until thresholds met or timeout."""
 for _ in range(timeout_sec // settings.RUG_RECHECK_SEC):
 tok = await fetch(mint)
 if is_good(tok):
 return True
 await asyncio.sleep(settings.RUG_RECHECK_SEC)
 await log("INFO", f"RugCheck failed for {mint[:8]}… after {timeout_sec}s")
 return False