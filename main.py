"""
App entry‑point. Spins up DB, Helius watcher, candidate evaluator,
position monitor, and the FastAPI dashboard (Uvicorn in a background thread).
"""

import os
import sys
import signal
import asyncio, uvicorn

from pumpfun_sniper.db import init, async_session, Candidate
from pumpfun_sniper.helius_watcher import helius_loop
from pumpfun_sniper.strategy import process_candidate
from pumpfun_sniper.executor import monitor_loop
from pumpfun_sniper.dashboard import app
from pumpfun_sniper.config import settings


def _exit_handler(signum, frame):
    """Exit immediately on Ctrl-C."""
    print("Received SIGINT, exiting...", flush=True)
    sys.exit(0)

signal.signal(signal.SIGINT, _exit_handler)

async def _eval_loop():
    while True:
        async with async_session() as s:
            cands = (
                await s.scalars(
                    Candidate.__table__.select().where(Candidate.status == "NEW")
                )
            ).all()
            for c in cands:
                await process_candidate(c)
        await asyncio.sleep(5)


async def main():
    print(f"[DEBUG] DEBUG={settings.DEBUG}")

    await init()
    tasks = [
        helius_loop(),
        _eval_loop(),
        monitor_loop(),
        asyncio.to_thread(
            uvicorn.run,
            app,
            host="0.0.0.0",
            port=8000,
            log_level="warning",
        ),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
