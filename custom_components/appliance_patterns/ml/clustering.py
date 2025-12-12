from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .feature_extraction import blend_series

DistanceFn = Callable[[list[float], list[float]], float]


@dataclass
class Cluster:
    centroid: list[float]
    indices: list[int]


def cluster_runs(runs: list[list[float]], distance_fn: DistanceFn, threshold: float) -> list[Cluster]:
    clusters: list[Cluster] = []
    for index, run in enumerate(runs):
        if not run:
            continue
        best_cluster: Cluster | None = None
        best_distance = float("inf")
        for cluster in clusters:
            distance = distance_fn(run, cluster.centroid)
            if distance < best_distance:
                best_distance = distance
                best_cluster = cluster
        if best_cluster is None or best_distance > threshold:
            clusters.append(Cluster(centroid=list(run), indices=[index]))
            continue
        best_cluster.indices.append(index)
        best_cluster.centroid = blend_series(best_cluster.centroid, run)
    return clusters


def select_representatives(
    runs: list[list[float]],
    clusters: list[Cluster],
) -> list[list[float]]:
    representatives: list[list[float]] = []
    for cluster in clusters:
        if not cluster.indices:
            continue
        representatives.append(runs[cluster.indices[0]])
    return representatives
