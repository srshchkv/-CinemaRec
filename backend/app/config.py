from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/cinemarec"
    SECRET_KEY: str = "ec214f0d00dc9c0cc1f3ff04abb39a3f0da1d9a16c5420bd7017220069fb4afd"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    USE_SENTENCE_TRANSFORMERS: bool = False
    MODELS_PATH: str = "../ml/models"
    CSV_PATH: str = "../data_movies_ВКР2.csv"
    TMDB_API_KEY: str | None = None
    OMDB_API_KEY: str | None = None

    model_config = {"env_file": ".env"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
