"""
Reconnect Controller
====================
Handles RTSP stream drop recovery with exponential back-off.

Behaviour
---------
• Each consecutive failure doubles the wait time:
      attempt 1 →  2 s
      attempt 2 →  4 s
      attempt 3 →  8 s
      attempt 4 → 16 s
      ...
      capped at max_delay_s (default 60 s)

• retries=-1  → infinite retries (never give up)
• retries=0   → no retries (fail immediately)
• retries=N   → try N times then raise StreamGaveUpError

• On a successful reconnect the back-off counter resets to zero.

• Jitter (+0–20% random) is added to each delay to prevent
  thundering-herd if many cameras drop at the same time.

Why this matters
----------------
Almost every IP camera will drop its RTSP stream occasionally —
Wi-Fi glitches, camera reboots, PoE switch hiccups.  Without auto-
reconnect the whole process dies.  A hard-coded auto-restart keeps
the system "always on" as described in the project documentation.
"""

from __future__ import annotations

import time
import random
import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class StreamGaveUpError(RuntimeError):
    """Raised when all reconnect attempts are exhausted."""


@dataclass
class ReconnectStats:
    camera_id: str
    total_reconnects: int = 0
    total_failures: int = 0
    consecutive_fails: int = 0
    last_reconnect_at: Optional[float] = None
    last_fail_reason: str = ""

    @property
    def uptime_reconnects(self) -> int:
        return self.total_reconnects


class ReconnectController:
    """
    Manages retry logic for one camera stream.

    Parameters
    ----------
    camera_id    : str
    retries      : int   — max attempts (-1 = infinite)
    base_delay_s : float — starting back-off delay in seconds (default 2)
    max_delay_s  : float — ceiling for back-off (default 60)
    jitter       : bool  — add random 0–20% jitter to each delay
    """

    def __init__(
        self,
        camera_id: str,
        retries: int = 5,
        base_delay_s: float = 2.0,
        max_delay_s: float = 60.0,
        jitter: bool = True,
    ):
        self.camera_id = camera_id
        self.retries = retries
        self.base_delay_s = base_delay_s
        self.max_delay_s = max_delay_s
        self.jitter = jitter
        self._stats = ReconnectStats(camera_id=camera_id)

    # ── Public API ────────────────────────────────────────────────

    def run_with_reconnect(
        self,
        stream_fn: Callable[[], None],
        on_reconnect: Optional[Callable[[int], None]] = None,
    ) -> None:
        """
        Call `stream_fn()` in a loop.  On any exception or return,
        apply back-off and retry.  `on_reconnect(attempt)` is called
        before each retry (use to drain FrameBuffer, log UI events, etc.).

        Raises StreamGaveUpError when retries are exhausted.

        Usage:
            ctrl = ReconnectController("cam_01", retries=5)
            ctrl.run_with_reconnect(
                stream_fn    = lambda: processor.process_stream("cam_01", url),
                on_reconnect = lambda n: buffer.drain(),
            )
        """
        attempt = 0

        while True:
            try:
                logger.info(
                    f"[Reconnect] {self.camera_id}: starting stream "
                    f"(attempt {attempt + 1})"
                )
                stream_fn()
                # stream_fn returned normally (EOF / intentional stop)
                logger.info(f"[Reconnect] {self.camera_id}: stream ended cleanly.")
                return

            except Exception as exc:
                self._stats.total_failures += 1
                self._stats.consecutive_fails += 1
                self._stats.last_fail_reason = str(exc)
                logger.warning(
                    f"[Reconnect] {self.camera_id}: stream error — {exc} "
                    f"(consecutive failures: {self._stats.consecutive_fails})"
                )

            # Check retry budget
            if self.retries != -1 and attempt >= self.retries:
                raise StreamGaveUpError(
                    f"{self.camera_id}: gave up after {attempt + 1} attempts. "
                    f"Last error: {self._stats.last_fail_reason}"
                )

            # Calculate back-off delay
            delay = min(
                self.base_delay_s * (2**attempt),
                self.max_delay_s,
            )
            if self.jitter:
                delay *= 1.0 + random.uniform(0, 0.2)

            logger.info(
                f"[Reconnect] {self.camera_id}: waiting {delay:.1f}s "
                f"before retry {attempt + 1}/{self.retries if self.retries != -1 else '∞'}"
            )
            time.sleep(delay)

            # Fire callback (e.g. drain buffer, update UI state)
            if on_reconnect:
                try:
                    on_reconnect(attempt)
                except Exception as cb_exc:
                    logger.debug(f"[Reconnect] on_reconnect callback error: {cb_exc}")

            attempt += 1
            self._stats.total_reconnects += 1
            self._stats.consecutive_fails = 0
            self._stats.last_reconnect_at = time.time()

    def reset(self) -> None:
        """Call after a successful stable period to reset failure counters."""
        self._stats.consecutive_fails = 0
        self._stats.last_fail_reason = ""

    @property
    def stats(self) -> ReconnectStats:
        return self._stats


# ─────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────


class ReconnectRegistry:
    _controllers: dict[str, ReconnectController] = {}

    def get_or_create(
        self,
        camera_id: str,
        retries: int = 5,
    ) -> ReconnectController:
        if camera_id not in self._controllers:
            self._controllers[camera_id] = ReconnectController(
                camera_id=camera_id, retries=retries
            )
        return self._controllers[camera_id]

    def all_stats(self) -> list[ReconnectStats]:
        return [c.stats for c in self._controllers.values()]


reconnect_registry = ReconnectRegistry()
