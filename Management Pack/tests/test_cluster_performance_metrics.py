#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the Cluster Performance KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.kpi_score import kpi_score
from metrics.cluster import cluster_performance_metrics as cp
from fakes import FakeSuiteApi, FakeObject, FakeMoRef

CLUSTER_ID = "cluster-1"
ALL_ZERO = {metric.name: 0.0 for metric in cp.METRICS}


# --- The KPI ----------------------------------------------------------------

def test_all_zeros_is_100():
    assert kpi_score(cp.METRICS, ALL_ZERO) == 100.0


def test_one_red_metric_is_not_hidden_by_nine_good_ones():
    # CPU Ready = 5 scores 18.75 with weight 8. The other nine score 100 with weight 1.
    # KPI = (9 x 100 + 18.75 x 8) / (9 + 8) = 1050 / 17 = 61.76. A plain average would give 91.9.
    assert kpi_score(cp.METRICS, {**ALL_ZERO, "CPU Ready": 5.0}) == 61.76


def test_everything_at_its_worst_is_0():
    assert kpi_score(cp.METRICS, {metric.name: metric.zero_at for metric in cp.METRICS}) == 0.0


def test_missing_metric_is_left_out_not_scored_as_perfect():
    # Only two sub-metrics have data: one perfect (100, weight 1), one at the start of red (25, weight 8).
    # KPI = (100 x 1 + 25 x 8) / 9 = 33.33. Counting the eight missing ones as perfect would give 64.71.
    values = {"CPU Ready": 0.0, "CPU Co-Stop": 4.0, "Memory Ballooned": None}
    assert kpi_score(cp.METRICS, values) == 33.33


# --- Sub-metric formulas ----------------------------------------------------

def test_average_and_max():
    assert cp.average_and_max([1.0, 2.0, 6.0]) == (3.0, 6.0)
    assert cp.average_and_max([]) == (None, None)


def test_vmotion_rate():
    assert cp.vmotion_rate({cp.VMOTION_COUNT: 3.0, cp.RUNNING_VMS: 200.0}) == 1.5
    assert cp.vmotion_rate({cp.VMOTION_COUNT: 3.0, cp.RUNNING_VMS: 0.0}) is None   # no running VMs
    assert cp.vmotion_rate({cp.RUNNING_VMS: 200.0}) is None                        # stat missing


def test_memory_formulas():
    stats = {
        cp.MEM_COMPRESSED: 1.0, cp.MEM_SWAPPED_OUT: 1.0, cp.MEM_BALLOONED: 2.0,
        cp.MEM_CONSUMED: 108.0, cp.MEM_SYSTEM_USAGE: 10.0,
    }
    assert cp.memory_compressed_or_swapped_pct(stats) == 2.0    # 2 / (2 + 98)
    assert cp.memory_ballooned_pct(stats) == 2.0                # 2 / (2 + 98)

    del stats[cp.MEM_CONSUMED]
    assert cp.memory_compressed_or_swapped_pct(stats) is None
    assert cp.memory_ballooned_pct(stats) is None


# --- End to end, with a fake VCF Operations ---------------------------------

def collect(samples, status_code=200):
    cluster_obj = FakeObject(CLUSTER_ID)
    cluster_ref = FakeMoRef("domain-c1", vm=[FakeMoRef("vm-1"), FakeMoRef("vm-2")], host=[FakeMoRef("host-1"), FakeMoRef("host-2")])
    vms = {"vm-1": FakeObject("vm-1"), "vm-2": FakeObject("vm-2")}
    hosts = {"host-1": FakeObject("host-1"), "host-2": FakeObject("host-2")}
    cp.collect_cluster_performance_metrics(cluster_obj, "Cluster 1", cluster_ref, vms, hosts, FakeSuiteApi(samples, status_code))
    return {key.split("|")[-1]: value for key, value in cluster_obj.metrics.items()}


def host_samples(bad_per_cycle, packets_per_cycle):
    samples = {key: [0.0] * len(bad_per_cycle) for key in cp.HOST_BAD_PACKET_STATS + cp.HOST_PACKET_STATS}
    samples["net|droppedRx_summation_sum"] = bad_per_cycle
    samples["net|packetsRx_summation_sum"] = packets_per_cycle
    return samples


HEALTHY = {
    CLUSTER_ID: {
        cp.VMOTION_COUNT: [0.0], cp.RUNNING_VMS: [2.0], cp.MEM_COMPRESSED: [0.0], cp.MEM_SWAPPED_OUT: [0.0],
        cp.MEM_CONSUMED: [100.0], cp.MEM_SYSTEM_USAGE: [10.0], cp.MEM_BALLOONED: [0.0],
    },
    "vm-1": {key: [0.0] for key in cp.VM_STATS},
    "vm-2": {key: [0.0] for key in cp.VM_STATS},
    "host-1": host_samples([0.0] * 6, [1000.0] * 6),
    "host-2": host_samples([0.0] * 6, [1000.0] * 6),
}


def test_healthy_cluster_publishes_every_metric_and_scores_100():
    published = collect(HEALTHY)
    assert set(published) == {metric.name for metric in cp.METRICS} | {cp.KPI_NAME}
    assert published[cp.KPI_NAME] == 100.0


def test_vm_stats_give_the_average_and_the_worst_vm():
    samples = {**HEALTHY, "vm-1": {**HEALTHY["vm-1"], "cpu|20_sec_peak_readyPct": [6.0]}}
    published = collect(samples)
    assert published["CPU Ready"] == 3.0
    assert published["Worst VM CPU Ready"] == 6.0


def test_bad_packets_use_the_whole_window_and_the_worst_host():
    # host-2 drops 30 of 1000 packets in one cycle (3 %, deep red), then nothing for five cycles.
    # Over the window that is 30 of 6000 = 0.5 %, which is orange.
    samples = {**HEALTHY, "host-2": host_samples([30.0, 0.0, 0.0, 0.0, 0.0, 0.0], [1000.0] * 6)}
    assert collect(samples)["Worst ESXi Bad Network Packets"] == 0.5


def test_failed_stats_calls_publish_nothing():
    assert collect(HEALTHY, status_code=500) == {}


def test_metrics_without_data_are_not_published():
    samples = {**HEALTHY, "vm-1": {}, "vm-2": {}}
    published = collect(samples)
    assert "CPU Ready" not in published
    assert "Worst VM Memory Contention" not in published
    assert published["Memory Ballooned"] == 0.0
    assert published[cp.KPI_NAME] == 100.0
