"""Central application settings.

Loads configuration from environment variables (and an optional `.env` file at
the repository root). Required secrets have no defaults, so the app fails fast
with a clear error if any are missing.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is two levels up from this file: backend/app/config.py -> repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed application configuration.

    Required fields (no default) will raise on startup if unset. Optional fields
    default to ``None`` / sensible values so the service can boot without them.
    """

    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Required secrets -----------------------------------------------------
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for LLM reasoning.")
    SUPABASE_URL: str = Field(..., description="Supabase project URL.")
    SUPABASE_SERVICE_KEY: str = Field(
        ..., description="Supabase service role key (server-side only)."
    )
    SUPABASE_DB_URL: str = Field(
        ..., description="Postgres connection URL for domain tables + checkpointer."
    )

    # --- Optional configuration ----------------------------------------------
    NOTION_TOKEN: str | None = Field(
        default=None, description="Notion integration token for MCP export."
    )
    NOTION_PARENT_PAGE_ID: str | None = Field(
        default=None, description="Notion page id under which exported plans are created."
    )
    NOTION_VERSION: str = Field(
        default="2022-06-28", description="Notion API version header."
    )
    NOTION_MCP_COMMAND: str = Field(
        default="npx", description="Command to launch the Notion MCP server."
    )
    NOTION_MCP_ARGS: str = Field(
        default="-y @notionhq/notion-mcp-server",
        description="Space-separated args for the Notion MCP server command.",
    )
    CONTACT_EMAIL: str | None = Field(
        default=None, description="Email for the OpenAlex polite pool."
    )
    SEMANTIC_SCHOLAR_API_KEY: str | None = Field(
        default=None, description="Optional Semantic Scholar API key for higher limits."
    )

    # --- App behavior ---------------------------------------------------------
    OPENAI_MODEL: str = Field(default="gpt-4o", description="Default OpenAI model.")
    APP_ENV: str = Field(default="development", description="Deployment environment.")
    LOG_LEVEL: str = Field(default="INFO", description="Log level for structlog.")
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins.",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def notion_mcp_args(self) -> list[str]:
        return self.NOTION_MCP_ARGS.split()

    @property
    def notion_configured(self) -> bool:
        return bool(self.NOTION_TOKEN and self.NOTION_PARENT_PAGE_ID)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance, failing fast with a clear message.

    Raises:
        RuntimeError: if any required environment variables are missing/invalid.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        missing = [
            ".".join(str(loc) for loc in err["loc"])
            for err in exc.errors()
            if err["type"] in {"missing", "value_error.missing"}
        ]
        details = ", ".join(missing) if missing else str(exc)
        raise RuntimeError(
            "Invalid or missing configuration. Set the following environment "
            f"variables (see .env.example): {details}"
        ) from exc
