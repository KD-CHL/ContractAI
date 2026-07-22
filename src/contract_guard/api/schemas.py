"""Public HTTP request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TextReviewRequest(APIModel):
    text: str = Field(min_length=1, description="Complete contract text to review")
    contract_id: str | None = Field(default=None, max_length=256)
    filename: str = Field(default="contract.txt", min_length=1, max_length=512)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def text_must_not_be_whitespace(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text cannot be blank")
        return value


class DocumentInfo(APIModel):
    filename: str
    media_type: str
    fingerprint: str
    size_bytes: int = Field(ge=0)
    character_count: int | None = Field(default=None, ge=0)
    page_count: int | None = Field(default=None, ge=1)


class ReviewResponse(APIModel):
    review_id: str
    created_by_user_id: str | None = None
    status: str
    contract_id: str | None = None
    document: DocumentInfo
    report: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    cached: bool = False
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    decision_status: str = "draft"
    state_version: int = Field(default=1, ge=1)


class ReviewListItem(APIModel):
    review_id: str
    created_by_user_id: str | None = None
    status: str
    decision_status: str
    contract_id: str | None = None
    document_name: str
    media_type: str
    total_findings: int = Field(ge=0)
    highest_risk: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class ReviewListResponse(APIModel):
    items: list[ReviewListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


class DashboardResponse(APIModel):
    total_reviews: int = Field(ge=0)
    completed_reviews: int = Field(ge=0)
    high_risk_reviews: int = Field(ge=0)
    failed_reviews: int = Field(ge=0)
    status_counts: dict[str, int]
    recent_reviews: list[ReviewListItem]


class DeleteReviewResponse(APIModel):
    review_id: str
    deleted: bool
    message: str


class FeedbackRequest(APIModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    accepted: bool | None = None
    helpful: bool | None = Field(
        default=None,
        description="Alias-like convenience for accepted when rating a review",
    )
    finding_id: str | None = Field(default=None, max_length=256)
    comment: str | None = Field(default=None, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_feedback_value(self) -> FeedbackRequest:
        if self.accepted is not None and self.helpful is not None and self.accepted != self.helpful:
            raise ValueError("accepted and helpful cannot disagree")
        if (
            all(
                value is None
                for value in (
                    self.rating,
                    self.accepted,
                    self.helpful,
                    self.finding_id,
                    self.comment,
                )
            )
            and not self.metadata
        ):
            raise ValueError("at least one feedback field is required")
        return self

    @property
    def resolved_accepted(self) -> bool | None:
        return self.accepted if self.accepted is not None else self.helpful


class FeedbackResponse(APIModel):
    feedback_id: str
    review_id: str
    rating: int | None = None
    accepted: bool | None = None
    finding_id: str | None = None
    comment: str | None = None
    created_at: datetime


class ObligationsResponse(APIModel):
    review_id: str
    status: str
    obligations: list[dict[str, Any]] = Field(default_factory=list)


class MemoryItem(APIModel):
    memory_id: str
    layer: str
    key: str
    content: Any
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MemoryListResponse(APIModel):
    layer: str
    memories: list[MemoryItem] = Field(default_factory=list)


class MemoryUpsertRequest(APIModel):
    content: Any
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(APIModel):
    status: str
    service: str
    version: str
    environment: str
    storage: str
    mode: str
    ai_enabled: bool
    model: str | None = None
    api_prefix: str
    max_upload_bytes: int = Field(gt=0)
    auth_required: bool
    registration_enabled: bool
