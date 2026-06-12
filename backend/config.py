from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ladderlab:ladderlab@localhost:5432/ladderlab"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()