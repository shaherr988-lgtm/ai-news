from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app configuration, read from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg2://ai_news:ai_news@localhost:5432/ai_news"

    # LLM provider selection (generation) — "openai" | "anthropic" | "gemini" | "deepseek"
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"
    gemini_model: str = "gemini-3.6-flash"
    deepseek_api_key: str | None = None
    deepseek_model: str = "deepseek-chat"

    # Safety ceiling on LLM generate/summarize calls per run_daily invocation —
    # matters mainly for Gemini's free tier (20 generate_content calls/day
    # total). One call is always reserved for the final digest build; set
    # generously (e.g. 1000) for a paid provider with no such cap.
    llm_daily_call_budget: int = 1000

    # Embedding provider selection (RAG) — "openai" or "gemini".
    # NOTE: required even when llm_provider="anthropic" — Anthropic has no
    # native text-embeddings endpoint. embedding_dim MUST match whatever
    # provider/model is active: the pgvector column size is fixed at table
    # creation time, so changing providers means recreating article_chunks.
    embedding_provider: str = "openai"
    embedding_dim: int = 1536
    openai_embedding_model: str = "text-embedding-3-small"

    # Gemini embeddings — a free-tier-friendly alternative to OpenAI (an
    # aistudio.google.com API key works without adding billing). Set
    # EMBEDDING_PROVIDER=gemini and EMBEDDING_DIM=768 to use it.
    gemini_api_key: str | None = None
    gemini_embedding_model: str = "gemini-embedding-001"

    # RAG chunking / retrieval
    rag_chunk_size_chars: int = 1000
    rag_chunk_overlap_chars: int = 150
    rag_top_k: int = 5

    # Email — "gmail", "outlook" (Microsoft 365 org accounts only), or
    # "brevo" (recommended for personal accounts — see BrevoAPISender).
    email_provider: str = "gmail"
    gmail_address: str | None = None
    gmail_app_password: str | None = None
    outlook_address: str | None = None
    outlook_app_password: str | None = None
    # "brevo" — a dedicated transactional email service (free tier: 300/day),
    # sent over its HTTPS API rather than SMTP (see BrevoAPISender in
    # apps/pipeline/mailer.py for why: PaaS free tiers like Render block
    # outbound SMTP ports). The API key comes from the Brevo dashboard
    # (Settings -> SMTP & API -> API keys & MCP), not the SMTP login/key pair.
    brevo_api_key: str | None = None
    brevo_sender_email: str | None = None
    digest_recipient_email: str | None = None

    # Optional HTTP Basic Auth for the web app — unset by default (no auth,
    # fine for pure localhost use). Set both when exposing the app beyond your
    # own machine (e.g. a temporary public tunnel) so it isn't wide open.
    basic_auth_username: str | None = None
    basic_auth_password: str | None = None

    # Secret token for POST /internal/run-daily — lets a free external cron
    # service (e.g. cron-job.org) trigger the daily pipeline over HTTP, since
    # Render's own Cron Job service has no free tier. Exempted from
    # BasicAuthMiddleware (see apps/web/main.py) so the external scheduler
    # doesn't also need Basic Auth credentials — the token alone gates it.
    run_daily_token: str | None = None

    # Optional: Webshare (or similar) residential proxy for YouTube transcript
    # fetching — usually only needed once deployed to a datacenter host (e.g.
    # Render), which YouTube tends to block transcript requests from. Read
    # directly from the environment in apps/pipeline/fetch_youtube.py, not
    # here, since it's consumed by a third-party SDK's own config object.


@lru_cache
def get_settings() -> Settings:
    """Cached singleton accessor so we don't re-parse the environment on every call."""
    return Settings()
