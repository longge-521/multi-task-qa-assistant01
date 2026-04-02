import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Force load .env and override system environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path, override=True)

class Settings(BaseSettings):
    # DeepSeek API config
    DEEPSEEK_API_KEY: str = "sk-xxx"
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    
    # App config
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 5000
    DEBUG: bool = True
    
    # Database config (aligned with .env variable name)
    SQLITE_URL: str = "sqlite:///chat_history.db"
    
    # Vector DB config
    KNOWLEDGE_BASE_DIR: str = "knowledge"
    VECTOR_DB_PATH: str = "vector_db_index"

    model_config = SettingsConfigDict(
        env_file=env_path,
        env_file_encoding='utf-8',
        extra='ignore'
    )

# Singleton instance for the app
settings = Settings()
