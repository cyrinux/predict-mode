from __future__ import annotations

from math import sqrt
from statistics import mean, pstdev
from typing import Iterable


def downsample_series(samples: Iterable[tuple[float, float]], interval: int) -> list[tuple[float, float]]:
    ordered = sorted(samples, key=lambda item: item[0])
    if not ordered:
        return []
    bucket_start = ordered[0][0]
    bucket: list[float] = []
    result: list[tuple[float, float]] = []
    for timestamp, value in ordered:
        if timestamp - bucket_start >= interval and bucket:
            result.append((bucket_start, sum(bucket) / len(bucket)))
            bucket = []
            while timestamp - bucket_start >= interval:
                bucket_start += interval
        bucket.append(value)
    if bucket:
        result.append((bucket_start, sum(bucket) / len(bucket)))
    return result


def normalize_series(series: list[float]) -> list[float]:
    if not series:
        return []
    low = min(series)
    high = max(series)
    span = high - low
    if span == 0:
        midpoint = 0.5
        return [midpoint] * len(series)
    return [(value - low) / span for value in series]


def extract_features(series: list[float], sample_interval: int) -> dict[str, float]:
    if not series:
        return {
            "duration": 0.0,
            "mean": 0.0,
            "peak": 0.0,
            "std": 0.0,
        }
    avg = mean(series)
    peak = max(series)
    deviation = pstdev(series) if len(series) > 1 else 0.0
    duration = len(series) * sample_interval
    return {"duration": duration, "mean": avg, "peak": peak, "std": deviation}


def segment_phases(series: list[float], minimum_samples: int = 10) -> list[dict[str, float]]:
    if not series:
        return []
    if len(series) <= minimum_samples:
        return [
            {
                "name": "phase_1",
                "start_ratio": 0.0,
                "end_ratio": 1.0,
            }
        ]
    std = pstdev(series) if len(series) > 1 else 0.0
    threshold = max(std * 0.2, 0.05)
    segments: list[dict[str, float]] = []
    start = 0
    current_sign = 0
    for idx in range(1, len(series)):
        delta = series[idx] - series[idx - 1]
        sign = 0
        if delta > threshold:
            sign = 1
        elif delta < -threshold:
            sign = -1
        if current_sign == 0 and sign != 0:
            current_sign = sign
        if sign != 0 and current_sign != sign and idx - start >= minimum_samples:
            segments.append((start, idx))
            start = idx
            current_sign = sign
    segments.append((start, len(series)))
    normalized: list[dict[str, float]] = []
    total = len(series)
    for index, (seg_start, seg_end) in enumerate(segments, start=1):
        normalized.append(
            {
                "name": f"phase_{index}",
                "start_ratio": seg_start / total,
                "end_ratio": seg_end / total,
            }
        )
    return normalized


def window_to_series(window: Iterable[tuple[float, float]]) -> list[float]:
    return [value for _, value in sorted(window, key=lambda item: item[0])]


def series_variance(series: list[float]) -> float:
    if len(series) <= 1:
        return 0.0
    deviation = pstdev(series)
    return deviation * deviation


def blend_series(existing: list[float], new: list[float]) -> list[float]:
    if not existing:
        return list(new)
    if not new:
        return list(existing)
    target_len = max(len(existing), len(new))
    blended: list[float] = []
    for idx in range(target_len):
        left = existing[int(idx * len(existing) / target_len)]
        right = new[int(idx * len(new) / target_len)]
        blended.append((left + right) / 2)
    return blended


def root_mean_square(series: list[float]) -> float:
    if not series:
        return 0.0
    return sqrt(sum(value * value for value in series) / len(series))
