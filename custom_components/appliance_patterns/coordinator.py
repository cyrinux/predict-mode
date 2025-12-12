from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor
from statistics import mean
from typing import Sequence

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_MIN_RUN_DURATION,
    CONF_OFF_DELAY,
    CONF_OFF_POWER,
    CONF_ON_POWER,
    CONF_SAMPLE_INTERVAL,
    CONF_WINDOW_DURATION,
    STATE_IDLE,
    STATE_RUNNING,
)
from .ml.feature_extraction import downsample_series, window_to_series
from .ml.model import AppliancePatternModel, MatchResult
from .run_tracker import RunTracker
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


class ApplianceRuntimeManager:
    def __init__(self, hass: HomeAssistant, entry, config: dict) -> None:
        self.hass = hass
        self.entry = entry
        self.config = config
        self.coordinator = ApplianceCoordinator()
        self.storage = PatternStorage(hass, entry.entry_id)
        self.model = AppliancePatternModel(config["sample_interval"])
        self._rebuild_tracker()
        self._listeners: list[CALLBACK_TYPE] = []
        self._match: MatchResult = MatchResult()

    def _rebuild_tracker(self) -> None:
        self.tracker = RunTracker(
            on_threshold=self.config["on_power"],
            off_threshold=self.config["off_power"],
            off_delay=self.config["off_delay"],
            sample_interval=self.config["sample_interval"],
            window_duration=self.config["window_duration"],
            min_run_duration=self.config["min_run_duration"],
        )

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

    async def async_auto_tune(self) -> dict[str, float]:
        await self.storage.async_load()
        runs = self._recent_runs(self.storage.get_runs())
        if not runs:
            raise HomeAssistantError("Aucun cycle complet n'est disponible pour l'auto-calibrage.")
        derived = self._derive_parameters(runs)
        new_options = {**self.entry.options, **derived}
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)
        self._apply_derived_settings(derived)
        return derived

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

    def _apply_derived_settings(self, derived: dict[str, float]) -> None:
        for key in (
            CONF_ON_POWER,
            CONF_OFF_POWER,
            CONF_OFF_DELAY,
            CONF_SAMPLE_INTERVAL,
            CONF_WINDOW_DURATION,
            CONF_MIN_RUN_DURATION,
        ):
            if key in derived:
                self.config[key] = derived[key]
        self.config["on_power"] = self.config[CONF_ON_POWER]
        self.config["off_power"] = self.config[CONF_OFF_POWER]
        self.config["off_delay"] = self.config[CONF_OFF_DELAY]
        self.config["sample_interval"] = self.config[CONF_SAMPLE_INTERVAL]
        self.config["window_duration"] = self.config[CONF_WINDOW_DURATION]
        self.config["min_run_duration"] = self.config[CONF_MIN_RUN_DURATION]
        self.model._sample_interval = self.config["sample_interval"]
        self._rebuild_tracker()

    def _recent_runs(self, raw_runs: list[dict]) -> list[list[tuple[float, float]]]:
        normalized: list[list[tuple[float, float]]] = []
        for run in reversed(raw_runs):
            samples = run.get("samples")
            if not samples:
                continue
            converted: list[tuple[float, float]] = []
            for item in samples:
                if not isinstance(item, Sequence) or len(item) != 2:
                    continue
                try:
                    ts = float(item[0])
                    power = float(item[1])
                except (TypeError, ValueError):
                    continue
                converted.append((ts, power))
            if len(converted) < 3:
                continue
            converted.sort(key=lambda sample: sample[0])
            normalized.append(converted)
            if len(normalized) >= 5:
                break
        return normalized

    def _derive_parameters(self, runs: list[list[tuple[float, float]]]) -> dict[str, float]:
        values: list[float] = []
        durations: list[float] = []
        sampling: list[float] = []
        for samples in runs:
            duration = samples[-1][0] - samples[0][0]
            if duration <= 0:
                continue
            durations.append(duration)
            values.extend(power for _, power in samples)
            intervals = [
                samples[idx][0] - samples[idx - 1][0]
                for idx in range(1, len(samples))
                if samples[idx][0] > samples[idx - 1][0]
            ]
            if intervals:
                sampling.append(sum(intervals) / len(intervals))
        if len(values) < 3 or not durations:
            raise HomeAssistantError("Cycles insuffisants pour dériver des paramètres fiables.")
        sorted_values = sorted(values)
        baseline = self._percentile(sorted_values, 0.2)
        active = self._percentile(sorted_values, 0.7)
        if active <= baseline:
            active = baseline + max(5.0, baseline * 0.5)
        off_power = round(max(1.0, baseline * 1.2), 1)
        on_power = round(max(off_power + 1.0, baseline + (active - baseline) * 0.6), 1)
        mean_duration = mean(durations)
        window_duration = int(min(7200, max(600, mean_duration * 1.2)))
        min_run_duration = int(max(60, min(mean_duration * 0.3, window_duration)))
        if sampling:
            sample_interval = int(max(2, min(10, round(mean(sampling)))))
        else:
            sample_interval = self.config["sample_interval"]
        pauses = [self._longest_low_power(samples, off_power) for samples in runs]
        longest_pause = max(pauses) if pauses else 0.0
        off_delay = int(min(300, max(30, longest_pause * 1.2 if longest_pause else 90)))
        return {
            CONF_ON_POWER: on_power,
            CONF_OFF_POWER: off_power,
            CONF_OFF_DELAY: off_delay,
            CONF_SAMPLE_INTERVAL: sample_interval,
            CONF_WINDOW_DURATION: window_duration,
            CONF_MIN_RUN_DURATION: min_run_duration,
        }

    @staticmethod
    def _percentile(values: Sequence[float], percentile: float) -> float:
        if not values:
            return 0.0
        if percentile <= 0:
            return values[0]
        if percentile >= 1:
            return values[-1]
        index = (len(values) - 1) * percentile
        lower = floor(index)
        upper = ceil(index)
        if lower == upper:
            return values[int(index)]
        fraction = index - lower
        return values[lower] + (values[upper] - values[lower]) * fraction

    @staticmethod
    def _longest_low_power(samples: list[tuple[float, float]], threshold: float) -> float:
        longest = 0.0
        start: float | None = None
        for timestamp, power in samples:
            if power <= threshold:
                if start is None:
                    start = timestamp
            else:
                if start is not None:
                    longest = max(longest, timestamp - start)
                    start = None
        if start is not None:
            longest = max(longest, samples[-1][0] - start)
        return longest

    @staticmethod
    def _safe_float(value: str) -> float | None:
        if value in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
