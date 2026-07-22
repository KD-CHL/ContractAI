"""ContractGuard FastAPI application factory."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from contract_guard.agent.workflow import (
    ContextProvider,
    ContractReviewWorkflow,
    ReviewDependencies,
)
from contract_guard.api import router as api_router
from contract_guard.api.errors import install_exception_handlers
from contract_guard.api.schemas import HealthResponse
from contract_guard.config import Settings, get_settings
from contract_guard.infrastructure.db.migrations import upgrade_database
from contract_guard.services.cache import InMemoryReviewCache, ReviewCache
from contract_guard.services.documents import DocumentService, VisionOCR
from contract_guard.services.events import EventBus, LocalEventBus
from contract_guard.services.identity import SQLiteIdentityService
from contract_guard.services.knowledge import (
    LightRAGContextProvider,
    LocalKnowledgeContextProvider,
)
from contract_guard.services.memory import RepositoryMemoryContextProvider
from contract_guard.services.rate_limit import SlidingWindowRateLimiter
from contract_guard.services.storage import ReviewRepository, SQLiteReviewRepository
from contract_guard.services.vision import OpenAIVisionOCR


def _default_workflow(
    settings: Settings,
    repository: ReviewRepository,
) -> ContractReviewWorkflow:
    local_knowledge = LocalKnowledgeContextProvider(settings.knowledge_path)
    knowledge_provider: ContextProvider = local_knowledge
    if settings.app_mode == "hybrid" and settings.lightrag_base_url:
        knowledge_provider = LightRAGContextProvider(
            settings.lightrag_base_url,
            api_key=os.environ.get("LIGHTRAG_API_KEY"),
            fallback=local_knowledge,
        )
    memory_provider = RepositoryMemoryContextProvider(repository)
    if settings.llm_enabled:
        return ContractReviewWorkflow.with_openai(
            settings=settings,
            model=settings.openai_model,
            knowledge_provider=knowledge_provider,
            memory_provider=memory_provider,
        )
    return ContractReviewWorkflow(
        ReviewDependencies(
            knowledge_provider=knowledge_provider,
            memory_provider=memory_provider,
        )
    )


def create_app(
    *,
    settings: Settings | None = None,
    workflow: Any | None = None,
    review_workflow: Any | None = None,
    repository: ReviewRepository | None = None,
    storage: ReviewRepository | None = None,
    cache: ReviewCache | None = None,
    event_bus: EventBus | None = None,
    vision_ocr: VisionOCR | None = None,
    document_service: DocumentService | None = None,
    identity_service: SQLiteIdentityService | None = None,
) -> FastAPI:
    """Construct an application with replaceable platform dependencies."""

    resolved_settings = settings or get_settings()
    if resolved_settings.sqlite_path != ":memory:":
        upgrade_database(resolved_settings.sqlite_path)
    resolved_repository = repository or storage
    owns_repository = resolved_repository is None
    if resolved_repository is None:
        resolved_repository = SQLiteReviewRepository(resolved_settings.sqlite_path)

    resolved_identity = identity_service
    owns_identity = resolved_identity is None
    if resolved_identity is None:
        if resolved_settings.sqlite_path == ":memory:":
            if resolved_settings.auth_required:
                raise ValueError("authenticated apps require a file-backed SQLite database")
        else:
            resolved_identity = SQLiteIdentityService(
                resolved_settings.sqlite_path,
                access_ttl_minutes=resolved_settings.auth_access_ttl_minutes,
                refresh_ttl_days=resolved_settings.auth_refresh_ttl_days,
                registration_enabled=resolved_settings.registration_enabled,
            )

    resolved_workflow = (
        workflow
        or review_workflow
        or _default_workflow(
            resolved_settings,
            resolved_repository,
        )
    )
    resolved_cache = cache or InMemoryReviewCache(
        default_ttl_seconds=resolved_settings.cache_ttl_seconds
    )
    resolved_events = event_bus or LocalEventBus()
    resolved_vision_ocr = vision_ocr
    if document_service is None and resolved_vision_ocr is None and resolved_settings.llm_enabled:
        resolved_vision_ocr = OpenAIVisionOCR(
            model=resolved_settings.openai_model or "gpt-5.6-luna",
            base_url=resolved_settings.openai_base_url,
            timeout=resolved_settings.openai_timeout_seconds,
            max_retries=resolved_settings.openai_max_retries,
        )
    resolved_documents = document_service or DocumentService(
        vision_ocr=resolved_vision_ocr,
        max_bytes=resolved_settings.max_upload_bytes,
        max_pages=resolved_settings.max_document_pages,
        max_characters=resolved_settings.max_document_characters,
        max_docx_uncompressed_bytes=resolved_settings.max_docx_uncompressed_bytes,
        max_ocr_pixels=resolved_settings.max_ocr_pixels,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_repository:
            close = getattr(resolved_repository, "close", None)
            if callable(close):
                close()
        if owns_identity and resolved_identity is not None:
            resolved_identity.close()

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        docs_url="/docs" if resolved_settings.docs_enabled else None,
        redoc_url="/redoc" if resolved_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.repository = resolved_repository
    app.state.review_cache = resolved_cache
    app.state.event_bus = resolved_events
    app.state.document_service = resolved_documents
    app.state.review_workflow = resolved_workflow
    app.state.identity = resolved_identity
    app.state.login_rate_limiter = SlidingWindowRateLimiter(
        limit=resolved_settings.login_attempt_limit,
        window_seconds=resolved_settings.login_window_seconds,
    )

    logging.getLogger().setLevel(resolved_settings.log_level)
    access_logger = logging.getLogger("contract_guard.http")
    install_exception_handlers(app)

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> Response:
        supplied_request_id = request.headers.get("x-request-id", "").strip()
        request_id = (
            supplied_request_id
            if re.fullmatch(r"[A-Za-z0-9._:-]{8,80}", supplied_request_id)
            else str(uuid4())
        )
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        access_logger.info(
            json.dumps(
                {
                    "event": "http.request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "actor_user_id": getattr(getattr(request.state, "user", None), "id", None),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return response

    @app.middleware("http")
    async def browser_security_headers(request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        return response

    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Org-ID",
                "X-Session-ID",
                "X-Request-ID",
            ],
        )

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
        summary="Service health check",
    )
    async def health() -> HealthResponse:
        healthcheck = getattr(resolved_repository, "healthcheck", None)
        storage_ok = bool(healthcheck()) if callable(healthcheck) else True
        if not storage_ok:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="storage unavailable",
            )
        return HealthResponse(
            status="ok",
            service=resolved_settings.app_name,
            version=resolved_settings.app_version,
            environment=resolved_settings.environment,
            storage="ok",
            mode=resolved_settings.app_mode,
            ai_enabled=resolved_settings.llm_enabled,
            model=(resolved_settings.openai_model if resolved_settings.llm_enabled else None),
            api_prefix=resolved_settings.api_prefix,
            max_upload_bytes=resolved_settings.max_upload_bytes,
            auth_required=resolved_settings.auth_required,
            registration_enabled=resolved_settings.registration_enabled,
        )

    @app.get("/live", tags=["system"], summary="Process liveness check")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["system"], summary="Configured dependency readiness")
    async def ready() -> dict[str, Any]:
        healthcheck = getattr(resolved_repository, "healthcheck", None)
        storage_ok = bool(healthcheck()) if callable(healthcheck) else True
        openai_configured = bool(os.environ.get("OPENAI_API_KEY"))
        dependencies = {
            "storage": "ok" if storage_ok else "unavailable",
            "openai": (
                "configured"
                if openai_configured
                else ("not_required" if not resolved_settings.llm_enabled else "missing")
            ),
            "knowledge": ("configured" if resolved_settings.lightrag_base_url else "local"),
        }
        if not storage_ok or (resolved_settings.llm_enabled and not openai_configured):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "service dependencies are not ready", **dependencies},
            )
        return {"status": "ready", "dependencies": dependencies}

    app.include_router(api_router, prefix=resolved_settings.api_prefix)

    # Vue SPA static serving — registered LAST so catch-all doesn't shadow API routes
    web_directory = Path(__file__).resolve().parent / "web"
    if web_directory.is_dir():
        assets_directory = web_directory / "assets"
        if assets_directory.is_dir():
            app.mount(
                "/assets",
                StaticFiles(directory=assets_directory),
                name="assets",
            )

        _CSP = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'"
        )

        @app.get("/", include_in_schema=False)
        async def web_ui() -> FileResponse:
            response = FileResponse(web_directory / "index.html")
            response.headers["Content-Security-Policy"] = _CSP
            return response

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_fallback(full_path: str) -> FileResponse:
            file_path = web_directory / full_path
            if full_path and file_path.is_file():
                return FileResponse(file_path)
            response = FileResponse(web_directory / "index.html")
            response.headers["Content-Security-Policy"] = _CSP
            return response

    return app


app = create_app()


__all__ = ["app", "create_app"]
