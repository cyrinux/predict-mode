from custom_components.appliance_patterns.const import STATE_IDLE, STATE_RUNNING
from custom_components.appliance_patterns.run_tracker import RunTracker


def test_run_tracker_detects_complete_cycle() -> None:
    tracker = RunTracker(
        on_threshold=10,
        off_threshold=4,
        off_delay=15,
        sample_interval=5,
        window_duration=600,
        min_run_duration=30,
    )
    timestamp = 0.0
    for _ in range(5):
        tracker.process_sample(timestamp, 1)
        timestamp += 5
    for _ in range(12):
        tracker.process_sample(timestamp, 20)
        timestamp += 5
    assert tracker.state == STATE_RUNNING
    completed = None
    for _ in range(6):
        completed = tracker.process_sample(timestamp, 0.5)
        timestamp += 5
        if completed is not None:
            break
    assert tracker.state == STATE_IDLE
    assert completed is not None
    assert len(completed) >= 6
