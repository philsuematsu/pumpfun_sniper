"""
Examines NEW candidates, waits RugCheck + grace periods, then executes BUYs.
"""

import asyncio, math, datetime as dt
from pumpfun_sniper.config import settings
from pumpfun_sniper.db import session_ctx, Candidate, OpenPos, log
from pumpfun_sniper.rugcheck import wait_until_good
from pumpfun_sniper.jupiter import buy


async def _update_status(mint: str, status: str):
    async with session_ctx() as s:
        cand = await s.get(Candidate, mint)
        cand.status = status
        await s.commit()


async def process_candidate(row: Candidate) -> None:
    await asyncio.sleep(settings.CREATION_GRACE_SEC)
    ok = await wait_until_good(row.mint, timeout_sec=180)
    if not ok:
        await _update_status(row.mint, "REJECTED")
        return

    price_per_token, _sig = await buy(settings.BUY_SIZE_SOL, row.mint)
    qty = settings.BUY_SIZE_SOL / price_per_token
    stop = price_per_token * (1 - settings.TRAIL_STOP_PCT / 100)
    tp = price_per_token * (1 + settings.TAKE_PROFIT_PCT / 100)

    async with session_ctx() as s:
        s.add(
            OpenPos(
                mint=row.mint,
                qty=qty,
                avg_price=price_per_token,
                cost=settings.BUY_SIZE_SOL,
                stop_price=stop,
                take_profit=tp,
                opened_at=dt.datetime.utcnow(),
            )
        )
        await s.commit()

    await _update_status(row.mint, "BOUGHT")
