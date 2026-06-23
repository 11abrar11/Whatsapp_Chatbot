"""
Application Configuration
Loads and validates all environment variables using Pydantic Settings.
"""

import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Groq (LLM) ---
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model name",
    )
    groq_fallback_model: str = Field(
        default="llama-3.1-8b-instant",
        description="Fallback Groq model when primary hits rate limits",
    )

    # --- Gemini (Embeddings) ---
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_embedding_model: str = Field(
        default="text-embedding-004",
        description="Gemini embedding model name",
    )

    # --- Qdrant ---
    qdrant_host: str = Field(default="qdrant", description="Qdrant hostname")
    qdrant_port: int = Field(default=6333, description="Qdrant port")
    qdrant_collection: str = Field(
        default="pp5_knowledge",
        description="Qdrant collection name",
    )

    # --- Baileys (WhatsApp) ---
    baileys_service_url: str = Field(
        default="http://localhost:3001",
        description="URL of the Baileys Node.js WhatsApp service",
    )

    # --- Google Sheets ---
    google_sheet_id: str = Field(default="", description="Google Sheet ID")
    google_service_account_json: str = Field(
        default="/app/config/service_account.json",
        description="Path to Google service account JSON file",
    )

    # --- Gmail SMTP ---
    gmail_sender: str = Field(default="", description="Gmail sender address")
    gmail_app_password: str = Field(default="", description="Gmail App Password")
    escalation_recipient: str = Field(
        default="",
        description="Email address to receive escalation notifications",
    )

    # --- Application ---
    backend_port: int = Field(default=8000, description="Backend server port")
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = {
        "env_file": "config/.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton settings instance
_settings = None


def get_settings() -> Settings:
    """Get the application settings (cached singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
