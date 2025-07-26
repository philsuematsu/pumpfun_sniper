import os
import datetime as dt

def dbg(msg: str) -> None:
    if os.getenv("DEBUG") == "verbose":
        ts = dt.datetime.utcnow().isoformat()
        print(f"[DEBUG] {ts} {msg}")
