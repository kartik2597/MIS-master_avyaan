from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = Field(
        "MIS Master 2.O",
        validation_alias="APP_PROJECT_NAME",
    )

    ENVIRONMENT: str = Field(
        "development",
        validation_alias="APP_ENVIRONMENT",
    )

    DEBUG: bool = Field(
        False,
        validation_alias="APP_DEBUG",
    )

    POSTGRES_SERVER: str = Field(
        "localhost",
        validation_alias=AliasChoices(
            "POSTGRES_SERVER",
            "APP_DB_HOST",
        ),
    )

    POSTGRES_PORT: int = Field(
        5432,
        validation_alias=AliasChoices(
            "POSTGRES_PORT",
            "APP_DB_PORT",
        ),
    )

    POSTGRES_USER: str = Field(
        "postgres",
        validation_alias=AliasChoices(
            "POSTGRES_USER",
            "APP_DB_USER",
        ),
    )

    POSTGRES_PASSWORD: str = Field(
        "postgres",
        validation_alias=AliasChoices(
            "POSTGRES_PASSWORD",
            "APP_DB_PASSWORD",
        ),
    )

    POSTGRES_DB: str = Field(
        "mis_master",
        validation_alias=AliasChoices(
            "POSTGRES_DB",
            "APP_DB_NAME",
        ),
    )

    SECRET_KEY: str = Field(
        "change-me-to-a-long-random-secret",
        validation_alias="APP_SECRET_KEY",
        min_length=16,
    )

    ALGORITHM: str = Field(
        "HS256",
        validation_alias="APP_ALGORITHM",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        60,
        validation_alias="APP_ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    LOG_LEVEL: str = Field(
        "INFO",
        validation_alias="APP_LOG_LEVEL",
    )

    STORAGE_DIR: str = Field(
        "storage",
        validation_alias="APP_STORAGE_DIR",
    )

    @computed_field
    @property
    def STORAGE_PATH(self) -> Path:
        storage_path = Path(self.STORAGE_DIR)

        if storage_path.is_absolute():
            return storage_path

        return BASE_DIR / storage_path

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()