"""App entry-point. Spins up DB, Helius watcher, candidate evaluator,
position monitor and the FastAPI dashboard."""

import os
import sys
import signal
import threading
import asyncio
import uvicorn

from pumpfun_sniper.db import init, async_session, Candidate
from pumpfun_sniper.helius_watcher import helius_loop
from pumpfun_sniper.strategy import process_candidate
from pumpfun_sniper.executor import monitor_loop
from pumpfun_sniper.dashboard import app
from pumpfun_sniper.config import settings


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


async def main() -> None:
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _exit_handler() -> None:
        """Exit cleanly on Ctrl-C."""
        print("Received SIGINT, exiting...", flush=True)
        stop.set()

    loop.add_signal_handler(signal.SIGINT, _exit_handler)

    print(f"[DEBUG] DEBUG={settings.DEBUG}")

    await init()

    # Run FastAPI dashboard in a daemon thread so process can exit immediately
    thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": "0.0.0.0", "port": 8000, "log_level": "warning"},
        daemon=True,
    )
    thread.start()

    tasks = [
        asyncio.create_task(helius_loop()),
        asyncio.create_task(_eval_loop()),
        asyncio.create_task(monitor_loop()),
    ]

    await stop.wait()
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
