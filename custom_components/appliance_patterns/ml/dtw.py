from __future__ import annotations

from math import inf


def dtw_distance(series_a: list[float], series_b: list[float], window: int | None = None) -> float:
    if not series_a or not series_b:
        return inf
    len_a = len(series_a)
    len_b = len(series_b)
    if window is None:
        window = max(len_a, len_b)
    window = max(window, abs(len_a - len_b))
    dp = [inf] * (len_b + 1)
    prev = [inf] * (len_b + 1)
    prev[0] = 0.0
    for i in range(1, len_a + 1):
        dp[0] = inf
        start = max(1, i - window)
        end = min(len_b, i + window)
        for j in range(start, end + 1):
            cost = abs(series_a[i - 1] - series_b[j - 1])
            best = min(prev[j], prev[j - 1], dp[j - 1])
            dp[j] = cost + best
        prev, dp = dp, prev
    return prev[len_b]
