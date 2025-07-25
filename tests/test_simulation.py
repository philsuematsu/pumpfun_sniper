import types
import os
import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

# stub external deps so importing jupiter works without them
sys.modules["solana.rpc.async_api"] = types.SimpleNamespace(AsyncClient=object)
sys.modules["solders.keypair"] = types.SimpleNamespace(Keypair=object)
sys.modules["solana.transaction"] = types.SimpleNamespace(Transaction=object)
sys.modules["solana.rpc.types"] = types.SimpleNamespace(TxOpts=object)
async def _alog(*a, **k):
    return None
sys.modules["pumpfun_sniper.db"] = types.SimpleNamespace(log=_alog)

for var in [
    "HELIUS_WSS",
    "RUGCHECK_KEY",
    "BIRDEYE_KEY",
    "BASE_WALLET",
    "KEYPAIR_PATH",
    "DB_DSN",
]:
    os.environ.setdefault(var, "test")
os.environ.setdefault("ENV_PATH", "/dev/null")

import pumpfun_sniper.jupiter as jupiter


@pytest.mark.asyncio
async def test_buy_sell_simulation(monkeypatch):
    jupiter.settings.SIMULATION = True

    async def fake_quote(inp, out, amt):
        return {"outAmount": 1000}

    called = {"swap": False, "send": False}

    async def fake_swap(route):
        called["swap"] = True
        return b"tx"

    async def fake_send(raw):
        called["send"] = True
        return "sig"

    monkeypatch.setattr(jupiter, "_quote", fake_quote)
    monkeypatch.setattr(jupiter, "_swap_tx", fake_swap)
    monkeypatch.setattr(jupiter, "_send", fake_send)

    price, sig = await jupiter.buy(1.0, "mint")
    assert sig == "SIMULATED"
    assert price == 1e9 / 1000
    sig2 = await jupiter.sell("mint", 123)
    assert sig2 == "SIMULATED"
    assert not called["swap"] and not called["send"]

