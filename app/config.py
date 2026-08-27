from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "MemberAssist: Health Insurance Knowledge Hub"
    APP_ENV: str = "production"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: Union[List[str], str] = [
        "https://winelogbooks.com",
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
    ]

    # Azure AI Search Configuration
    AZURE_SEARCH_SERVICE_ENDPOINT: str = ""
    AZURE_SEARCH_API_KEY: str = ""
    AZURE_SEARCH_INDEX_NAME: str = "health-plan-knowledge-index"
    AZURE_SEARCH_SEMANTIC_CONFIG_NAME: str = "health-plan-semantic-config"

    # Azure AI Foundry / Azure OpenAI Model Configuration
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = "gpt-4o-mini"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"

    # Mock Mode: Fallback to mock search & reasoning when credentials are not configured
    ENABLE_MOCK_FALLBACK: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
