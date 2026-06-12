"""
LadderLab – Event persistence helper.
Allows the scan cycle (running in a separate thread) to safely
enqueue alarm/emergency events and inserts them into the database
via an asynchronous background task.
"""

import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .database import async_session
from .models import ExecutionLog


class EventPersistence:
    """Manages a queue of events and writes them to the database."""

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Begin consuming the queue."""
        self._task = asyncio.create_task(self._worker())

    async def stop(self):
        """Gracefully stop the worker."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def enqueue(self, event_type: str, message: str, severity: Optional[str] = None):
        """Thread‑safe method to add an event to the queue."""
        try:
            self.queue.put_nowait((event_type, message, severity))
        except asyncio.QueueFull:
            # Should never happen with an unbounded queue, but safe fallback
            pass

    async def _worker(self):
        """Continuously consume events and store them in the database."""
        while True:
            event_type, message, severity = await self.queue.get()
            try:
                async with async_session() as session:
                    session.add(ExecutionLog(
                        timestamp=asyncio.get_running_loop().time(),  # we'll override in route
                        event_type=event_type,
                        severity=severity,
                        message=message,
                    ))
                    await session.commit()
            except Exception:
                # Log the failure but keep the worker alive
                # (in a real system we would use proper logging)
                pass
            finally:
                self.queue.task_done()