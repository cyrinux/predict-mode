from custom_components.appliance_patterns.ml.clustering import cluster_runs
from custom_components.appliance_patterns.ml.dtw import dtw_distance


def test_cluster_runs_groups_similar_sequences() -> None:
    runs = [
        [0, 1, 2, 3],
        [0, 1, 2, 2.9],
        [5, 4, 3, 2],
        [5.1, 3.9, 3, 2],
    ]
    clusters = cluster_runs(runs, dtw_distance, threshold=1.5)
    assert len(clusters) == 2
    sizes = sorted(len(cluster.indices) for cluster in clusters)
    assert sizes == [2, 2]
