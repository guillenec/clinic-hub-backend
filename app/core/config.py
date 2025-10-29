# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore")

    JWT_SECRET: str = Field(...)   # <-- default "dummy"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DB_HOST: str 
    DB_PORT: int 
    DB_USER: str      # en minúsculas si así creaste el user
    DB_PASSWORD: str 
    DB_NAME: str
    
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    MAX_UPLOAD_MB: int = 2
    MEDIA_FOLDER_SIGNATURES: str = "clinic-hub/signatures"
    MEDIA_FOLDER_STAMPS: str = "clinic-hub/stamps"
    MEDIA_FOLDER_AVATARS: str = "clinic-hub/avatars"   # NUEVO (usuarios)
    MEDIA_FOLDER_PHOTOS: str = "clinic-hub/photos"     # NUEVO (doctores/pacientes)

     # --- Zoom OAuth (añadí esto) ---
    ZOOM_CLIENT_ID: str
    ZOOM_CLIENT_SECRET: str
    ZOOM_REDIRECT_URL: str
    ZOOM_BASE_URL: str 
    ZOOM_API: str 
    APP_NAME: str 

    @property
    def async_database_url(self) -> str:
        return (f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4")

    # class Config:
    #     env_file = ".env"

# settings = Settings()
settings = Settings()  # type: ignore[call-arg]

