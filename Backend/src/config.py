import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
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
    UPLOAD_DOC_DIR: str = "knowledge/upload_doc"
    LOAD_DOC_DIR: str = "knowledge/load_doc"
    CHUNK_DOC_DIR: str = "knowledge/chunk_doc"
    EMBEDDING_DOC_DIR: str = "knowledge/embedding_doc"
    VECTOR_STORE_DIR: str = "knowledge/vector_store"
    
    VECTOR_DB_PATH: str = "vector_db_index"
    METADATA_PATH: str = Field(default="vector_db_index/metadata.json")

    @field_validator('METADATA_PATH', 'VECTOR_DB_PATH', 'KNOWLEDGE_BASE_DIR', 'UPLOAD_DOC_DIR', 'LOAD_DOC_DIR', 'CHUNK_DOC_DIR', 'EMBEDDING_DOC_DIR', 'VECTOR_STORE_DIR', mode='before')
    @classmethod
    def resolve_relative_paths(cls, v: str, info):
        """Resolve relative paths to absolute paths relative to project root."""
        if not v or v.startswith('/') or ':' in v:  # Already absolute or URL
            return v

        # Project root is parent of Backend/src directory
        project_root = Path(__file__).parent.parent

        # Resolve path relative to project root
        resolved_path = (project_root / v).resolve()

        # For directories, ensure they exist
        if info.field_name in ['VECTOR_DB_PATH', 'KNOWLEDGE_BASE_DIR', 'UPLOAD_DOC_DIR']:
            resolved_path.mkdir(parents=True, exist_ok=True)

        return str(resolved_path)

    model_config = SettingsConfigDict(
        env_file=env_path,
        env_file_encoding='utf-8',
        extra='ignore'
    )

# Singleton instance for the app
settings = Settings()
