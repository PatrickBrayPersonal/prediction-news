from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    kalshi_api_key: str = ""
    kalshi_private_key_path: str = "kalshi_private.key"

    cors_origins: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> list[str]:
        return self.cors_origins.split(",")


settings = Settings()
