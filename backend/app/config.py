from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ProductHub"
    environment: str = "development"
    database_url: str = "sqlite:///./producthub.db"
    api_prefix: str = "/api/v1"


settings = Settings()
