# PumpFun Sniper — Real‑time Solana meme‑coin trader

> **Version 0.2.0** 
---

## Functional Description

`pumpfun_sniper` is an end‑to‑end Python bot that **discovers, evaluates, buys, monitors and sells** brand‑new Solana tokens launched via [pump.fun](https://pump.fun).  
It is designed for **fully‑automated operation** yet exposes a web dashboard—so you can watch candidates, open/closed positions, PnL and live logs scroll by in real time.

### 1  Discovery

* **Helius Geyser WebSocket** (`helius_watcher.py`) subscribes to Pump.fun program logs and receives each mint event in < 1 s.  
* Tokens with duplicate names or created by previously‑blocked rug‑pull addresses are discarded immediately and never polute later filters.

### 2  Candidate vetting

1. **Grace period** — wait `CREATION_GRACE_SEC` (default 20 s) to filter out flash‑rug contracts.  
2. **RugCheck.xyz API** — repeatedly poll until all configurable thresholds (holders, locked LP %, max creator balance %, etc.) pass; otherwise mark as *REJECTED*.  
3. Good candidates move to the *BUY* stage.

### 3  Execution

* **Jupiter quote + swap** endpoints find the best route (Raydium/Orca/ PumpSwap) and return a ready‑to‑sign Base64 transaction.  
* A **Jito Tip** is injected to improve inclusion speed.  
* **Tenacity retry** logic resubmits failed swaps up to `MAX_RETRIES`.

### 4  Position management

* **Birdeye REST** `price_volume/multi` fetches batched price + volume for up to 40 mints per request, minimising CU and REST limits.  
* Every 3 s the bot:
  * Updates a **trailing stop** (`TRAIL_STOP_PCT`),   
  * Closes positions at **take‑profit** (`TAKE_PROFIT_PCT`) or when price ≤ stop,  
  * Optionally exits near **bonding‑curve** limit (≥ `BONDING_EXIT_THRESHOLD`%).  
* Sales use Jupiter again; realised PnL is written to `closed_positions`.

### 5  Persistence and restart safety

All state lives in Postgres tables created at first run:

| Table | Purpose |
|-------|---------|
| `seen_names` | Block repeated token names |
| `blocked_creators` | Addresses that rugged early |
| `candidates` | Mint + metadata + status (NEW, REJECTED, BOUGHT) |
| `open_positions` | Size, avg price, dynamic stop/TP |
| `closed_positions` | Trade history + PnL |
| `logs` | Timestamped INFO/WARN/ERROR rows |

Because the bot reads its own tables on start‑up, you can stop and restart the process without losing track of open trades, blocked creators or seen names.

### 6  Dashboard (FastAPI + SSE)

* One static HTML file (`static/index.html`) + Tabulator.js renders four auto‑scrolling tables.  
* FastAPI streams Server‑Sent Events (`/socket/*`) so rows update live without page reloads.  
* No frontend build pipeline—just open **http://localhost:8000**.

# alternatively set ENV_PATH to another secrets file
# 4. optional simulation mode
# set SIMULATION=true in your .env for paper trading

# Alternatively use SQLite for quick tests:
# DB_DSN=sqlite+aiosqlite:///test.db (install aiosqlite)

# 5. run

## Configuration reference (.env)
| Variable | Purpose | Example
|----------|---------|---------|
| HELIUS_WSS	| WebSocket URL incl. API key	| wss://mainnet.helius-rpc.com/?api-key=***
| RUGCHECK_KEY	| RugCheck.xyz API key	| abc123
| BIRDEYE_KEY	| Birdeye public API key	| xyz789
| RPC_HTTP	| Solana RPC endpoint	| https://api.mainnet-beta.solana.com
| DB_DSN	| Postgres URL	| postgresql+asyncpg://pumpfun_sniper:pwd@localhost/pumpfun_sniper
| BASE_WALLET	| Public key used for swaps	| 3nqrc…Yh3s
| KEYPAIR_PATH	| Path to wallet id.json	| /home/me/.config/solana/id.json

…and many more tunables—see .env.sample for defaults.		

## Quick Start

```bash
# 1. requirements
python -m pip install --user -r requirements.txt

# 2. Postgres (one‑time) (may require sudo -u postgres command prefix)
psql -c "CREATE ROLE pumpfun_sniper LOGIN PASSWORD 'password';"
psql -c "CREATE DATABASE pumpfun_sniper OWNER pumpfun_sniper;"

# 3. config
cp .env.sample .env && nano .env   # fill API keys, wallet path, DB_DSN, etc.

# 4. run
python -m pumpfun_sniper.main
