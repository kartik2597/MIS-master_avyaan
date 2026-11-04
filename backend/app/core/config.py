from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_SECRET_KEY = "change-me-to-a-long-random-secret"
DEFAULT_DB_PASSWORD = "postgres"
LOCAL_ENVIRONMENTS = {"development", "dev", "local", "test"}
# Local development origins only. Add any LAN or production origin through
# APP_CORS_ORIGINS in .env instead of hardcoding it here.
DEFAULT_CORS_ORIGINS = (
    "http://localhost:8080,http://127.0.0.1:8080,"
    "http://localhost:5173,http://127.0.0.1:5173"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = Field(
        "MIS Master",
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
        DEFAULT_DB_PASSWORD,
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
        DEFAULT_SECRET_KEY,
        validation_alias="APP_SECRET_KEY",
        min_length=16,
    )

    ALGORITHM: str = Field(
        "HS256",
        validation_alias="APP_ALGORITHM",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        30,
        validation_alias="APP_ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    # A refresh token lets the browser get a new access token without asking for
    # the password again, so people are not signed out every 30 minutes.
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        7,
        gt=0,
        validation_alias="APP_REFRESH_TOKEN_EXPIRE_DAYS",
    )

    LOG_LEVEL: str = Field(
        "INFO",
        validation_alias="APP_LOG_LEVEL",
    )

    STORAGE_DIR: str = Field(
        "storage",
        validation_alias="APP_STORAGE_DIR",
    )

    MAX_UPLOAD_SIZE_MB: int = Field(
        25,
        gt=0,
        validation_alias="APP_MAX_UPLOAD_SIZE_MB",
    )

    # When true, an upload by an ADMIN or MIS user is imported as soon as it passes
    # validation, with no separate "Process report" step.
    AUTO_PROCESS_UPLOADS: bool = Field(
        True,
        validation_alias="APP_AUTO_PROCESS_UPLOADS",
    )

    # When true, a report row whose Employee ID is not in the employee master is
    # skipped and listed on the Upload History page. Off by default because reports
    # normally add unknown agents to the master (employee_sync).
    REJECT_UNKNOWN_EMPLOYEES: bool = Field(
        False,
        validation_alias="APP_REJECT_UNKNOWN_EMPLOYEES",
    )

    # Build the daily (every day), weekly (Mondays) and monthly (1st of the month)
    # MIS workbooks into storage/reports once the server clock passes this hour.
    AUTO_REPORTS_ENABLED: bool = Field(
        True,
        validation_alias="APP_AUTO_REPORTS_ENABLED",
    )

    AUTO_REPORTS_HOUR: int = Field(
        6,
        ge=0,
        le=23,
        validation_alias="APP_AUTO_REPORTS_HOUR",
    )

    # Optional: email the scheduled reports. Leave SMTP_HOST or REPORT_EMAIL_TO empty
    # to only save them to storage/reports. REPORT_EMAIL_TO is comma-separated.
    SMTP_HOST: str = Field("", validation_alias="APP_SMTP_HOST")
    SMTP_PORT: int = Field(587, validation_alias="APP_SMTP_PORT")
    SMTP_USER: str = Field("", validation_alias="APP_SMTP_USER")
    SMTP_PASSWORD: str = Field("", validation_alias="APP_SMTP_PASSWORD")
    SMTP_FROM: str = Field("", validation_alias="APP_SMTP_FROM")
    REPORT_EMAIL_TO: str = Field("", validation_alias="APP_REPORT_EMAIL_TO")

    # Comma-separated list, e.g. "http://localhost:8080,https://mis.example.com".
    CORS_ORIGINS: str = Field(
        DEFAULT_CORS_ORIGINS,
        validation_alias="APP_CORS_ORIGINS",
    )

    @model_validator(mode="after")
    def reject_insecure_defaults_outside_development(self) -> "Settings":
        if self.ENVIRONMENT.strip().lower() in LOCAL_ENVIRONMENTS:
            return self

        problems = []
        if self.SECRET_KEY == DEFAULT_SECRET_KEY or len(self.SECRET_KEY) < 32:
            problems.append("APP_SECRET_KEY must be a random value of 32+ characters")
        if self.POSTGRES_PASSWORD == DEFAULT_DB_PASSWORD:
            problems.append("POSTGRES_PASSWORD must not be the default")
        if self.DEBUG:
            problems.append("APP_DEBUG must be false")
        if problems:
            raise ValueError(
                f"Insecure settings for environment '{self.ENVIRONMENT}': "
                + "; ".join(problems)
            )
        return self

    @computed_field
    @property
    def CORS_ORIGIN_LIST(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @computed_field
    @property
    def REPORT_EMAIL_LIST(self) -> list[str]:
        return [a.strip() for a in self.REPORT_EMAIL_TO.split(",") if a.strip()]

    @computed_field
    @property
    def REPORTS_PATH(self) -> Path:
        return self.STORAGE_PATH / "reports"

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
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()