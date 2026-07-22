from dataclasses import dataclass

import pytest

from contract_guard.services.cache import InMemoryReviewCache, review_cache_key
from contract_guard.services.storage import MemoryLayer, SQLiteReviewRepository


@dataclass
class ExampleReport:
    contract_id: str
    obligations: tuple[dict[str, str], ...]


def test_sqlite_review_lifecycle_and_scope_isolation() -> None:
    repository = SQLiteReviewRepository(":memory:")
    review = repository.create_review(
        org_id="org-a",
        session_id="session-a",
        fingerprint="abc123",
        document_name="contract.txt",
        media_type="text/plain",
        contract_id="contract-1",
        metadata={"source": "test"},
    )

    assert review.status == "processing"
    assert repository.get_review(review.id, org_id="org-b", session_id="session-a") is None
    assert repository.get_review(review.id, org_id="org-a", session_id="session-b") is None

    completed = repository.update_review(
        review.id,
        org_id="org-a",
        session_id="session-a",
        status="completed",
        report=ExampleReport(
            contract_id="contract-1",
            obligations=({"obligation_id": "o-1", "action": "pay"},),
        ),
    )

    assert completed is not None
    assert completed.report["contract_id"] == "contract-1"
    assert repository.list_obligations(review.id, org_id="org-a", session_id="session-a") == [
        {"obligation_id": "o-1", "action": "pay"}
    ]
    assert repository.healthcheck()


def test_feedback_cannot_cross_scope() -> None:
    repository = SQLiteReviewRepository(":memory:")
    review = repository.create_review(
        org_id="org-a",
        session_id="session-a",
        fingerprint="fingerprint",
        document_name="contract.txt",
        media_type="text/plain",
    )

    assert (
        repository.add_feedback(
            review.id,
            org_id="org-b",
            session_id="session-a",
            rating=5,
        )
        is None
    )
    feedback = repository.add_feedback(
        review.id,
        org_id="org-a",
        session_id="session-a",
        rating=4,
        accepted=True,
        comment="Useful",
    )

    assert feedback is not None
    assert feedback.rating == 4
    assert len(repository.list_feedback(review.id, org_id="org-a", session_id="session-a")) == 1


async def test_fingerprint_cache_is_scoped_and_expires() -> None:
    current_time = 100.0
    cache = InMemoryReviewCache(default_ttl_seconds=10, clock=lambda: current_time)
    await cache.set(
        {"result": "org-a"},
        org_id="org-a",
        session_id="session-a",
        fingerprint="fingerprint",
    )

    assert await cache.get(org_id="org-a", session_id="session-a", fingerprint="fingerprint") == {
        "result": "org-a"
    }
    assert (
        await cache.get(org_id="org-b", session_id="session-a", fingerprint="fingerprint") is None
    )
    current_time = 111.0
    assert (
        await cache.get(org_id="org-a", session_id="session-a", fingerprint="fingerprint") is None
    )


def test_cache_key_contains_document_fingerprint_but_not_tenant_ids() -> None:
    key = review_cache_key(
        org_id="private-org",
        session_id="private-session",
        fingerprint="abc123",
    )

    assert "abc123" in key
    assert "private-org" not in key
    assert "private-session" not in key


def test_rating_is_validated() -> None:
    repository = SQLiteReviewRepository(":memory:")
    review = repository.create_review(
        org_id="org",
        session_id="session",
        fingerprint="fingerprint",
        document_name="contract.txt",
        media_type="text/plain",
    )

    with pytest.raises(ValueError, match="between 1 and 5"):
        repository.add_feedback(
            review.id,
            org_id="org",
            session_id="session",
            rating=6,
        )


def test_four_memory_layers_upsert_retrieve_and_isolate() -> None:
    repository = SQLiteReviewRepository(":memory:")
    for layer in MemoryLayer:
        memory = repository.upsert_memory(
            org_id="org-a",
            session_id="session-a",
            layer=layer,
            key=f"{layer.value}-key",
            content={"value": layer.value},
        )
        assert memory.layer is layer

    # Global memory is organization-scoped and visible regardless of session.
    global_memory = repository.retrieve_memory(
        "global-key",
        org_id="org-a",
        session_id="another-session",
        layer=MemoryLayer.GLOBAL,
    )
    assert global_memory is not None
    assert global_memory.session_id is None

    # Every other layer remains scoped to the exact session.
    assert (
        repository.retrieve_memory(
            "profile-key",
            org_id="org-a",
            session_id="session-b",
            layer=MemoryLayer.PROFILE,
        )
        is None
    )
    assert (
        repository.retrieve_memory(
            "profile-key",
            org_id="org-b",
            session_id="session-a",
            layer=MemoryLayer.PROFILE,
        )
        is None
    )

    original = repository.retrieve_memory(
        "profile-key",
        org_id="org-a",
        session_id="session-a",
        layer=MemoryLayer.PROFILE,
    )
    updated = repository.upsert_memory(
        org_id="org-a",
        session_id="session-a",
        layer=MemoryLayer.PROFILE,
        key="profile-key",
        content={"value": "updated"},
    )
    assert original is not None
    assert updated.id == original.id
    assert updated.content == {"value": "updated"}


def test_non_global_memory_requires_session() -> None:
    repository = SQLiteReviewRepository(":memory:")

    with pytest.raises(ValueError, match="session_id is required"):
        repository.upsert_memory(
            org_id="org",
            session_id=None,
            layer=MemoryLayer.EPISODIC,
            key="event",
            content={},
        )
