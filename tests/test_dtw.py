from custom_components.appliance_patterns.ml.dtw import dtw_distance


def test_dtw_distance_identical_series() -> None:
    assert dtw_distance([1, 2, 3, 4], [1, 2, 3, 4]) == 0


def test_dtw_distance_handles_misalignment() -> None:
    distance = dtw_distance([0, 1, 0], [1, 0, 1])
    assert distance > 0
    assert distance < 3
