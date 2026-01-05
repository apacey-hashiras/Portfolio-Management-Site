from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "secret"
    DEBUG: bool = True

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
