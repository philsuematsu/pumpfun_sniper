"""
Monitors open positions: updates trailing stops, triggers TP/SL, monitors
bonding‑curve %, and writes PnL to closed_positions.
"""

import asyncio, math, datetime as dt
from pumpfun_sniper.config import settings
from pumpfun_sniper.db import session_ctx, OpenPos, ClosedPos, log
from pumpfun_sniper.birdeye import get_prices
from pumpfun_sniper.bonding import bonding_pct
from pumpfun_sniper.jupiter import sell


async def _close(p: OpenPos, exit_price: float):
    pnl = (exit_price - p.avg_price) * p.qty
    async with session_ctx() as s:
        closed = ClosedPos(
            mint=p.mint,
            qty=p.qty,
            entry_price=p.avg_price,
            exit_price=exit_price,
            pnl=pnl,
            opened_at=p.opened_at,
            closed_at=dt.datetime.utcnow(),
        )
        await s.delete(p)
        s.add(closed)
        await s.commit()
    await log("INFO", f"CLOSED {p.mint[:6]}… PnL={pnl:.4f} SOL")


async def monitor_loop():
    while True:
        async with session_ctx() as s:
            positions = (await s.scalars(OpenPos.__table__.select())).all()
        if not positions:
            await asyncio.sleep(3)
            continue

        prices = await get_prices([p.mint for p in positions])
        for p in positions:
            curr = prices.get(p.mint)
            if not curr:
                continue

            # update trailing stop
            new_stop = max(p.stop_price, curr * (1 - settings.TRAIL_STOP_PCT / 100))
            async with session_ctx() as s:
                pos = await s.get(OpenPos, p.mint)
                pos.stop_price = new_stop
                pos.unrealized_pnl = (curr - pos.avg_price) * pos.qty
                pos.updated_at = dt.datetime.utcnow()
                await s.commit()

            # exit conditions
            if curr <= new_stop or curr >= p.take_profit:
                await sell(p.mint, math.floor(p.qty))
                await _close(p, curr)
                continue
            pct = await bonding_pct(p.mint)
            if pct and pct >= settings.BONDING_EXIT_THRESHOLD:
                await sell(p.mint, math.floor(p.qty))
                await _close(p, curr)
        await asyncio.sleep(3)
