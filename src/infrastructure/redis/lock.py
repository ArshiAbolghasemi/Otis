"""Cross-worker mutual exclusion, backed by Redis.

AI Farm works out of fixed directories on disk, so two concurrent runs would
corrupt each other. Every run takes this lock first; a job that cannot take it
re-queues itself instead of waiting.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from redis import Redis
from redis.exceptions import LockError

from otis.logging import get_logger

logger = get_logger(__name__)


@contextmanager
def try_lock(redis_url: str, key: str, ttl_seconds: int) -> Iterator[bool]:
    """Yield whether ``key`` was acquired, releasing it on the way out.

    The lock is never waited on: it either is free now or it is not. ``ttl``
    caps how long a crashed worker can keep it, so it must exceed the longest
    expected run.
    """
    client = Redis.from_url(redis_url)
    lock = client.lock(key, timeout=ttl_seconds, thread_local=False)
    acquired = lock.acquire(blocking=False)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            try:
                lock.release()
            except LockError:
                # The TTL expired mid-run; someone else may hold it now.
                logger.warning("Lock %s had already expired when releasing", key)
        client.close()
