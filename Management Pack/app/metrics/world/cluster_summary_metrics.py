#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster summary metrics on the vSphere World object.

What they are
-------------
Four numbers that summarise the Cluster Performance and Cluster Risk scores of every cluster in VCF Operations,
across all vCenters. They are published on the vSphere World object, under vCommunity:

    10th Percentile Cluster Performance   90 % of the clusters score at or above it
    Worst Cluster Performance             the lowest Cluster Performance score
    10th Percentile Cluster Risk          90 % of the clusters score at or above it
    Worst Cluster Risk                    the lowest Cluster Risk score

A score is "higher is better", so the bad end is the low end: the 10th percentile, not the 90th.

Where the scores come from
--------------------------
The scores already stored in VCF Operations, read with one request for all clusters. There is one vSphere World
object, but one account of this pack per vCenter. Every account reads the clusters of all vCenters, so they all
publish the same values instead of overwriting each other with the clusters of their own vCenter only.

Known limitation: the stored score of a cluster is the one of its last collection, so a value can be up to one
collection cycle old. See docs/vsphere-world-metrics.md.
"""
import logging
import math
from typing import Dict, List, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.cluster import cluster_performance_metrics, cluster_risk_metrics
from utils.ops_stats import query_resources, read_latest_stats

logger = logging.getLogger(__name__)

# The cluster scores, as stored in VCF Operations.
CLUSTER_PERFORMANCE_SCORE = f"vCommunity|{cluster_performance_metrics.GROUP}|{cluster_performance_metrics.KPI_KEY}"
CLUSTER_RISK_SCORE = f"vCommunity|{cluster_risk_metrics.GROUP}|{cluster_risk_metrics.KPI_KEY}"

# Metric name -> (cluster score it summarises, how).
METRICS = {
    "10th Percentile Cluster Performance": (CLUSTER_PERFORMANCE_SCORE, "10th percentile"),
    "Worst Cluster Performance":           (CLUSTER_PERFORMANCE_SCORE, "lowest"),
    "10th Percentile Cluster Risk":        (CLUSTER_RISK_SCORE, "10th percentile"),
    "Worst Cluster Risk":                  (CLUSTER_RISK_SCORE, "lowest"),
}


def percentile_10(numbers: List[float]) -> Optional[float]:
    """The value that 90 % of the numbers are at or above. None when the list is empty.

    Nearest-rank method, the mirror of percentile_90() in metrics/vm_contention.py: sort the numbers and take
    the one at position 10 % of the count, rounded up. With 20 clusters that is the 2nd lowest. With 10 or
    fewer clusters it is the lowest.
    """
    if not numbers:
        return None
    position = math.ceil(0.1 * len(numbers))
    return sorted(numbers)[position - 1]


def summary_values(scores_by_cluster: Dict[str, Dict[str, float]]) -> Dict[str, Optional[float]]:
    """Value of every metric in METRICS. A cluster without a score is left out. None means "no data"."""
    values = {}
    for name, (score_key, how) in METRICS.items():
        scores = [stats[score_key] for stats in scores_by_cluster.values() if score_key in stats]
        if how == "10th percentile":
            values[name] = percentile_10(scores)
        else:
            values[name] = min(scores) if scores else None
    return values


def read_cluster_scores(suite_api_client: SuiteApiClient) -> Dict[str, Dict[str, float]]:
    """{cluster resource id: {score key: latest score}} for every cluster in VCF Operations, of all vCenters."""
    clusters = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "ClusterComputeResource", None)
    return read_latest_stats(suite_api_client, [cluster.id for cluster in clusters],
                             [CLUSTER_PERFORMANCE_SCORE, CLUSTER_RISK_SCORE])


def collect_cluster_summary_metrics(world_obj: Object, suite_api_client: SuiteApiClient) -> None:
    """Publishes the metrics in METRICS on the vSphere World object."""
    try:
        values = summary_values(read_cluster_scores(suite_api_client))
        for name, value in values.items():
            if value is not None:
                world_obj.with_metric(f"vCommunity|{name}", round(value, 2))
    except Exception as e:
        # A failure here must not stop the rest of the collection.
        logger.warning(f"Failed to publish the cluster summary metrics on vSphere World - {repr(e)}")
