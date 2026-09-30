"""Leitura centralizada das configurações do projeto a partir do .env."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env", override=True)

@dataclass(frozen=True)
class Settings:
    # Provedor ativo: "anthropic", "openai" ou "ollama"
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "16384"))


settings = Settings()
