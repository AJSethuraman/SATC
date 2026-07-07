"""Typed application configuration loaded from environment / .env.

All paths are resolved relative to ``data_dir`` so the whole app can be pointed
at a different data root (e.g. in tests) by overriding one setting.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The value shipped in .env.example. SEC calls are refused until it is changed,
# because SEC fair-access rules expect a User-Agent that identifies the caller.
PLACEHOLDER_USER_AGENT = "stock-helper dev (you@example.com)"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    sec_user_agent: str = ""
    stock_helper_db_url: str = ""
    # Price data (Stooq, NON-CANONICAL) is on by default: the valuation engine
    # needs a price for margin-of-safety and market multiples. Intrinsic DCF and
    # fundamental factors still work with it off. Every price-derived output is
    # labeled non-canonical. Set ENABLE_PRICE_DATA=false to disable.
    enable_price_data: bool = True
    log_level: str = "INFO"
    sec_cache_ttl_hours: float = 24.0
    data_dir: Path = Path("data")

    @property
    def db_url(self) -> str:
        if self.stock_helper_db_url:
            return self.stock_helper_db_url
        return f"sqlite:///{self.data_dir / 'db' / 'stock_helper.db'}"

    @property
    def raw_sec_dir(self) -> Path:
        return self.data_dir / "raw" / "sec"

    @property
    def price_cache_dir(self) -> Path:
        return self.data_dir / "cache" / "prices"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    def ensure_dirs(self) -> None:
        for path in (
            self.raw_sec_dir,
            self.price_cache_dir,
            self.reports_dir,
            self.data_dir / "db",
        ):
            path.mkdir(parents=True, exist_ok=True)

    def require_sec_user_agent(self) -> str:
        """Return the configured SEC User-Agent or raise with a helpful message."""
        ua = self.sec_user_agent.strip().strip('"')
        if not ua or ua == PLACEHOLDER_USER_AGENT:
            raise RuntimeError(
                "SEC_USER_AGENT is not configured. Copy .env.example to .env and set "
                'SEC_USER_AGENT="Your Name (you@example.com)" — SEC fair-access rules '
                "require an identifying User-Agent."
            )
        return ua


@lru_cache
def get_settings() -> Settings:
    return Settings()
