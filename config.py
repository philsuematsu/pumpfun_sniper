from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
 # ─── External endpoints ────────────────────────────────────────────────
 HELIUS_WSS: str # wss://mainnet.helius-rpc.com/?api-key=…
 RUGCHECK_KEY: str
 BIRDEYE_KEY: str
 RPC_HTTP: str = "https://api.mainnet-beta.solana.com"
 JUPITER_QUOTE: str = "https://quote-api.jup.ag/v6/quote"
 JUPITER_SWAP: str = "https://quote-api.jup.ag/v6/swap"
 MORALIS_KEY: str | None = None # optional (bonding check)

 # ─── Wallet and auth ──────────────────────────────────────────────────
 BASE_WALLET: str
 KEYPAIR_PATH: str # filesystem path to id.json (array of ints)

 # ─── Trading parameters (runtime‑tunable via .env) ────────────────────
 BUY_SIZE_SOL: float = 0.01
 SLIPPAGE_BPS: int = 75
 JITO_TIP_LAMPORTS: int = 2_000_000
 TAKE_PROFIT_PCT: float = 200.0
 TRAIL_STOP_PCT: float = 35.0
 BONDING_EXIT_THRESHOLD: float = 90.0
 CREATION_GRACE_SEC: int = 20
 RUG_RECHECK_SEC: int = 30
 MIGRATION_WAIT_SEC: int = 15

 # ─── Persistence / retries ────────────────────────────────────────────
 DB_DSN: str
 MAX_RETRIES: int = 3
 BACKOFF_SEC: float = 0.5

 model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings() # import this everywhere