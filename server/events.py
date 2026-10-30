"""Bus de eventos SSE para empujar movimientos a la app."""

from __future__ import annotations

import asyncio
import json
from typing import Any


class EventBus:
    def __init__(self):
        self._queues: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._queues.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)

    def publish(self, event: dict[str, Any]) -> None:
        for q in list(self._queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Si un cliente se atrasa, descartamos el evento más viejo.
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass

    def publish_transaction(self, transaction: dict, account: dict | None = None) -> None:
        self.publish(
            {
                "type": "transaction",
                "transaction": transaction,
                "account": account,
            }
        )


def sse_data(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
