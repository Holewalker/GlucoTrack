from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    libre_email: str
    libre_password: str
    libre_patient_id: str = ""
    target_low: int = 60
    target_high: int = 140
    poll_interval_minutes: int = 5
    db_path: str = "/data/glucose.db"

    model_config = {"env_file": ".env"}


settings = Settings()
