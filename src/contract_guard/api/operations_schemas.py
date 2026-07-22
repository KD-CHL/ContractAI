"""HTTP schemas for the contract risk operations workspace."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from contract_guard.api.schemas import APIModel


class WorkItemResponse(APIModel):
    work_item_id: str
    review_id: str
    kind: str
    source_id: str | None = None
    source_ordinal: int = Field(ge=0)
    title: str
    source_payload: dict[str, Any] = Field(default_factory=dict)
    risk_level: str | None = None
    status: str
    assignee_user_id: str | None = None
    assignee_display_name: str | None = None
    assignee_email: str | None = None
    due_at: datetime | None = None
    note: str | None = None
    state_version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    document_name: str


class WorkItemListResponse(APIModel):
    items: list[WorkItemResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


class ReviewWorkItemsResponse(APIModel):
    review_id: str
    items: list[WorkItemResponse]


class WorkItemUpdateRequest(APIModel):
    expected_version: int = Field(ge=1)
    status: str | None = Field(default=None, max_length=32)
    assignee_user_id: str | None = Field(default=None, max_length=128)
    due_at: datetime | None = None
    note: str | None = Field(default=None, max_length=5000)

    @field_validator("due_at")
    @classmethod
    def due_at_must_include_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("截止时间必须包含时区")
        return value

    @model_validator(mode="after")
    def require_a_change(self) -> WorkItemUpdateRequest:
        changed_fields = self.model_fields_set.difference({"expected_version"})
        if not changed_fields:
            raise ValueError("请至少更新一个工作项字段")
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("工作项状态不能为空")
        if "note" in self.model_fields_set and self.note is not None and not self.note.strip():
            raise ValueError("备注不能为空白")
        return self


class WorkItemEventResponse(APIModel):
    event_id: str
    work_item_id: str
    actor_user_id: str | None = None
    actor_display_name: str | None = None
    action: str
    from_status: str | None = None
    to_status: str | None = None
    changes: dict[str, Any] = Field(default_factory=dict)
    note: str | None = None
    state_version: int = Field(ge=1)
    created_at: datetime


class WorkItemEventsResponse(APIModel):
    work_item_id: str
    items: list[WorkItemEventResponse]


class OperationsSummaryResponse(APIModel):
    my_open: int = Field(ge=0)
    overdue: int = Field(ge=0)
    high_risk_open: int = Field(ge=0)
    pending_approvals: int = Field(ge=0)
    completed_this_week: int = Field(ge=0)


class ReviewDecisionRequest(APIModel):
    expected_version: int = Field(ge=1)
    status: str = Field(min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=5000)

    @field_validator("note")
    @classmethod
    def note_cannot_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("审批说明不能为空白")
        return value


class ReviewDecisionResponse(APIModel):
    review_id: str
    previous_status: str
    decision_status: str
    state_version: int = Field(ge=1)
    updated_at: datetime


__all__ = [
    "OperationsSummaryResponse",
    "ReviewDecisionRequest",
    "ReviewDecisionResponse",
    "ReviewWorkItemsResponse",
    "WorkItemEventResponse",
    "WorkItemEventsResponse",
    "WorkItemListResponse",
    "WorkItemResponse",
    "WorkItemUpdateRequest",
]
