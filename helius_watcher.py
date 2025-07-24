"""
Listens to Pump.fun program logs via Helius Geyser WebSocket and inserts new
token mints as *candidates* in the database. Duplicate names and blocked
creators are filtered server‑side.
"""

import asyncio, base64, json, re, datetime as dt, websockets

from pumpfun_sniper.config import settings
from pumpfun_sniper.db import session_ctx, SeenName, BlockedCreator, Candidate, log

PUMP_FUN_PROGRAM = "Pump11111111111111111111111111111111111111"

# Regex helpers for metadata parsing ------------------------------------------
NAME_RE = re.compile(rb"name\x04(.+?)\x00")
SYMB_RE = re.compile(rb"symbol\x06(.+?)\x00")

async def name_seen(name:str) -> bool:
 async with session_ctx() as s: return await s.get(SeenName, name) is not None

async def creator_blocked(creator:str) -> bool:
 async with session_ctx() as s: return await s.get(BlockedCreator, creator) is not None

async def helius_loop() -> None:
 sub = {
 "jsonrpc":"2.0","id":1,"method":"logsSubscribe",
 "params":[{"mentions":[PUMP_FUN_PROGRAM]},"processed"]
 }
 async with websockets.connect(settings.HELIUS_WSS, ping_interval=20) as ws:
 await ws.send(json.dumps(sub))
 async for raw in ws:
 data=json.loads(raw)
 if "params" not in data:
 continue
 logs=data["params"]["result"]["value"]["logs"]
 # Expect a base64 metadata line → decode
 try:
 b64 = next(l.split(" ")[-1] for l in logs if "base64" in l)
 meta = base64.b64decode(b64)
 name = NAME_RE.search(meta).group(1).decode(errors="ignore")
 sym = SYMB_RE.search(meta).group(1).decode(errors="ignore")
 mint = data["params"]["result"]["value"]["logPubkey"]
 creator = data["params"]["result"]["value"]["accounts"][0]
 except Exception as e:
 await log("WARN", f"metadata parse failed: {e}")
 continue

 if await name_seen(name) or await creator_blocked(creator):
 continue

 async with session_ctx() as s:
 s.add(Candidate(mint=mint, name=name, symbol=sym, creator=creator,
 created_at=dt.datetime.utcnow(), status="NEW"))
 s.add(SeenName(name=name))
 await s.commit()
 await log("INFO", f"NEW candidate {name} ({sym}) {mint[:8]}…")