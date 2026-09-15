"""Configuração da aplicação, lida do ambiente.

Nada de segredo embutido no código: tudo vem do .env, que está no .gitignore.
O repositório é público (ver CLAUDE.md, regra 2.1).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://gih:gih@localhost:5432/gih"
    api_port: int = 8000

    # Limite de entrada para evitar consumo excessivo de recursos (RNF15).
    tamanho_maximo_relatorio: int = 500_000
    tamanho_maximo_pergunta: int = 1_000


config = Config()
