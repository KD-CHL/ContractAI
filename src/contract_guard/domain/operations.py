"""Operational state machines and errors for review follow-through.

The review workflow produces immutable, evidence-backed findings and obligations.
This module defines the smaller mutable state machines used after that analysis has
completed: review approval and the work items derived from the report.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final


class WorkItemKind(StrEnum):
    FINDING = "finding"
    OBLIGATION = "obligation"


class FindingWorkStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"


class ObligationWorkStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WAIVED = "waived"


class ReviewDecisionStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class OperationsError(RuntimeError):
    """Base class for expected operational workflow failures."""


class WorkItemNotFound(OperationsError):
    pass


class ReviewNotFound(OperationsError):
    pass


class StateConflict(OperationsError):
    """Raised when a client attempts to update a stale state version."""

    def __init__(self, *, expected: int, current: int) -> None:
        self.expected = expected
        self.current = current
        super().__init__(f"state version conflict: expected {expected}, current {current}")


class InvalidTransition(OperationsError):
    """Raised when an entity's state machine rejects a requested transition."""

    def __init__(self, *, entity: str, current: str, target: str) -> None:
        self.entity = entity
        self.current = current
        self.target = target
        super().__init__(f"invalid {entity} transition: {current} -> {target}")


class AssignmentError(OperationsError):
    pass


class ApprovalBlocked(OperationsError):
    """Raised when unresolved high-risk work blocks review approval."""

    def __init__(self, blocker_ids: tuple[str, ...]) -> None:
        self.blocker_ids = blocker_ids
        super().__init__(
            f"审批被阻塞：仍有 {len(blocker_ids)} 个高风险工作项未解决或接受，"
            "请先完成处置后再批准。"
        )


class InvalidDueAt(OperationsError):
    pass


class _UnsetType:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"


UNSET: Final = _UnsetType()
UnsetType = _UnsetType


_FINDING_TRANSITIONS: Final[dict[FindingWorkStatus, frozenset[FindingWorkStatus]]] = {
    FindingWorkStatus.OPEN: frozenset(
        {
            FindingWorkStatus.IN_PROGRESS,
            FindingWorkStatus.RESOLVED,
            FindingWorkStatus.ACCEPTED,
        }
    ),
    FindingWorkStatus.IN_PROGRESS: frozenset(
        {
            FindingWorkStatus.OPEN,
            FindingWorkStatus.RESOLVED,
            FindingWorkStatus.ACCEPTED,
        }
    ),
    FindingWorkStatus.RESOLVED: frozenset({FindingWorkStatus.OPEN}),
    FindingWorkStatus.ACCEPTED: frozenset({FindingWorkStatus.OPEN}),
}

_OBLIGATION_TRANSITIONS: Final[dict[ObligationWorkStatus, frozenset[ObligationWorkStatus]]] = {
    ObligationWorkStatus.PENDING: frozenset(
        {
            ObligationWorkStatus.IN_PROGRESS,
            ObligationWorkStatus.COMPLETED,
            ObligationWorkStatus.WAIVED,
        }
    ),
    ObligationWorkStatus.IN_PROGRESS: frozenset(
        {
            ObligationWorkStatus.PENDING,
            ObligationWorkStatus.COMPLETED,
            ObligationWorkStatus.WAIVED,
        }
    ),
    ObligationWorkStatus.COMPLETED: frozenset({ObligationWorkStatus.PENDING}),
    ObligationWorkStatus.WAIVED: frozenset({ObligationWorkStatus.PENDING}),
}

_REVIEW_TRANSITIONS: Final[dict[ReviewDecisionStatus, frozenset[ReviewDecisionStatus]]] = {
    ReviewDecisionStatus.DRAFT: frozenset({ReviewDecisionStatus.IN_REVIEW}),
    ReviewDecisionStatus.IN_REVIEW: frozenset(
        {ReviewDecisionStatus.APPROVED, ReviewDecisionStatus.REJECTED}
    ),
    ReviewDecisionStatus.REJECTED: frozenset({ReviewDecisionStatus.IN_REVIEW}),
    ReviewDecisionStatus.APPROVED: frozenset({ReviewDecisionStatus.IN_REVIEW}),
}


def initial_work_status(kind: WorkItemKind) -> str:
    if kind is WorkItemKind.FINDING:
        return FindingWorkStatus.OPEN.value
    return ObligationWorkStatus.PENDING.value


def terminal_work_statuses(kind: WorkItemKind) -> frozenset[str]:
    if kind is WorkItemKind.FINDING:
        return frozenset({FindingWorkStatus.RESOLVED.value, FindingWorkStatus.ACCEPTED.value})
    return frozenset({ObligationWorkStatus.COMPLETED.value, ObligationWorkStatus.WAIVED.value})


def validate_work_status(kind: WorkItemKind, value: str) -> None:
    try:
        if kind is WorkItemKind.FINDING:
            FindingWorkStatus(value)
        else:
            ObligationWorkStatus(value)
    except ValueError as exc:
        raise InvalidTransition(entity=kind.value, current=value, target=value) from exc


def validate_work_transition(
    kind: WorkItemKind,
    *,
    current: str,
    target: str,
    note: str | None,
) -> None:
    """Validate one status transition and its mandatory disposition note."""

    if kind is WorkItemKind.FINDING:
        try:
            current_status = FindingWorkStatus(current)
            target_status = FindingWorkStatus(target)
        except ValueError as exc:
            raise InvalidTransition(entity=kind.value, current=current, target=target) from exc
        allowed = _FINDING_TRANSITIONS[current_status]
        requires_note = target_status in {
            FindingWorkStatus.RESOLVED,
            FindingWorkStatus.ACCEPTED,
        }
        if target_status == current_status:
            return
        if target_status not in allowed:
            raise InvalidTransition(entity=kind.value, current=current, target=target)
        if requires_note and not (note or "").strip():
            raise InvalidTransition(entity=kind.value, current=current, target=target)
        return

    try:
        current_obligation_status = ObligationWorkStatus(current)
        target_obligation_status = ObligationWorkStatus(target)
    except ValueError as exc:
        raise InvalidTransition(entity=kind.value, current=current, target=target) from exc
    allowed_obligation_statuses = _OBLIGATION_TRANSITIONS[current_obligation_status]
    if target_obligation_status == current_obligation_status:
        return
    if target_obligation_status not in allowed_obligation_statuses:
        raise InvalidTransition(entity=kind.value, current=current, target=target)
    if target_obligation_status is ObligationWorkStatus.WAIVED and not (note or "").strip():
        raise InvalidTransition(entity=kind.value, current=current, target=target)


def validate_review_transition(
    *,
    current: str,
    target: str,
    note: str | None,
) -> None:
    try:
        current_status = ReviewDecisionStatus(current)
        target_status = ReviewDecisionStatus(target)
    except ValueError as exc:
        raise InvalidTransition(entity="review", current=current, target=target) from exc
    if target_status == current_status or target_status not in _REVIEW_TRANSITIONS[current_status]:
        raise InvalidTransition(entity="review", current=current, target=target)
    if target_status is ReviewDecisionStatus.REJECTED and not (note or "").strip():
        raise InvalidTransition(entity="review", current=current, target=target)


def require_aware_due_at(value: datetime | None) -> None:
    if value is None:
        return
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidDueAt("due_at must include a timezone offset")


__all__ = [
    "ApprovalBlocked",
    "AssignmentError",
    "FindingWorkStatus",
    "InvalidDueAt",
    "InvalidTransition",
    "ObligationWorkStatus",
    "OperationsError",
    "ReviewDecisionStatus",
    "ReviewNotFound",
    "StateConflict",
    "UNSET",
    "UnsetType",
    "WorkItemKind",
    "WorkItemNotFound",
    "initial_work_status",
    "require_aware_due_at",
    "terminal_work_statuses",
    "validate_review_transition",
    "validate_work_status",
    "validate_work_transition",
]
