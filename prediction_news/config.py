from pathlib import Path

from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    kalshi_key_id: str = ""
    kalshi_private_key_path: str = "kalshi_private.key"

    cors_origins: str = "http://localhost:5173"
    kalshi_events_limit: int = 10
    rss_lookback_hours: int = 48
    feed_domains: str = "politics"

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "extra": "ignore"}

    @property
    def cors_origins_list(self) -> list[str]:
        return self.cors_origins.split(",")

    @property
    def feed_domains_list(self) -> list[str]:
        return self.feed_domains.split(",")


settings = Settings()
