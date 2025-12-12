from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from custom_components.appliance_patterns.const import STATE_IDLE
from custom_components.appliance_patterns.run_tracker import RunTracker
from custom_components.appliance_patterns.ml.model import AppliancePatternModel

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "washing_machine_history.csv"


def _load_history() -> list[tuple[float, float]]:
    samples: list[tuple[float, float]] = []
    if not FIXTURE.exists():
        raise FileNotFoundError(FIXTURE)
    with FIXTURE.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            state_raw = row["state"]
            if state_raw.lower() in {"unavailable", "unknown"}:
                continue
            try:
                state = float(state_raw)
            except ValueError:
                continue
            stamp = datetime.fromisoformat(row["last_changed"].replace("Z", "+00:00")).timestamp()
            samples.append((stamp, state))
    return samples


def test_run_tracker_detects_real_cycle() -> None:
    samples = _load_history()
    tracker = RunTracker(
        on_threshold=15.0,
        off_threshold=5.0,
        off_delay=120,
        sample_interval=5,
        window_duration=5400,
        min_run_duration=600,
    )
    completed = None
    for timestamp, power in samples:
        completed = tracker.process_sample(timestamp, power)
        if completed is not None:
            break
    assert tracker.state == STATE_IDLE
    assert completed is not None
    assert len(completed) > 50


def test_model_matches_real_cycle() -> None:
    samples = _load_history()
    active_series = [power for _, power in samples if power > 0]
    assert active_series, "history file must contain non-zero readings"
    model = AppliancePatternModel(sample_interval=5)
    label = model.add_run(active_series)
    assert label is not None
    window = active_series[: min(180, len(active_series))]
    match = model.match_window(window, elapsed=len(window) * 5)
    assert match.label == label
    assert match.time_remaining is not None
    assert match.confidence > 0
