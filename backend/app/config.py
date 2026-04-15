from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_expire_minutes: int = 480
    prometheus_url: str = "http://localhost:9090"


settings = Settings()
