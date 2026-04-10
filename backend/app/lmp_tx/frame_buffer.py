"""
FrameBuffer — Thread-safe Bounded Frame Queue
==============================================
Sits between the RTSP reader thread and the inference thread.

Key behaviour
-------------
• Fixed maximum size (queue_size from CameraConfig).
• When FULL: drops the OLDEST frame (not the newest), so the consumer
  always processes the most recent image — never shows stale video.
• put_nowait() is used by the producer; get() blocks the consumer until
  a frame arrives (or times out).
• drain() empties the buffer instantly — useful on reconnect.
• Thread-safe: uses queue.Queue internally.

Why this matters
----------------
If inference takes 200 ms per frame but the camera sends 30 fps, the
backlog would grow by ~4 frames every second. Without a bounded buffer
the process eventually runs gigabytes of RAM and shows video from
minutes ago. A queue_size of 30 caps that at ~1 second of lag before
old frames are dropped.
"""

from __future__ import annotations

import queue
import logging
import threading
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BufferStats:
    camera_id: str
    total_enqueued: int = 0
    total_dropped: int = 0
    total_consumed: int = 0
    current_depth: int = 0
    max_depth_seen: int = 0

    @property
    def drop_rate(self) -> float:
        if self.total_enqueued == 0:
            return 0.0
        return self.total_dropped / self.total_enqueued


class FrameBuffer:
    """
    Bounded FIFO queue for one camera stream.

    Parameters
    ----------
    camera_id  : str   — for logging
    maxsize    : int   — queue_size from CameraConfig (default 30)
    """

    def __init__(self, camera_id: str, maxsize: int = 30):
        self.camera_id = camera_id
        self.maxsize = max(1, maxsize)
        self._q: queue.Queue = queue.Queue(maxsize=self.maxsize)
        self._stats = BufferStats(camera_id=camera_id)
        self._lock = threading.Lock()

    # ── Producer side ─────────────────────────────────────────────

    def put(self, frame) -> bool:
        """
        Add a frame.  If the queue is full, drop the OLDEST entry first,
        then insert the new frame so the consumer never falls behind.
        Returns True if the frame was added, False if something went wrong.
        """
        with self._lock:
            if self._q.full():
                try:
                    self._q.get_nowait()  # evict oldest
                    self._stats.total_dropped += 1
                    logger.debug(
                        f"[FrameBuffer] {self.camera_id}: buffer full — "
                        f"dropped oldest frame (total drops: {self._stats.total_dropped})"
                    )
                except queue.Empty:
                    pass  # race condition — queue drained between checks

            try:
                self._q.put_nowait(frame)
                self._stats.total_enqueued += 1
                depth = self._q.qsize()
                self._stats.current_depth = depth
                if depth > self._stats.max_depth_seen:
                    self._stats.max_depth_seen = depth
                return True
            except queue.Full:
                # Extremely unlikely after the eviction above
                self._stats.total_dropped += 1
                return False

    # ── Consumer side ─────────────────────────────────────────────

    def get(self, timeout: float = 1.0):
        """
        Block until a frame is available (or timeout expires).
        Returns the frame, or None on timeout.
        """
        try:
            frame = self._q.get(timeout=timeout)
            with self._lock:
                self._stats.total_consumed += 1
                self._stats.current_depth = self._q.qsize()
            return frame
        except queue.Empty:
            return None

    def get_nowait(self):
        """Non-blocking get. Returns None if empty."""
        try:
            frame = self._q.get_nowait()
            with self._lock:
                self._stats.total_consumed += 1
                self._stats.current_depth = self._q.qsize()
            return frame
        except queue.Empty:
            return None

    # ── Housekeeping ──────────────────────────────────────────────

    def drain(self) -> int:
        """Empty the buffer (e.g., after reconnect). Returns frames dropped."""
        dropped = 0
        while not self._q.empty():
            try:
                self._q.get_nowait()
                dropped += 1
            except queue.Empty:
                break
        with self._lock:
            self._stats.total_dropped += dropped
            self._stats.current_depth = 0
        logger.info(f"[FrameBuffer] {self.camera_id}: drained {dropped} stale frames.")
        return dropped

    @property
    def depth(self) -> int:
        return self._q.qsize()

    @property
    def stats(self) -> BufferStats:
        return self._stats

    def __repr__(self) -> str:
        return (
            f"<FrameBuffer camera={self.camera_id} "
            f"depth={self.depth}/{self.maxsize} "
            f"drops={self._stats.total_dropped}>"
        )


# ─────────────────────────────────────────────────────────────────
# Global Buffer Registry
# ─────────────────────────────────────────────────────────────────


class FrameBufferRegistry:
    """Creates and tracks one FrameBuffer per camera."""

    _buffers: dict[str, FrameBuffer] = {}

    def get_or_create(self, camera_id: str, maxsize: int = 30) -> FrameBuffer:
        if camera_id not in self._buffers:
            self._buffers[camera_id] = FrameBuffer(camera_id, maxsize)
            logger.info(
                f"[FrameBufferRegistry] Created buffer for {camera_id} "
                f"(maxsize={maxsize})"
            )
        return self._buffers[camera_id]

    def get(self, camera_id: str) -> Optional[FrameBuffer]:
        return self._buffers.get(camera_id)

    def all_stats(self) -> list[BufferStats]:
        return [b.stats for b in self._buffers.values()]

    def drain_all(self) -> dict[str, int]:
        return {cid: buf.drain() for cid, buf in self._buffers.items()}


buffer_registry = FrameBufferRegistry()
