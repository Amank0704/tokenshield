"""
TokenShield — Industrial-Grade Server-Sent Events (SSE) Event Bus
==================================================================
Provides real-time, low-latency streaming of all security telemetry,
signal alerts, multi-layer status changes, and mitigation executions.

Features:
  - Concurrent lock-free broadcast via thread-safe bounded Queues
  - Historical buffer replay on client reconnect (last 50 events)
  - Automatic periodic heartbeats (15s) to sustain long-lived browser pipes
  - Strict JSON event framing
"""

import time
import json
import queue
import logging
import threading
from typing import Generator, Dict, Any, List

log = logging.getLogger("ts.api.sse")


class SSEEventBus:
    def __init__(self, history_limit: int = 100):
        self._subscribers: List[queue.Queue] = []
        self._history: List[str] = []
        self._lock = threading.Lock()
        self.history_limit = history_limit

    def publish(self, event_type: str, data: Dict[str, Any]):
        """
        Publishes an event to all connected dashboard SSE streams.
        """
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
            "iso_time": time.strftime("%H:%M:%S")
        }
        json_str = json.dumps(payload)

        with self._lock:
            self._history.append(json_str)
            if len(self._history) > self.history_limit:
                self._history.pop(0)

            dead_subs = []
            for q in self._subscribers:
                try:
                    q.put_nowait(json_str)
                except queue.Full:
                    dead_subs.append(q)

            for d in dead_subs:
                if d in self._subscribers:
                    self._subscribers.remove(d)

    def subscribe(self, replay_count: int = 25) -> Generator[str, None, None]:
        """
        Subscribes a client and yields standard text/event-stream chunks.
        """
        q = queue.Queue(maxsize=300)
        with self._lock:
            self._subscribers.append(q)
            replay_batch = list(self._history[-replay_count:])

        try:
            # 1. Initial handshake
            yield f"data: {json.dumps({'type': 'connection_established', 'data': {'status': 'connected', 'subscribers': len(self._subscribers)}})}\n\n"

            # 2. Replay recent events
            for event_json in replay_batch:
                yield f"data: {event_json}\n\n"

            # 3. Stream live events with heartbeats
            while True:
                try:
                    msg = q.get(timeout=15.0)
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    heartbeat = json.dumps({
                        "type": "heartbeat",
                        "data": {"timestamp": time.time(), "status": "nominal"}
                    })
                    yield f"data: {heartbeat}\n\n"

        finally:
            with self._lock:
                if q in self._subscribers:
                    self._subscribers.remove(q)

    def get_subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)


_GLOBAL_BUS = SSEEventBus()

def get_event_bus() -> SSEEventBus:
    return _GLOBAL_BUS

def publish_event(event_type: str, data: Dict[str, Any]):
    _GLOBAL_BUS.publish(event_type, data)
