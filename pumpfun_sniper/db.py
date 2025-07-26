"""
Async SQLAlchemy setup + helper CRUD shortcuts.
Tables are created automatically on first run (no Alembic needed).
"""

import os
import datetime as dt
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, mapped_column, Mapped
from sqlalchemy import String, DateTime, Float, Integer, select
from pumpfun_sniper.config import settings
from pumpfun_sniper.debug import dbg

engine = create_async_engine(
    settings.DB_DSN,
    echo=os.getenv("DEBUG") == "verbose",
    pool_size=10,
    max_overflow=20,
)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


# ──────────────────────────────────────────────────────────────────────────────
class SeenName(Base):
    __tablename__ = "seen_names"
    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    first_seen: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
    )


class BlockedCreator(Base):
    __tablename__ = "blocked_creators"
    creator: Mapped[str] = mapped_column(String(44), primary_key=True)
    blocked_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
    )


class Candidate(Base):
    __tablename__ = "candidates"
    mint: Mapped[str] = mapped_column(String(44), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    symbol: Mapped[str] = mapped_column(String(16))
    creator: Mapped[str] = mapped_column(String(44))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="NEW")


class OpenPos(Base):
    __tablename__ = "open_positions"
    mint: Mapped[str] = mapped_column(String(44), primary_key=True)
    qty: Mapped[float] = mapped_column(Float)
    avg_price: Mapped[float] = mapped_column(Float)
    cost: Mapped[float] = mapped_column(Float)
    stop_price: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    opened_at: Mapped[dt.datetime] = mapped_column(DateTime)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow
    )
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)


class ClosedPos(Base):
    __tablename__ = "closed_positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mint: Mapped[str] = mapped_column(String(44))
    qty: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float)
    opened_at: Mapped[dt.datetime] = mapped_column(DateTime)
    closed_at: Mapped[dt.datetime] = mapped_column(DateTime)


class LogEntry(Base):
    __tablename__ = "logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    level: Mapped[str] = mapped_column(String(8))
    msg: Mapped[str] = mapped_column(String(512))


# ─────────────────────────── general helpers ──────────────────────────────────
async def init() -> None:
    """Create tables if they do not yet exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class session_ctx:
    """Async context‑manager wrapper for a session."""

    def __init__(self):
        self._ctx = async_session()

    async def __aenter__(self):
        return self._ctx

    async def __aexit__(self, *e):
        await self._ctx.close()


# tiny logger ------------------------------------------------------------------
async def log(level: str, msg: str):
    async with session_ctx() as s:
        s.add(LogEntry(level=level[:8], msg=msg[:510]))
        await s.commit()
    dbg(f"SQL LOG {level} {msg}")
