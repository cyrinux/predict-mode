from custom_components.appliance_patterns.ml.model import AppliancePatternModel


def test_model_predicts_time_remaining() -> None:
    model = AppliancePatternModel(sample_interval=5)
    run = [float(value) for value in range(20)] * 3
    label = model.add_run(run)
    assert label is not None
    window = run[:30]
    elapsed = len(window) * 5
    match = model.match_window(window, elapsed)
    assert match.label == label
    assert match.time_remaining is not None
    assert match.time_remaining >= 0
    assert match.confidence > 0
