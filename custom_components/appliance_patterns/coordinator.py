from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from .const import STATE_IDLE, STATE_RUNNING
from .ml.feature_extraction import downsample_series, window_to_series
from .ml.model import AppliancePatternModel, MatchResult
from .storage.db import PatternStorage


@dataclass
class ApplianceRuntimeState:
    state: str = STATE_IDLE
    program: str | None = None
    phase: str | None = None
    time_remaining: float | None = None
    confidence: float = 0.0
    active_power: float | None = None
    run_start: float | None = None
    last_sample: float | None = None


class ApplianceCoordinator:
    def __init__(self) -> None:
        self._listeners: list[CALLBACK_TYPE] = []
        self.data = ApplianceRuntimeState()

    def async_add_listener(self, listener: CALLBACK_TYPE) -> CALLBACK_TYPE:
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    @callback
    def async_set_state(self, state: ApplianceRuntimeState) -> None:
        self.data = state
        for listener in list(self._listeners):
            listener()


class RunTracker:
    def __init__(
        self,
        on_threshold: float,
        off_threshold: float,
        off_delay: float,
        sample_interval: int,
        window_duration: int,
        min_run_duration: int,
    ) -> None:
        self._on_threshold = on_threshold
        self._off_threshold = off_threshold
        self._off_delay = off_delay
        self._sample_interval = sample_interval
        self._window_duration = window_duration
        self._min_run_duration = min_run_duration
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
        if power >= self._on_threshold and self._state == STATE_IDLE:
            self._start_run(timestamp)
        if self._state == STATE_RUNNING:
            if power >= self._off_threshold:
                self._last_active_ts = timestamp
            record = not self._last_record_ts or timestamp - self._last_record_ts >= self._sample_interval
            if record:
                self._current_run.append((timestamp, power))
                self._last_record_ts = timestamp
            if self._last_active_ts and timestamp - self._last_active_ts >= self._off_delay:
                return self._stop_run()
        return None

    def _append_window(self, timestamp: float, power: float) -> None:
        self._window.append((timestamp, power))
        cutoff = timestamp - self._window_duration
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
        if duration >= self._min_run_duration:
            return run
        return None


class ApplianceRuntimeManager:
    def __init__(self, hass: HomeAssistant, entry, config: dict) -> None:
        self.hass = hass
        self.entry = entry
        self.config = config
        self.coordinator = ApplianceCoordinator()
        self.storage = PatternStorage(hass, entry.entry_id)
        self.model = AppliancePatternModel(config["sample_interval"])
        self.tracker = RunTracker(
            on_threshold=config["on_power"],
            off_threshold=config["off_power"],
            off_delay=config["off_delay"],
            sample_interval=config["sample_interval"],
            window_duration=config["window_duration"],
            min_run_duration=config["min_run_duration"],
        )
        self._listeners: list[CALLBACK_TYPE] = []
        self._match: MatchResult = MatchResult()

    async def async_setup(self) -> None:
        stored = await self.storage.async_load()
        self.model.load(stored.get("patterns", []))
        await self._subscribe_sensors()

    async def async_unload(self) -> None:
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()

    async def async_reset_patterns(self) -> None:
        await self.storage.async_reset()
        self.model.load([])
        self._match = MatchResult()

    async def async_import(self, payload: dict) -> None:
        await self.storage.async_import(payload)
        self.model.load(self.storage.get_patterns())

    def export(self) -> dict:
        return self.storage.export()

    async def _subscribe_sensors(self) -> None:
        for entity_id in self.config["power_sensors"]:
            unsub = async_track_state_change_event(
                self.hass,
                [entity_id],
                self._handle_power_event,
            )
            self._listeners.append(unsub)

    @callback
    def _handle_power_event(self, event: Event) -> None:
        new_state: State | None = event.data.get("new_state")
        if new_state is None:
            return
        power = self._safe_float(new_state.state)
        if power is None:
            return
        timestamp = new_state.last_changed.timestamp()
        completed = self.tracker.process_sample(timestamp, power)
        elapsed = self.tracker.current_elapsed(timestamp)
        window_series = window_to_series(self.tracker.window)
        if self.tracker.state == STATE_RUNNING and window_series:
            self._match = self.model.match_window(window_series, elapsed)
        else:
            self._match = MatchResult()
        self._publish_state(power, timestamp)
        if completed:
            self.hass.async_create_task(self._persist_completed_run(completed))

    async def _persist_completed_run(self, run: list[tuple[float, float]]) -> None:
        downsampled = downsample_series(run, self.config["sample_interval"])
        series = [value for _, value in downsampled]
        label = self.model.add_run(series)
        await self.storage.async_set_patterns(self.model.serialize())
        await self.storage.async_append_run(
            {
                "samples": run,
                "label": label,
                "appliance": self.entry.title,
                "timestamp": run[0][0] if run else None,
            }
        )

    @callback
    def _publish_state(self, power: float, timestamp: float) -> None:
        state = ApplianceRuntimeState(
            state=self.tracker.state,
            program=self._match.label if self.tracker.state == STATE_RUNNING else None,
            phase=self._match.phase if self.tracker.state == STATE_RUNNING else None,
            time_remaining=self._match.time_remaining if self.tracker.state == STATE_RUNNING else None,
            confidence=self._match.confidence if self.tracker.state == STATE_RUNNING else 0.0,
            active_power=power,
            run_start=self.tracker.run_start,
            last_sample=timestamp,
        )
        self.coordinator.async_set_state(state)

    @staticmethod
    def _safe_float(value: str) -> float | None:
        if value in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
