from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    JWT_SECRET: str = Field(...)   # <-- default "dummy"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "clinic"        # en minúsculas si así creaste el user
    DB_PASSWORD: str = "superseguro"
    DB_NAME: str = "clinic_hub"

    @property
    def async_database_url(self) -> str:
        return (f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4")

    class Config:
        env_file = ".env"

# settings = Settings()
settings = Settings()  # type: ignore[call-arg]
