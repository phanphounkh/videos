import asyncio
from collections.abc import Coroutine
from typing import Any

# asyncio keeps only a weak reference to a task: with nothing else holding it, a
# background loop can be garbage-collected mid-run. spawn() keeps it alive.
_tasks: set[asyncio.Task] = set()


def spawn(coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return task
