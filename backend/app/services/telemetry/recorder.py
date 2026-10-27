"""Gets events from the code that makes them onto the Redis stream the telemetry
service reads.

THE RULE: telemetry must never slow down or break the thing it measures.
  - `record()` is synchronous, allocation-light and cannot raise;
  - a full in-process queue drops the NEW event and counts it (it never blocks);
  - a Redis failure drops the batch and counts it (it never propagates);
  - nothing waits for a flush except shutdown, which gets a few seconds.

Events are written to Redis in batches by one background task per process. The API and
the render worker each have their own recorder.
"""

import asyncio
import contextlib
import json
import time

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.telemetry.events import Event

log = get_logger(__name__)

QUEUE_SIZE = 10_000
BATCH_SIZE = 200
FLUSH_INTERVAL = 0.5
SHUTDOWN_GRACE = 5.0


class Recorder:
    def __init__(
        self,
        *,
        queue_size: int = QUEUE_SIZE,
        batch_size: int = BATCH_SIZE,
        interval: float = FLUSH_INTERVAL,
    ) -> None:
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=queue_size)
        self._batch_size = batch_size
        self._interval = interval
        self._task: asyncio.Task[None] | None = None
        self._stopping = False
        self._redis: redis.Redis | None = None
        self.recorded = 0
        self.flushed = 0
        self.dropped = 0
        self.failed = 0

    # ------------------------------------------------------------------ writing
    def record(self, event: Event) -> bool:
        """Queue one event. Returns whether it was accepted. Never raises."""
        try:
            if not get_settings().telemetry_enabled:
                return False
            self._queue.put_nowait(event)
            self.recorded += 1
            return True
        except Exception:  # noqa: BLE001 - QueueFull, or anything else: counted, never raised
            self.dropped += 1
            return False

    # ----------------------------------------------------------------- flushing
    def _client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.Redis.from_url(
                get_settings().redis_url,
                decode_responses=True,
                # Fail fast and never retry: a stuck Redis must not stall the writer.
                socket_connect_timeout=2,
                socket_timeout=2,
                retry=Retry(NoBackoff(), 0),
            )
        return self._redis

    def _drain(self, limit: int) -> list[Event]:
        batch: list[Event] = []
        while len(batch) < limit:
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return batch

    async def _write(self, batch: list[Event]) -> None:
        if not batch:
            return
        settings = get_settings()
        try:
            pipe = self._client().pipeline(transaction=False)
            for event in batch:
                # `maxlen` (approximate) is a safety valve: if the telemetry service is
                # down for a long time, Redis must not grow without bound.
                pipe.xadd(
                    settings.telemetry_stream_key,
                    {"payload": json.dumps(event.wire(), ensure_ascii=False)},
                    maxlen=settings.telemetry_stream_maxlen,
                    approximate=True,
                )
            await pipe.execute()
            self.flushed += len(batch)
        except Exception as exc:  # noqa: BLE001 - dropped and counted, never raised
            self.failed += len(batch)
            log.warning("telemetry_flush_failed", events=len(batch), error=str(exc)[:200])

    async def flush(self) -> None:
        """Writes everything queued right now. Used by shutdown and by tests."""
        while True:
            batch = self._drain(self._batch_size)
            if not batch:
                return
            await self._write(batch)

    async def _run(self) -> None:
        last = time.monotonic()
        while not self._stopping:
            try:
                await asyncio.sleep(0.1)
                due = time.monotonic() - last >= self._interval
                if self._queue.qsize() >= self._batch_size or (due and not self._queue.empty()):
                    await self.flush()
                    last = time.monotonic()
                elif due:
                    last = time.monotonic()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - the loop must survive anything
                log.warning("telemetry_loop_error", error=str(exc)[:200])

    # ---------------------------------------------------------------- lifecycle
    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopping = False
            self._task = asyncio.get_running_loop().create_task(self._run())

    async def stop(self) -> None:
        """Stops the loop and gives the remaining events a few seconds to land."""
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
            self._task = None
        with contextlib.suppress(Exception):
            await asyncio.wait_for(self.flush(), SHUTDOWN_GRACE)
        if self._redis is not None:
            with contextlib.suppress(Exception):
                await self._redis.aclose()
            self._redis = None

    def stats(self) -> dict[str, int]:
        return {
            "queued": self._queue.qsize(),
            "recorded": self.recorded,
            "flushed": self.flushed,
            "dropped": self.dropped,
            "failed": self.failed,
        }


_recorder: Recorder | None = None


def get_recorder() -> Recorder:
    global _recorder
    if _recorder is None:
        _recorder = Recorder()
    return _recorder


def record(event: Event) -> bool:
    """Stamps the event with whoever is asking (see context.py) and queues it.

    This is the one function the rest of the code calls. It never raises."""
    try:
        from app.services.telemetry import context

        ctx = context.current()
        event.source = event.source or context.source()
        event.user_id = event.user_id or ctx.get("user_id")
        event.session_id = event.session_id or ctx.get("session_id")
        event.request_id = event.request_id or ctx.get("request_id")
        event.user_agent = event.user_agent or ctx.get("user_agent")
        return get_recorder().record(event)
    except Exception:  # noqa: BLE001
        return False
