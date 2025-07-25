"""
Thin async wrapper around RugCheck.xyz public API plus threshold comparison.
"""

import asyncio
import httpx
from pumpfun_sniper.config import settings
from pumpfun_sniper.db import log

THRESHOLDS = {
 "holders": 50,
 "lp_locked_pct": 70,
 "creator_balance_pct": 10,
 "market_cap_usd": 2000,
}

async def fetch(mint: str) -> dict:
 """Fetch full token report from RugCheck."""
 url = f"https://api.rugcheck.xyz/v1/tokens/{mint}/report"
 async with httpx.AsyncClient(timeout=10) as cli:
 r = await cli.get(url)
 r.raise_for_status()
 return r.json()

def is_good(tok: dict) -> bool:
 try:
 holders = tok.get("totalHolders", 0)
 lp_locked = tok.get("lpLockedPct") or 0
 supply = tok["token"]["supply"]
 decimals = tok["token"]["decimals"]
 creator_pct = tok.get("creatorBalance", 0) / supply * 100
 market_cap = tok.get("price", 0) * (supply / (10 ** decimals))
 return (
 holders >= THRESHOLDS["holders"]
 and lp_locked >= THRESHOLDS["lp_locked_pct"]
 and creator_pct <= THRESHOLDS["creator_balance_pct"]
 and market_cap >= THRESHOLDS["market_cap_usd"]
 )
 except (KeyError, TypeError, ZeroDivisionError):
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