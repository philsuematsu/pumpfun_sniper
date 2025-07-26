"""
FastAPI server with Server‑Sent Events (SSE) endpoints plus a static SPA.
"""

import asyncio, json, datetime as dt, pathlib
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from fastapi.staticfiles import StaticFiles
from pumpfun_sniper.db import async_session, Candidate, OpenPos, ClosedPos, LogEntry

BASE = pathlib.Path(__file__).parent
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
HTML = (BASE / "static" / "index.html").read_text()

@app.get("/", response_class=HTMLResponse)
async def index(): return HTML

def _row(obj, cols): # serialize SQLAlchemy row
    d = {}
    for c in cols:
        v = getattr(obj, c)
        if isinstance(v, dt.datetime):
            v = v.isoformat(sep=" ", timespec="seconds")
        d[c] = v
    return d

async def _stream(model, cols, order_col):
    while True:
        async with async_session() as s:
            rows = (
                await s.scalars(
                    model.__table__.select().order_by(order_col.desc())
                )
            ).all()
        yield "data:" + json.dumps([_row(r, cols) for r in rows]) + "\n\n"
        await asyncio.sleep(2)

@app.get("/socket/candidates")
async def sse_candidates():
    return EventSourceResponse(
        _stream(
            Candidate,
            ["mint", "name", "status", "created_at"],
            Candidate.created_at,
        )
    )

@app.get("/socket/open")
async def sse_open():
 return EventSourceResponse(_stream(OpenPos,
 ["mint","qty","avg_price","stop_price","take_profit","updated_at"], OpenPos.updated_at))

@app.get("/socket/closed")
async def sse_closed():
 return EventSourceResponse(_stream(ClosedPos,
 ["mint","qty","pnl","closed_at"], ClosedPos.closed_at))

@app.get("/socket/logs")
async def sse_logs():
 return EventSourceResponse(_stream(LogEntry,
 ["ts","level","msg"], LogEntry.ts))