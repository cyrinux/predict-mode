from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from .const import STATE_IDLE, STATE_RUNNING


@dataclass
class RunTracker:
    on_threshold: float
    off_threshold: float
    off_delay: float
    sample_interval: int
    window_duration: int
    min_run_duration: int

    def __post_init__(self) -> None:
        self._window: deque[tuple[float, float]] = deque()
        self._state = STATE_IDLE
        self._current_run: list[tuple[float, float]] = []
        self._last_sample_ts: float | None = None
        self._last_record_ts: float | None = None
        self._last_active_ts: float | None = None
        self._run_start: float | None = None

    @property
    def state(self) -> str:
        return self._state

    @property
    def run_start(self) -> float | None:
        return self._run_start

    @property
    def window(self) -> Iterable[tuple[float, float]]:
        return list(self._window)

    def current_elapsed(self, timestamp: float | None = None) -> float:
        if self._state != STATE_RUNNING or self._run_start is None:
            return 0.0
        current = timestamp or self._last_sample_ts or self._run_start
        return max(0.0, current - self._run_start)

    def process_sample(self, timestamp: float, power: float) -> list[tuple[float, float]] | None:
        self._append_window(timestamp, power)
        self._last_sample_ts = timestamp
        if power >= self.on_threshold and self._state == STATE_IDLE:
            self._start_run(timestamp)
        if self._state == STATE_RUNNING:
            if power >= self.off_threshold:
                self._last_active_ts = timestamp
            record = not self._last_record_ts or timestamp - self._last_record_ts >= self.sample_interval
            if record:
                self._current_run.append((timestamp, power))
                self._last_record_ts = timestamp
            if self._last_active_ts and timestamp - self._last_active_ts >= self.off_delay:
                return self._stop_run()
        return None

    def _append_window(self, timestamp: float, power: float) -> None:
        self._window.append((timestamp, power))
        cutoff = timestamp - self.window_duration
        while self._window and self._window[0][0] < cutoff:
            self._window.popleft()

    def _start_run(self, timestamp: float) -> None:
        self._state = STATE_RUNNING
        self._current_run = []
        self._run_start = timestamp
        self._last_active_ts = timestamp
        self._last_record_ts = None

    def _stop_run(self) -> list[tuple[float, float]] | None:
        if self._run_start is None:
            self._state = STATE_IDLE
            self._current_run = []
            return None
        duration = self._current_run[-1][0] - self._run_start if self._current_run else 0.0
        run = list(self._current_run)
        self._state = STATE_IDLE
        self._current_run = []
        self._run_start = None
        self._last_active_ts = None
        if duration >= self.min_run_duration:
            return run
        return None
