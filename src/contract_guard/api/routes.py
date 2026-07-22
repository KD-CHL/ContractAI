"""Versioned ContractGuard review routes."""

from __future__ import annotations

import hashlib
import inspect
import json
import logging
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from starlette.concurrency import run_in_threadpool

from contract_guard.api.dependencies import (
    TenantScope,
    get_document_service,
    get_event_bus,
    get_identity_service,
    get_repository,
    get_review_cache,
    get_review_workflow,
    get_tenant_scope,
    require_roles,
)
from contract_guard.api.schemas import (
    DocumentInfo,
    FeedbackRequest,
    FeedbackResponse,
    MemoryItem,
    MemoryListResponse,
    MemoryUpsertRequest,
    ObligationsResponse,
    ReviewResponse,
    TextReviewRequest,
)
from contract_guard.services.cache import ReviewCache
from contract_guard.services.documents import (
    DocumentError,
    DocumentService,
    DocumentTooLargeError,
    ParsedDocument,
    text_fingerprint,
)
from contract_guard.services.events import Event, EventBus
from contract_guard.services.identity import SQLiteIdentityService, UserRole
from contract_guard.services.storage import (
    MemoryLayer,
    ReviewRepository,
    StoredReview,
    to_jsonable,
)

router = APIRouter(tags=["reviews"])
logger = logging.getLogger(__name__)


def _get_review_for_scope(
    repository: ReviewRepository,
    review_id: str,
    scope: TenantScope,
    *,
    include_deleted: bool = False,
) -> StoredReview | None:
    actor_getter = getattr(repository, "get_review_for_actor", None)
    if scope.authenticated and callable(actor_getter):
        return actor_getter(
            review_id,
            org_id=scope.org_id,
            user_id=scope.user_id,
            can_manage_all=scope.role.can_view_all_reviews,
            include_deleted=include_deleted,
        )
    return repository.get_review(review_id, org_id=scope.org_id, session_id=scope.session_id)


def _record_audit_safely(
    identity: SQLiteIdentityService,
    request: Request,
    scope: TenantScope,
    *,
    action: str,
    resource_id: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    if not scope.authenticated:
        return
    try:
        identity.record_audit(
            org_id=scope.org_id,
            actor_user_id=scope.user_id,
            action=action,
            resource_type="review",
            resource_id=resource_id,
            request_id=getattr(request.state, "request_id", None),
            ip_address=request.client.host if request.client else None,
            details=details,
        )
    except Exception as exc:
        logger.warning(
            "Audit write failed request_id=%s error_type=%s",
            getattr(request.state, "request_id", None),
            type(exc).__name__,
        )


def _parse_metadata(value: str | None) -> dict[str, Any]:
    if value is None or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="metadata must be a valid JSON object",
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="metadata must be a JSON object",
        )
    return parsed


def _cache_variant(contract_id: str | None, *, memory_revision: str = "none") -> str:
    # The report embeds contract_id, so it forms part of the analysis variant
    # while the original document fingerprint remains the primary cache key.
    return f"review-v2:contract={contract_id or ''}:memory={memory_revision}"


def _memory_revision(repository: ReviewRepository, scope: TenantScope) -> str:
    """Fingerprint durable guidance that is allowed to change a repeat review."""

    list_memories = getattr(repository, "list_memories", None)
    if not callable(list_memories):
        return "none"
    try:
        memories = list_memories(
            org_id=scope.org_id,
            session_id=scope.session_id,
            layer=None,
            limit=1000,
        )
    except Exception:
        return "unavailable"
    durable_layers = {
        MemoryLayer.GLOBAL,
        MemoryLayer.PROFILE,
        MemoryLayer.EPISODIC,
    }
    parts = [
        f"{memory.layer.value}:{memory.key}:{memory.updated_at.isoformat()}"
        for memory in memories
        if memory.layer in durable_layers
    ]
    if not parts:
        return "none"
    return hashlib.sha256("\x1f".join(sorted(parts)).encode("utf-8")).hexdigest()[:16]


async def _invoke_workflow(
    workflow: Any,
    text: str,
    *,
    contract_id: str | None,
    org_id: str,
    session_id: str,
) -> dict[str, Any]:
    review = getattr(workflow, "areview", None)
    if review is None:
        review = getattr(workflow, "review", None)
    if review is None:
        if callable(workflow):
            review = workflow
        else:
            raise TypeError("the configured review workflow has no review method")

    kwargs: dict[str, Any] = {"contract_id": contract_id}
    parameters: Mapping[str, inspect.Parameter]
    try:
        parameters = inspect.signature(review).parameters
    except (TypeError, ValueError):  # pragma: no cover - unusual native callable
        parameters = {}
    accepts_extra = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )
    if accepts_extra or "org_id" in parameters:
        kwargs["org_id"] = org_id
    if accepts_extra or "session_id" in parameters:
        kwargs["session_id"] = session_id

    if inspect.iscoroutinefunction(review):
        result = await review(text, **kwargs)
    else:
        result = await run_in_threadpool(review, text, **kwargs)
        if inspect.isawaitable(result):
            result = await result

    if isinstance(result, Mapping) and "report" in result:
        result = result["report"]
    converted = to_jsonable(result)
    if not isinstance(converted, dict):
        raise TypeError("the review workflow must return a report object")
    return converted


async def _publish_safely(bus: EventBus, event: Event) -> None:
    # Event delivery is deliberately best-effort for the request path. Durable
    # production delivery can be supplied by an outbox-backed EventBus without
    # coupling the API to a specific broker.
    try:
        await bus.publish(event)
    except Exception:
        return


def _storage_metadata(
    document: ParsedDocument,
    request_metadata: Mapping[str, Any],
    *,
    cached: bool,
) -> dict[str, Any]:
    return {
        "request": dict(request_metadata),
        "_platform": {
            "size_bytes": document.size_bytes,
            "character_count": document.character_count,
            "page_count": document.page_count,
            "document_metadata": dict(document.metadata),
            "cached": cached,
        },
    }


def _response_from_review(review: StoredReview) -> ReviewResponse:
    platform = review.metadata.get("_platform", {})
    if not isinstance(platform, Mapping):
        platform = {}
    request_metadata = review.metadata.get("request", {})
    if not isinstance(request_metadata, Mapping):
        request_metadata = {}
    report_contract_id = review.report.get("contract_id")
    return ReviewResponse(
        review_id=review.id,
        created_by_user_id=review.created_by_user_id,
        status=review.status,
        contract_id=review.contract_id or (str(report_contract_id) if report_contract_id else None),
        document=DocumentInfo(
            filename=review.document_name,
            media_type=review.media_type,
            fingerprint=review.fingerprint,
            size_bytes=int(platform.get("size_bytes") or 0),
            character_count=(
                int(platform["character_count"])
                if platform.get("character_count") is not None
                else None
            ),
            page_count=(
                int(platform["page_count"]) if platform.get("page_count") is not None else None
            ),
        ),
        report=review.report,
        metadata=dict(request_metadata),
        cached=bool(platform.get("cached", False)),
        error=review.error,
        created_at=review.created_at,
        updated_at=review.updated_at,
        deleted_at=review.deleted_at,
        decision_status=review.decision_status,
        state_version=review.state_version,
    )


async def _submit_review(
    document: ParsedDocument,
    *,
    contract_id: str | None,
    request_metadata: Mapping[str, Any],
    scope: TenantScope,
    repository: ReviewRepository,
    cache: ReviewCache,
    event_bus: EventBus,
    workflow: Any,
) -> ReviewResponse:
    variant = _cache_variant(
        contract_id,
        memory_revision=_memory_revision(repository, scope),
    )
    try:
        cached_report = await cache.get(
            org_id=scope.org_id,
            session_id=scope.session_id,
            fingerprint=document.fingerprint,
            variant=variant,
        )
    except Exception:
        cached_report = None

    review = repository.create_review(
        org_id=scope.org_id,
        session_id=scope.session_id,
        fingerprint=document.fingerprint,
        document_name=document.filename,
        media_type=document.media_type,
        contract_id=contract_id,
        metadata=_storage_metadata(document, request_metadata, cached=cached_report is not None),
        created_by_user_id=scope.user_id,
    )
    base_event = {
        "review_id": review.id,
        "contract_id": contract_id,
        "fingerprint": document.fingerprint,
        "media_type": document.media_type,
    }
    await _publish_safely(
        event_bus,
        Event(
            name="review.created",
            payload=base_event,
            org_id=scope.org_id,
            session_id=scope.session_id,
        ),
    )

    if cached_report is not None:
        completed = repository.update_review(
            review.id,
            org_id=scope.org_id,
            session_id=scope.session_id,
            status="completed",
            report=cached_report,
        )
        if completed is None:  # pragma: no cover - repository invariant
            raise RuntimeError("created review disappeared before cache hydration")
        await _publish_safely(
            event_bus,
            Event(
                name="review.completed",
                payload={**base_event, "cached": True},
                org_id=scope.org_id,
                session_id=scope.session_id,
            ),
        )
        _remember_completed_review(
            repository,
            scope=scope,
            review_id=completed.id,
            contract_id=contract_id,
            report=cached_report,
            fingerprint=document.fingerprint,
            cached=True,
        )
        return _response_from_review(completed)

    try:
        report = await _invoke_workflow(
            workflow,
            document.text,
            contract_id=contract_id,
            org_id=scope.org_id,
            session_id=scope.session_id,
        )
        completed = repository.update_review(
            review.id,
            org_id=scope.org_id,
            session_id=scope.session_id,
            status="completed",
            report=report,
        )
        if completed is None:  # pragma: no cover - repository invariant
            raise RuntimeError("created review disappeared before completion")
        with suppress(Exception):
            await cache.set(
                report,
                org_id=scope.org_id,
                session_id=scope.session_id,
                fingerprint=document.fingerprint,
                variant=variant,
            )
        await _publish_safely(
            event_bus,
            Event(
                name="review.completed",
                payload={**base_event, "cached": False},
                org_id=scope.org_id,
                session_id=scope.session_id,
            ),
        )
        _remember_completed_review(
            repository,
            scope=scope,
            review_id=completed.id,
            contract_id=contract_id,
            report=report,
            fingerprint=document.fingerprint,
            cached=False,
        )
        return _response_from_review(completed)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Review workflow failed review_id=%s error_type=%s",
            review.id,
            type(exc).__name__,
        )
        repository.update_review(
            review.id,
            org_id=scope.org_id,
            session_id=scope.session_id,
            status="failed",
            error="审阅执行失败，请稍后重试",
        )
        await _publish_safely(
            event_bus,
            Event(
                name="review.failed",
                payload={**base_event, "error_type": type(exc).__name__},
                org_id=scope.org_id,
                session_id=scope.session_id,
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "contract review failed", "review_id": review.id},
        ) from exc


def _remember_completed_review(
    repository: ReviewRepository,
    *,
    scope: TenantScope,
    review_id: str,
    contract_id: str | None,
    report: Mapping[str, Any],
    fingerprint: str,
    cached: bool,
) -> None:
    """Keep a compact session trace without persisting the submitted contract text."""

    remember = getattr(repository, "upsert_memory", None)
    if not callable(remember):
        return
    findings = report.get("findings", [])
    finding_titles = [
        str(item.get("title"))
        for item in findings
        if isinstance(item, Mapping) and item.get("title")
    ][:20]
    with suppress(Exception):
        remember(
            org_id=scope.org_id,
            session_id=scope.session_id,
            layer=MemoryLayer.SHORT_TERM,
            key=f"review:{review_id}",
            content={
                "review_id": review_id,
                "contract_id": contract_id,
                "summary": report.get("summary", {}),
                "finding_titles": finding_titles,
            },
            metadata={
                "source": "completed_review",
                "fingerprint": fingerprint,
                "cached": cached,
                "contains_contract_text": False,
            },
        )


@router.post(
    "/reviews/text",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Review contract text",
)
async def review_text(
    request: TextReviewRequest,
    http_request: Request,
    scope: TenantScope = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.REVIEWER)),
    repository: ReviewRepository = Depends(get_repository),
    cache: ReviewCache = Depends(get_review_cache),
    event_bus: EventBus = Depends(get_event_bus),
    workflow: Any = Depends(get_review_workflow),
    documents: DocumentService = Depends(get_document_service),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> ReviewResponse:
    content = request.text.encode("utf-8")
    if len(content) > documents.max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"text exceeds the {documents.max_bytes}-byte limit",
        )
    if len(request.text) > documents.max_characters:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"text exceeds the {documents.max_characters}-character limit",
        )
    suffix = Path(request.filename).suffix.lower()
    document = ParsedDocument(
        text=request.text.strip(),
        fingerprint=text_fingerprint(request.text),
        filename=Path(request.filename).name or "contract.txt",
        media_type="text/markdown" if suffix in {".md", ".markdown"} else "text/plain",
        size_bytes=len(content),
    )
    result = await _submit_review(
        document,
        contract_id=request.contract_id,
        request_metadata=request.metadata,
        scope=scope,
        repository=repository,
        cache=cache,
        event_bus=event_bus,
        workflow=workflow,
    )
    _record_audit_safely(
        identity,
        http_request,
        scope,
        action="review.created",
        resource_id=result.review_id,
        details={"cached": result.cached, "media_type": result.document.media_type},
    )
    return result


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and review a contract document",
)
async def review_document(
    request: Request,
    file: UploadFile = File(...),
    contract_id: str | None = Form(default=None),
    metadata: str | None = Form(default=None),
    scope: TenantScope = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.REVIEWER)),
    repository: ReviewRepository = Depends(get_repository),
    cache: ReviewCache = Depends(get_review_cache),
    event_bus: EventBus = Depends(get_event_bus),
    workflow: Any = Depends(get_review_workflow),
    documents: DocumentService = Depends(get_document_service),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> ReviewResponse:
    try:
        content = await file.read(documents.max_bytes + 1)
    finally:
        await file.close()
    try:
        document = await documents.parse(
            content,
            filename=file.filename,
            media_type=file.content_type,
        )
    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except DocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    result = await _submit_review(
        document,
        contract_id=contract_id,
        request_metadata=_parse_metadata(metadata),
        scope=scope,
        repository=repository,
        cache=cache,
        event_bus=event_bus,
        workflow=workflow,
    )
    _record_audit_safely(
        identity,
        request,
        scope,
        action="review.created",
        resource_id=result.review_id,
        details={"cached": result.cached, "media_type": result.document.media_type},
    )
    return result


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Get a stored review",
)
async def get_review(
    review_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> ReviewResponse:
    review = _get_review_for_scope(repository, review_id, scope, include_deleted=True)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="review not found")
    return _response_from_review(review)


@router.post(
    "/reviews/{review_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit review feedback",
)
async def submit_feedback(
    review_id: str,
    request: FeedbackRequest,
    http_request: Request,
    scope: TenantScope = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.REVIEWER)),
    repository: ReviewRepository = Depends(get_repository),
    event_bus: EventBus = Depends(get_event_bus),
    identity: SQLiteIdentityService = Depends(get_identity_service),
) -> FeedbackResponse:
    add_feedback = getattr(repository, "add_feedback", None)
    if add_feedback is None:  # pragma: no cover - invalid integration configuration
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="feedback storage is unavailable",
        )
    review = _get_review_for_scope(repository, review_id, scope)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="review not found")
    feedback = add_feedback(
        review_id,
        org_id=scope.org_id,
        session_id=review.session_id,
        rating=request.rating,
        accepted=request.resolved_accepted,
        finding_id=request.finding_id,
        comment=request.comment,
        metadata=request.metadata,
    )
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="review not found")
    is_negative = (feedback.rating is not None and feedback.rating <= 2) or (
        feedback.accepted is False
    )
    remember = getattr(repository, "upsert_memory", None)
    if is_negative and callable(remember):
        with suppress(Exception):
            remember(
                org_id=scope.org_id,
                session_id=scope.session_id,
                layer=MemoryLayer.EPISODIC,
                key=f"feedback:{feedback.id}",
                content={
                    "review_id": review_id,
                    "finding_id": feedback.finding_id,
                    "rating": feedback.rating,
                    "accepted": feedback.accepted,
                    "comment": feedback.comment,
                },
                metadata={
                    "source": "review_feedback",
                    "signal": "negative",
                    "error": True,
                    "error_type": "negative_review_feedback",
                    "feedback_id": feedback.id,
                },
            )
    await _publish_safely(
        event_bus,
        Event(
            name="review.feedback_submitted",
            payload={
                "review_id": review_id,
                "feedback_id": feedback.id,
                "finding_id": feedback.finding_id,
            },
            org_id=scope.org_id,
            session_id=scope.session_id,
        ),
    )
    _record_audit_safely(
        identity,
        http_request,
        scope,
        action="review.feedback_submitted",
        resource_id=review_id,
        details={"finding_id": feedback.finding_id},
    )
    return FeedbackResponse(
        feedback_id=feedback.id,
        review_id=review_id,
        rating=feedback.rating,
        accepted=feedback.accepted,
        finding_id=feedback.finding_id,
        comment=feedback.comment,
        created_at=feedback.created_at,
    )


@router.get(
    "/reviews/{review_id}/obligations",
    response_model=ObligationsResponse,
    summary="List obligations extracted by a review",
)
async def get_obligations(
    review_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> ObligationsResponse:
    review = _get_review_for_scope(repository, review_id, scope)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="review not found")
    raw_obligations: Any = review.report.get("obligations", [])
    if isinstance(raw_obligations, Mapping):
        raw_obligations = raw_obligations.get("items", [])
    obligations = (
        [dict(item) if isinstance(item, Mapping) else {"value": item} for item in raw_obligations]
        if isinstance(raw_obligations, list)
        else []
    )
    return ObligationsResponse(review_id=review.id, status=review.status, obligations=obligations)


@router.get(
    "/memories/profile",
    response_model=MemoryListResponse,
    tags=["memory"],
    summary="List session profile memories",
)
async def get_profile_memories(
    limit: int = Query(default=100, ge=1, le=500),
    scope: TenantScope = Depends(get_tenant_scope),
    repository: ReviewRepository = Depends(get_repository),
) -> MemoryListResponse:
    list_memories = getattr(repository, "list_memories", None)
    if not callable(list_memories):  # pragma: no cover - invalid integration config
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="memory storage is unavailable",
        )
    memories = list_memories(
        org_id=scope.org_id,
        session_id=scope.session_id,
        layer=MemoryLayer.PROFILE,
        limit=limit,
    )
    return MemoryListResponse(
        layer=MemoryLayer.PROFILE.value,
        memories=[
            MemoryItem(
                memory_id=memory.id,
                layer=memory.layer.value,
                key=memory.key,
                content=memory.content,
                metadata=memory.metadata,
                created_at=memory.created_at,
                updated_at=memory.updated_at,
            )
            for memory in memories
        ],
    )


@router.put(
    "/memories/profile/{key}",
    response_model=MemoryItem,
    tags=["memory"],
    summary="Create or update a session profile memory",
)
async def upsert_profile_memory(
    key: str,
    request: MemoryUpsertRequest,
    scope: TenantScope = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.REVIEWER)),
    repository: ReviewRepository = Depends(get_repository),
) -> MemoryItem:
    upsert_memory = getattr(repository, "upsert_memory", None)
    if not callable(upsert_memory):  # pragma: no cover - invalid integration config
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="memory storage is unavailable",
        )
    try:
        memory = upsert_memory(
            org_id=scope.org_id,
            session_id=scope.session_id,
            layer=MemoryLayer.PROFILE,
            key=key,
            content=request.content,
            metadata={**request.metadata, "source": "profile_api"},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return MemoryItem(
        memory_id=memory.id,
        layer=memory.layer.value,
        key=memory.key,
        content=memory.content,
        metadata=memory.metadata,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )
