import os
import datetime as dt
from pumpfun_sniper.config import settings


def dbg(msg: str) -> None:
    if settings.DEBUG == "verbose":
        ts = dt.datetime.utcnow().isoformat()
        print(f"[DEBUG] {ts} {msg}")
