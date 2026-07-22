"""Runtime configuration for the ContractGuard HTTP service.

Local development may load the explicitly ignored ``.env.local`` file.  In
containers and production, process environment variables still take priority.
No configuration value is logged from this module.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DEFAULT_KNOWLEDGE_PATH = str(
    Path(__file__).resolve().parent / "resources" / "demo_knowledge_base.json"
)


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def _as_positive_int(value: str | None, default: int, *, name: str) -> int:
    if value is None:
        return default
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed


def _as_nonnegative_int(value: str | None, default: int, *, name: str) -> int:
    if value is None:
        return default
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"{name} must be zero or greater")
    return parsed


def _as_positive_float(value: str | None, default: float, *, name: str) -> float:
    if value is None:
        return default
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed


@dataclass(frozen=True, slots=True)
class Settings:
    """Application settings with safe, local-first defaults."""

    app_name: str = "ContractGuard"
    app_version: str = "0.1.0"
    environment: str = "development"
    app_mode: str = "offline"
    llm_enabled: bool = False
    openai_model: str | None = "gpt-5.6-luna"
    openai_base_url: str | None = None
    openai_timeout_seconds: float = 60.0
    openai_max_retries: int = 2
    lightrag_base_url: str | None = None
    knowledge_path: str = _DEFAULT_KNOWLEDGE_PATH
    api_prefix: str = "/api/v1"
    sqlite_path: str = "data/contractguard.db"
    max_upload_bytes: int = 20 * 1024 * 1024
    max_document_pages: int = 200
    max_document_characters: int = 1_000_000
    max_docx_uncompressed_bytes: int = 100 * 1024 * 1024
    max_ocr_pixels: int = 20_000_000
    cache_ttl_seconds: int = 60 * 60
    default_org_id: str = "default"
    default_session_id: str = "anonymous"
    cors_origins: tuple[str, ...] = ()
    docs_enabled: bool = True
    log_level: str = "INFO"
    auth_required: bool = True
    registration_enabled: bool = True
    auth_access_ttl_minutes: int = 8 * 60
    auth_refresh_ttl_days: int = 30
    auth_cookie_secure: bool = False
    login_attempt_limit: int = 10
    login_window_seconds: int = 5 * 60
    legacy_tenant_headers_enabled: bool = False

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build settings from an environment mapping.

        Supplying a mapping makes tests deterministic and, importantly, avoids
        any implicit filesystem reads.
        """

        env = os.environ if environ is None else environ
        defaults = cls()
        origins = tuple(
            item.strip()
            for item in env.get("CONTRACT_GUARD_CORS_ORIGINS", "").split(",")
            if item.strip()
        )
        prefix = env.get("CONTRACT_GUARD_API_PREFIX", defaults.api_prefix).strip()
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"
        prefix = prefix.rstrip("/") or "/"

        app_mode = (
            env.get("CONTRACT_GUARD_APP_MODE", env.get("APP_MODE", defaults.app_mode))
            .strip()
            .lower()
        )
        if app_mode not in {"offline", "hybrid"}:
            raise ValueError("APP_MODE must be either 'offline' or 'hybrid'")
        explicit_llm_enabled = env.get("CONTRACT_GUARD_LLM_ENABLED")
        llm_enabled = (
            app_mode == "hybrid"
            if explicit_llm_enabled is None
            else _as_bool(explicit_llm_enabled, False)
        )
        sqlite_path = _resolve_sqlite_path(env, defaults.sqlite_path)

        return cls(
            app_name=env.get("CONTRACT_GUARD_APP_NAME", defaults.app_name),
            app_version=env.get("CONTRACT_GUARD_APP_VERSION", defaults.app_version),
            environment=env.get("CONTRACT_GUARD_ENV", defaults.environment),
            app_mode=app_mode,
            llm_enabled=llm_enabled,
            openai_model=(
                env.get("CONTRACT_GUARD_OPENAI_MODEL")
                or env.get("OPENAI_MODEL")
                or defaults.openai_model
            ),
            openai_base_url=(
                env.get("CONTRACT_GUARD_OPENAI_BASE_URL")
                or env.get("OPENAI_BASE_URL")
                or defaults.openai_base_url
            ),
            openai_timeout_seconds=_as_positive_float(
                env.get("CONTRACT_GUARD_OPENAI_TIMEOUT_SECONDS"),
                defaults.openai_timeout_seconds,
                name="CONTRACT_GUARD_OPENAI_TIMEOUT_SECONDS",
            ),
            openai_max_retries=_as_nonnegative_int(
                env.get("CONTRACT_GUARD_OPENAI_MAX_RETRIES"),
                defaults.openai_max_retries,
                name="CONTRACT_GUARD_OPENAI_MAX_RETRIES",
            ),
            lightrag_base_url=(
                env.get("CONTRACT_GUARD_LIGHTRAG_BASE_URL")
                or env.get("LIGHTRAG_BASE_URL")
                or defaults.lightrag_base_url
            ),
            knowledge_path=env.get("CONTRACT_GUARD_KNOWLEDGE_PATH", defaults.knowledge_path),
            api_prefix=prefix,
            sqlite_path=sqlite_path,
            max_upload_bytes=_as_positive_int(
                env.get("CONTRACT_GUARD_MAX_UPLOAD_BYTES"),
                defaults.max_upload_bytes,
                name="CONTRACT_GUARD_MAX_UPLOAD_BYTES",
            ),
            max_document_pages=_as_positive_int(
                env.get("CONTRACT_GUARD_MAX_DOCUMENT_PAGES"),
                defaults.max_document_pages,
                name="CONTRACT_GUARD_MAX_DOCUMENT_PAGES",
            ),
            max_document_characters=_as_positive_int(
                env.get("CONTRACT_GUARD_MAX_DOCUMENT_CHARACTERS"),
                defaults.max_document_characters,
                name="CONTRACT_GUARD_MAX_DOCUMENT_CHARACTERS",
            ),
            max_docx_uncompressed_bytes=_as_positive_int(
                env.get("CONTRACT_GUARD_MAX_DOCX_UNCOMPRESSED_BYTES"),
                defaults.max_docx_uncompressed_bytes,
                name="CONTRACT_GUARD_MAX_DOCX_UNCOMPRESSED_BYTES",
            ),
            max_ocr_pixels=_as_positive_int(
                env.get("CONTRACT_GUARD_MAX_OCR_PIXELS"),
                defaults.max_ocr_pixels,
                name="CONTRACT_GUARD_MAX_OCR_PIXELS",
            ),
            cache_ttl_seconds=_as_positive_int(
                env.get("CONTRACT_GUARD_CACHE_TTL_SECONDS"),
                defaults.cache_ttl_seconds,
                name="CONTRACT_GUARD_CACHE_TTL_SECONDS",
            ),
            default_org_id=env.get("CONTRACT_GUARD_DEFAULT_ORG_ID", defaults.default_org_id),
            default_session_id=env.get(
                "CONTRACT_GUARD_DEFAULT_SESSION_ID", defaults.default_session_id
            ),
            cors_origins=origins,
            docs_enabled=_as_bool(env.get("CONTRACT_GUARD_DOCS_ENABLED"), defaults.docs_enabled),
            log_level=env.get("CONTRACT_GUARD_LOG_LEVEL", env.get("LOG_LEVEL", defaults.log_level))
            .strip()
            .upper(),
            auth_required=_as_bool(env.get("CONTRACT_GUARD_AUTH_REQUIRED"), defaults.auth_required),
            registration_enabled=_as_bool(
                env.get("CONTRACT_GUARD_REGISTRATION_ENABLED"),
                defaults.registration_enabled,
            ),
            auth_access_ttl_minutes=_as_positive_int(
                env.get("CONTRACT_GUARD_AUTH_ACCESS_TTL_MINUTES"),
                defaults.auth_access_ttl_minutes,
                name="CONTRACT_GUARD_AUTH_ACCESS_TTL_MINUTES",
            ),
            auth_refresh_ttl_days=_as_positive_int(
                env.get("CONTRACT_GUARD_AUTH_REFRESH_TTL_DAYS"),
                defaults.auth_refresh_ttl_days,
                name="CONTRACT_GUARD_AUTH_REFRESH_TTL_DAYS",
            ),
            auth_cookie_secure=_as_bool(
                env.get("CONTRACT_GUARD_AUTH_COOKIE_SECURE"),
                defaults.auth_cookie_secure,
            ),
            login_attempt_limit=_as_positive_int(
                env.get("CONTRACT_GUARD_LOGIN_ATTEMPT_LIMIT"),
                defaults.login_attempt_limit,
                name="CONTRACT_GUARD_LOGIN_ATTEMPT_LIMIT",
            ),
            login_window_seconds=_as_positive_int(
                env.get("CONTRACT_GUARD_LOGIN_WINDOW_SECONDS"),
                defaults.login_window_seconds,
                name="CONTRACT_GUARD_LOGIN_WINDOW_SECONDS",
            ),
            legacy_tenant_headers_enabled=_as_bool(
                env.get("CONTRACT_GUARD_LEGACY_TENANT_HEADERS_ENABLED"),
                defaults.legacy_tenant_headers_enabled,
            ),
        )

    @property
    def database_path(self) -> Path | None:
        """Return a normalized SQLite path, or ``None`` for in-memory mode."""

        if self.sqlite_path == ":memory:":
            return None
        return Path(self.sqlite_path).expanduser().resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return process-wide configuration after safe local dotenv loading."""

    _load_local_environment()
    return Settings.from_env()


def clear_settings_cache() -> None:
    """Reset cached settings (primarily useful for tests)."""

    get_settings.cache_clear()


def _load_local_environment() -> None:
    """Load an explicitly local env file without overriding managed variables."""

    env_file = os.environ.get("CONTRACT_GUARD_ENV_FILE", ".env.local").strip()
    if not env_file:
        return
    path = Path(env_file).expanduser()
    if not path.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dependency installation concern
        return
    load_dotenv(path, override=False)


def _resolve_sqlite_path(env: Mapping[str, str], default: str) -> str:
    explicit = env.get("CONTRACT_GUARD_SQLITE_PATH")
    if explicit:
        return explicit
    database_url = env.get("DATABASE_URL", "").strip()
    if not database_url:
        return default
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("the built-in repository supports SQLite DATABASE_URL values only")
    path = database_url[len(prefix) :]
    if not path:
        raise ValueError("SQLite DATABASE_URL must include a database path")
    return path
