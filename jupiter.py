"""
Buy / sell helpers via Jupiter quote + swap endpoints with an optional Jito tip.
"""

import asyncio, base64, httpx, json
from tenacity import retry, stop_after_attempt, wait_exponential

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.transaction import Transaction
from solana.rpc.types import TxOpts

from pumpfun_sniper.config import settings
from pumpfun_sniper.db import log
from pumpfun_sniper.debug import dbg

_SOL = "So11111111111111111111111111111111111111112"
_keypair: Keypair | None = None


def kp() -> Keypair:
    global _keypair
    if _keypair is None:
        with open(settings.KEYPAIR_PATH, "r") as fh:
            _keypair = Keypair.from_json(json.load(fh))
    return _keypair


async def _quote(inp: str, out: str, amount: int) -> dict:
    async with httpx.AsyncClient(timeout=10) as cli:
        params = {
            "inputMint": inp,
            "outputMint": out,
            "amount": amount,
            "slippageBps": settings.SLIPPAGE_BPS,
        }
        dbg(f"JUPITER QUOTE {settings.JUPITER_QUOTE} {params}")
        r = await cli.get(settings.JUPITER_QUOTE, params=params)
        dbg(f"JUPITER QUOTE RESPONSE {r.status_code} {r.text[:200]}")
        r.raise_for_status()
        return r.json()["data"][0]


async def _swap_tx(route: dict) -> bytes:
    async with httpx.AsyncClient(timeout=10) as cli:
        payload = {
            "quoteResponse": route,
            "userPublicKey": str(kp().pubkey()),
            "wrapAndUnwrapSol": True,
            "priorityFeeLamports": {"jitoTipLamports": settings.JITO_TIP_LAMPORTS},
        }
        dbg(f"JUPITER SWAP {settings.JUPITER_SWAP} {payload}")
        r = await cli.post(settings.JUPITER_SWAP, json=payload)
        dbg(f"JUPITER SWAP RESPONSE {r.status_code} {r.text[:200]}")
        r.raise_for_status()
        return base64.b64decode(r.json()["swapTransaction"])


@retry(
    stop=stop_after_attempt(settings.MAX_RETRIES),
    wait=wait_exponential(multiplier=settings.BACKOFF_SEC),
)
async def _send(raw: bytes) -> str:
    tx = Transaction.from_bytes(raw)
    tx.sign(kp())
    async with AsyncClient(settings.RPC_HTTP) as rpc:
        dbg(f"RPC send_transaction to {settings.RPC_HTTP}")
        sig = (
            await rpc.send_transaction(
                tx,
                kp(),
                opts=TxOpts(skip_preflight=True, max_retries=settings.MAX_RETRIES),
            )
        ).value
        dbg(f"RPC transaction signature {sig}")
        await rpc.confirm_transaction(sig, commitment="confirmed")
        return sig


# Public helpers --------------------------------------------------------------
async def buy(sol_amount: float, mint: str) -> tuple[float, str]:
    lamports = int(sol_amount * 1e9)
    route = await _quote(_SOL, mint, lamports)
    price = lamports / float(route["outAmount"])
    if settings.SIMULATION:
        await log("INFO", f"SIM BUY {mint[:6]}… {sol_amount} SOL")
        return price, "SIMULATED"
    raw = await _swap_tx(route)
    sig = await _send(raw)
    await log("INFO", f"BUY {mint[:6]}… {sol_amount} SOL sig={sig}")
    return price, sig


async def sell(mint: str, qty: int) -> str:
    route = await _quote(mint, _SOL, qty)
    if settings.SIMULATION:
        await log("INFO", f"SIM SELL {mint[:6]}… qty={qty}")
        return "SIMULATED"
    raw = await _swap_tx(route)
    sig = await _send(raw)
    await log("INFO", f"SELL {mint[:6]}… qty={qty} sig={sig}")
    return sig
