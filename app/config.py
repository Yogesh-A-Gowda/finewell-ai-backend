from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    secret_key: str = "changeme-secret-key"
    gemini_api_key: str = ""
    database_url: str = "sqlite:///./finwell.db"
    access_token_expire_minutes: int = 10080  # 7 days

    class Config:
        env_file = ".env"


settings = Settings()
