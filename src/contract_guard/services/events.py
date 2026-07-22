"""Review lifecycle events and pluggable delivery adapters."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any, Protocol
from uuid import uuid4


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Event:
    name: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    org_id: str | None = None
    session_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=_now)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "occurred_at": self.occurred_at.isoformat(),
            "org_id": self.org_id,
            "session_id": self.session_id,
            "payload": dict(self.payload),
        }


EventHandler = Callable[[Event], None | Awaitable[None]]
Unsubscribe = Callable[[], None]


class EventBus(Protocol):
    """Minimal interface required by the platform orchestration layer."""

    async def publish(self, event: Event) -> None: ...


class SubscribableEventBus(EventBus, Protocol):
    def subscribe(self, event_name: str, handler: EventHandler) -> Unsubscribe: ...


class LocalEventBus:
    """In-process pub/sub bus with deterministic handler snapshots."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._lock = RLock()

    def subscribe(self, event_name: str, handler: EventHandler) -> Unsubscribe:
        if not event_name:
            raise ValueError("event_name cannot be empty")
        with self._lock:
            handlers = self._handlers.setdefault(event_name, [])
            handlers.append(handler)

        def unsubscribe() -> None:
            with self._lock:
                current = self._handlers.get(event_name)
                if current and handler in current:
                    current.remove(handler)
                    if not current:
                        self._handlers.pop(event_name, None)

        return unsubscribe

    async def publish(self, event: Event) -> None:
        with self._lock:
            handlers = tuple(self._handlers.get(event.name, ())) + tuple(
                self._handlers.get("*", ())
            )
        if not handlers:
            return

        awaitables: list[Awaitable[None]] = []
        for handler in handlers:
            result = handler(event)
            if inspect.isawaitable(result):
                awaitables.append(result)
        if awaitables:
            await asyncio.gather(*awaitables)


class CompositeEventBus:
    """Fan an event out to local and remote publishers."""

    def __init__(self, publishers: Sequence[EventBus]) -> None:
        self.publishers = tuple(publishers)

    async def publish(self, event: Event) -> None:
        if self.publishers:
            await asyncio.gather(*(publisher.publish(event) for publisher in self.publishers))


class KafkaProducer(Protocol):
    """Producer shape used by aiokafka-compatible adapters."""

    def send_and_wait(
        self, topic: str, value: bytes, *, key: bytes | None = None
    ) -> Any | Awaitable[Any]: ...


class KafkaEventBus:
    """Outbound Kafka adapter with an injected producer (no hard dependency)."""

    def __init__(
        self,
        producer: KafkaProducer,
        *,
        topic_prefix: str = "contractguard",
    ) -> None:
        self.producer = producer
        self.topic_prefix = topic_prefix.rstrip(".")

    async def publish(self, event: Event) -> None:
        topic = f"{self.topic_prefix}.{event.name}" if self.topic_prefix else event.name
        encoded = json.dumps(
            event.as_dict(), ensure_ascii=False, separators=(",", ":"), default=str
        ).encode("utf-8")
        partition_key = (event.org_id or event.id).encode("utf-8")
        result = self.producer.send_and_wait(topic, encoded, key=partition_key)
        if inspect.isawaitable(result):
            await result


class RedisPublisher(Protocol):
    """Client shape used by redis-py sync and asyncio clients."""

    def publish(self, channel: str, message: str) -> Any | Awaitable[Any]: ...


class RedisEventBus:
    """Outbound Redis pub/sub adapter with an injected client."""

    def __init__(
        self,
        client: RedisPublisher,
        *,
        channel_prefix: str = "contractguard",
    ) -> None:
        self.client = client
        self.channel_prefix = channel_prefix.rstrip(".")

    async def publish(self, event: Event) -> None:
        channel = f"{self.channel_prefix}.{event.name}" if self.channel_prefix else event.name
        encoded = json.dumps(
            event.as_dict(), ensure_ascii=False, separators=(",", ":"), default=str
        )
        result = self.client.publish(channel, encoded)
        if inspect.isawaitable(result):
            await result


async def emit(
    bus: EventBus,
    name: str,
    payload: Mapping[str, Any] | None = None,
    *,
    org_id: str | None = None,
    session_id: str | None = None,
) -> Event:
    """Create and publish an event, returning its generated envelope."""

    event = Event(
        name=name,
        payload=dict(payload or {}),
        org_id=org_id,
        session_id=session_id,
    )
    await bus.publish(event)
    return event


InMemoryEventBus = LocalEventBus
KafkaEventBusAdapter = KafkaEventBus
RedisEventBusAdapter = RedisEventBus
