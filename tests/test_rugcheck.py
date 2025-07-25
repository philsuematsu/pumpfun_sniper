import asyncio
import types
import os
import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

for var in [
    "HELIUS_WSS",
    "RUGCHECK_KEY",
    "BIRDEYE_KEY",
    "BASE_WALLET",
    "KEYPAIR_PATH",
    "DB_DSN",
]:
    os.environ.setdefault(var, "test")

import types

sys.modules["pumpfun_sniper.db"] = types.SimpleNamespace(log=lambda *a, **k: None)
import pumpfun_sniper.rugcheck as rugcheck


@pytest.mark.asyncio
async def test_is_good_true():
    token = {
        "totalHolders": 60,
        "lpLockedPct": 80,
        "creatorBalance": 200000000000,
        "price": 1,
        "token": {"decimals": 9},
        "markets": [{"lp": {"tokenSupply": 2000000000000}}],
    }
    assert rugcheck.is_good(token)


@pytest.mark.asyncio
async def test_is_good_false():
    token = {
        "totalHolders": 10,
        "lpLockedPct": 10,
        "creatorBalance": 100000000000,
        "price": 0.5,
        "token": {"decimals": 9},
        "markets": [{"lp": {"tokenSupply": 100000000000}}],
    }
    assert not rugcheck.is_good(token)


@pytest.mark.asyncio
async def test_wait_until_good_succeeds(monkeypatch):
    good = {
        "totalHolders": 60,
        "lpLockedPct": 80,
        "creatorBalance": 200000000000,
        "price": 1,
        "token": {"decimals": 9},
        "markets": [{"lp": {"tokenSupply": 2000000000000}}],
    }
    bad = {
        "totalHolders": 10,
        "lpLockedPct": 10,
        "creatorBalance": 100000000000,
        "price": 0.5,
        "token": {"decimals": 9},
        "markets": [{"lp": {"tokenSupply": 100000000000}}],
    }

    calls = 0

    async def fake_fetch(mint: str):
        nonlocal calls
        calls += 1
        return good if calls > 1 else bad

    async def fake_log(level, msg):
        return None

    monkeypatch.setattr(rugcheck, "fetch", fake_fetch)
    monkeypatch.setattr(rugcheck, "log", fake_log)
    monkeypatch.setattr(rugcheck.settings, "RUG_RECHECK_SEC", 1)

    assert await rugcheck.wait_until_good("mint", timeout_sec=2)


@pytest.mark.asyncio
async def test_wait_until_good_timeout(monkeypatch):
    bad = {
        "totalHolders": 10,
        "lpLockedPct": 10,
        "creatorBalance": 100000000000,
        "price": 0.5,
        "token": {"decimals": 9},
        "markets": [{"lp": {"tokenSupply": 100000000000}}],
    }

    async def fake_fetch(mint: str):
        return bad

    async def fake_log(level, msg):
        return None

    monkeypatch.setattr(rugcheck, "fetch", fake_fetch)
    monkeypatch.setattr(rugcheck, "log", fake_log)
    monkeypatch.setattr(rugcheck.settings, "RUG_RECHECK_SEC", 1)

    assert not await rugcheck.wait_until_good("mint", timeout_sec=0)
