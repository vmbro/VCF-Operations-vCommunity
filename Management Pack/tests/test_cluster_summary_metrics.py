#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster summary metrics on vSphere World: the 10th percentile and the worst of the cluster scores.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.world import cluster_summary_metrics as cs
from fakes import FakeObject, FakeSuiteApi

PERFORMANCE = cs.CLUSTER_PERFORMANCE_SCORE
RISK = cs.CLUSTER_RISK_SCORE


def test_score_keys_are_the_published_cluster_kpis():
    assert PERFORMANCE == "vCommunity|Cluster Performance|Cluster Performance Score"
    assert RISK == "vCommunity|Cluster Risk|Cluster Risk Score"


def test_10th_percentile_is_the_value_90_percent_are_at_or_above():
    # 20 scores 1..20: position 10 % of 20 = 2, so the 2nd lowest.
    assert cs.percentile_10([float(n) for n in range(20, 0, -1)]) == 2.0
    # 10 or fewer: the lowest.
    assert cs.percentile_10([80.0, 40.0, 95.0]) == 40.0
    assert cs.percentile_10([]) is None


def test_summary_of_all_clusters():
    scores = {
        "cl-1": {PERFORMANCE: 86.35, RISK: 19.16},
        "cl-2": {PERFORMANCE: 98.0, RISK: 75.0},
        "cl-3": {PERFORMANCE: 50.0},                 # no Cluster Risk score this cycle: left out of it
    }
    assert cs.summary_values(scores) == {
        "10th Percentile Cluster Performance": 50.0,
        "Worst Cluster Performance": 50.0,
        "10th Percentile Cluster Risk": 19.16,
        "Worst Cluster Risk": 19.16,
    }


def test_no_cluster_score_gives_no_data():
    assert set(cs.summary_values({}).values()) == {None}


def test_reads_the_clusters_of_all_vcenters_and_publishes_on_vsphere_world():
    api = FakeSuiteApi(
        resources={"ClusterComputeResource": [("cl-1", "cluster-a", "domain-c1"), ("cl-2", "cluster-b", "domain-c2")]},
        samples={"cl-1": {PERFORMANCE: [70.0, 86.354], RISK: [19.16]}, "cl-2": {PERFORMANCE: [98.0], RISK: [75.0]}},
    )
    world = FakeObject("vSphere World")
    cs.collect_cluster_summary_metrics(world, api)
    # No adapter instance filter: the clusters of every vCenter.
    assert "adapterInstanceId" not in api.resource_queries[0]
    assert world.metrics == {
        "vCommunity|10th Percentile Cluster Performance": 86.35,
        "vCommunity|Worst Cluster Performance": 86.35,
        "vCommunity|10th Percentile Cluster Risk": 19.16,
        "vCommunity|Worst Cluster Risk": 19.16,
    }


def test_a_failed_stats_request_publishes_nothing():
    api = FakeSuiteApi(resources={"ClusterComputeResource": [("cl-1", "cluster-a", "domain-c1")]},
                       samples={"cl-1": {PERFORMANCE: [90.0]}}, status_code=500)
    world = FakeObject("vSphere World")
    cs.collect_cluster_summary_metrics(world, api)
    assert world.metrics == {}
