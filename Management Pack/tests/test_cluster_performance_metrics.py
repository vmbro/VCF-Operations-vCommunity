#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the Cluster Performance KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.kpi_score import kpi_score
from metrics.cluster import cluster_performance_metrics as cp
from metrics import vm_contention as vc
from fakes import FakeSuiteApi, FakeObject

ALL_ZERO = {metric.name: 0.0 for metric in cp.METRICS}


# --- The KPI ----------------------------------------------------------------

def test_all_zeros_is_100():
    assert kpi_score(cp.METRICS, ALL_ZERO) == 100.0


def test_one_red_metric_is_not_hidden_by_seven_good_ones():
    # 90th Percentile VM CPU Ready = 5 is a quarter into red (4 to 8): it scores 18.75 with weight 8.
    # Bad network packets are 0, so they are skipped (no free 100). The other seven score 100 with weight 1.
    # KPI = (7 x 100 + 18.75 x 8) / (7 + 8) = 850 / 15 = 56.67. A plain average would give 89.8.
    assert kpi_score(cp.METRICS, {**ALL_ZERO, "90th Percentile VM CPU Ready": 5.0}) == 56.67


def test_any_bad_packet_is_yellow_and_counts():
    # Green is exactly 0. A tiny share of bad packets is already yellow: it scores almost 75, with weight 2.
    # KPI = (8 x 100 + 74.38 x 2) / (8 + 2) = 94.88
    assert kpi_score(cp.METRICS, {**ALL_ZERO, "Highest ESXi Bad Network Packets": 0.005}) == 94.88


def test_everything_at_its_worst_is_0():
    assert kpi_score(cp.METRICS, {metric.name: metric.zero_at for metric in cp.METRICS}) == 0.0


def test_limits_match_the_source_table():
    # docs/Complex Metrics/vSphere Cluster Performance metric.png
    limits = {m.name: (m.green, m.yellow, m.orange, m.zero_at) for m in cp.METRICS}
    assert limits["Worst VM CPU Ready"] == (4, 8, 16, 32)
    assert limits["Worst VM CPU Co-Stop"] == (2, 4, 8, 16)
    assert limits["Worst VM Memory Latency"] == (1, 2, 4, 8)
    assert limits["Worst VM Disk Latency"] == (40, 80, 160, 320)
    assert limits["90th Percentile VM CPU Ready"] == (1, 2, 4, 8)
    assert limits["90th Percentile VM CPU Co-Stop"] == (0.5, 1, 2, 4)
    assert limits["90th Percentile VM Memory Latency"] == (0.5, 1, 2, 4)
    assert limits["90th Percentile VM Disk Latency"] == (20, 40, 60, 80)
    assert limits["Highest ESXi Bad Network Packets"] == (0, 0.2, 0.4, 0.8)   # green is exactly 0


# --- Sub-metric formulas ----------------------------------------------------

def test_percentile_90():
    assert vc.percentile_90([]) is None
    assert vc.percentile_90([3.0]) == 3.0
    # Fewer than 10 VMs: the highest.
    assert vc.percentile_90([5.0, 1.0, 2.0]) == 5.0
    # 20 VMs, 1 to 20: the 18th lowest. 18 of the 20 are at or below it.
    assert vc.percentile_90([float(n) for n in range(20, 0, -1)]) == 18.0


# --- End to end, with a fake VCF Operations ---------------------------------

CLUSTER_ID = "cluster-1"
VM_IDS = [f"vm-{n}" for n in range(1, 11)]       # 10 VMs: the 90th percentile is the 9th lowest
HOST_IDS = ["host-1", "host-2"]


def collect(samples, status_code=200):
    cluster_obj = FakeObject(CLUSTER_ID)
    cp.collect_cluster_performance_metrics(cluster_obj, "Cluster 1", VM_IDS, HOST_IDS, FakeSuiteApi(samples, status_code))
    return {key.split("|")[-1]: value for key, value in cluster_obj.metrics.items()}


def host_samples(bad_packets, packets):
    """The packet counters of one host in the last collection cycle: bad_packets dropped of all packets."""
    samples = {key: [0.0] for key in vc.HOST_BAD_PACKET_STATS + vc.HOST_PACKET_STATS}
    samples["net|droppedRx_summation_sum"] = [bad_packets]
    samples["net|packetsRx_summation_sum"] = [packets]
    return samples


HEALTHY = {
    **{vm_id: {key: [0.0] for key in vc.VM_STATS} for vm_id in VM_IDS},
    "host-1": host_samples(0.0, 1000.0),
    "host-2": host_samples(0.0, 1000.0),
}


def test_healthy_cluster_publishes_every_metric_and_scores_100():
    published = collect(HEALTHY)
    assert set(published) == {metric.name for metric in cp.METRICS} | {cp.KPI_KEY}
    assert published[cp.KPI_KEY] == 100.0


def test_vm_stats_give_the_worst_vm_and_the_90th_percentile():
    # CPU Ready of the 10 VMs is 1, 2, ... 10. The worst is 10. The 90th percentile is the 9th lowest: 9.
    samples = {**HEALTHY}
    for n, vm_id in enumerate(VM_IDS, start=1):
        samples[vm_id] = {**HEALTHY[vm_id], "cpu|20_sec_peak_readyPct": [float(n)]}
    published = collect(samples)
    assert published["Worst VM CPU Ready"] == 10.0
    assert published["90th Percentile VM CPU Ready"] == 9.0


def test_one_bad_vm_shows_as_deep_but_not_broad():
    samples = {**HEALTHY, "vm-1": {**HEALTHY["vm-1"], "virtualDisk|20_sec_peak_totalLatency_average": [200.0]}}
    published = collect(samples)
    assert published["Worst VM Disk Latency"] == 200.0
    assert published["90th Percentile VM Disk Latency"] == 0.0


def test_bad_packets_use_the_last_cycle_and_the_worst_host():
    # host-2 drops 15 of 1000 packets in the last 5 minutes: 1.5 %, beyond red. The spike is not averaged away.
    samples = {**HEALTHY, "host-2": host_samples(15.0, 1000.0)}
    assert collect(samples)["Highest ESXi Bad Network Packets"] == 1.5


def test_failed_stats_calls_publish_nothing():
    assert collect(HEALTHY, status_code=500) == {}


def test_metrics_without_data_are_not_published():
    samples = {**HEALTHY, **{vm_id: {} for vm_id in VM_IDS}}
    published = collect(samples)
    assert "Worst VM CPU Ready" not in published
    assert "90th Percentile VM Memory Latency" not in published
    assert published["Highest ESXi Bad Network Packets"] == 0.0
    assert published[cp.KPI_KEY] == 100.0
