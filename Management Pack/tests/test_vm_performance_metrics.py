#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the VM Performance KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.vm import vm_performance_metrics as vp
from metrics.vm import guest_os_performance_metrics as go
from fakes import FakeSuiteApi, FakeObject

# A VM with nothing wrong: no contention, CPU Run low, nothing compressed or swapped.
HEALTHY = {
    **{stat_key: 0.0 for stat_key in vp.SOURCE_STATS.values()},
    vp.MEM_COMPRESSED: 0.0,
    vp.MEM_SWAPPED: 0.0,
    vp.GUEST_USED_MEMORY: 4000000.0,
}


def collect(vm_stats):
    vm_obj = FakeObject("vm-1")
    vp.collect_vm_performance_metrics(vm_obj, "VM 1", vm_stats)
    return {key.split("|")[-1]: value for key, value in vm_obj.metrics.items()}


# --- The table --------------------------------------------------------------

def test_limits_match_the_source_table():
    # docs/Complex Metrics/Virtual Motherboard Performance metric.png
    limits = {m.name: (m.green, m.yellow, m.orange, m.zero_at, m.skip_when_green) for m in vp.METRICS}
    assert limits["CPU Co-Stop"] == (1, 2, 4, 8, False)
    assert limits["CPU Ready"] == (2, 4, 8, 16, False)
    assert limits["CPU Overlap"] == (0.5, 1, 2, 4, False)
    assert limits["Memory Contention"] == (0.5, 1, 2, 4, False)
    assert limits["Disk Latency"] == (10, 20, 40, 80, False)
    assert limits["Network Dropped Tx"] == (0.25, 0.5, 1, 2, False)
    assert limits["CPU Run"] == (95, 97, 99, 100, True)            # green is "Excluded"
    assert limits["Memory Ballooned"] == (2, 4, 8, 16, False)
    assert limits["Memory Zip Swap"] == (0.25, 0.5, 1, 2, False)


# --- Sub-metric formulas ----------------------------------------------------

def test_every_sub_metric_has_a_value():
    assert set(vp.vm_performance_values(HEALTHY)) == {metric.name for metric in vp.METRICS}
    assert None not in vp.vm_performance_values(HEALTHY).values()


def test_memory_zip_swap():
    stats = {vp.MEM_COMPRESSED: 10.0, vp.MEM_SWAPPED: 10.0, vp.GUEST_USED_MEMORY: 1000.0}
    assert vp.memory_compressed_or_swapped_pct(stats) == 2.0                              # 20 / 1000
    assert vp.memory_compressed_or_swapped_pct({**stats, vp.GUEST_USED_MEMORY: 0.0}) is None
    assert vp.memory_compressed_or_swapped_pct({vp.MEM_COMPRESSED: 10.0}) is None         # stats missing


# --- The KPI ----------------------------------------------------------------

def test_healthy_vm_scores_100_and_publishes_only_what_the_vm_does_not_have():
    assert collect(HEALTHY) == {"Memory Zip Swap": 0.0, vp.KPI_NAME: 100.0}


def test_one_red_metric_is_not_hidden_by_seven_good_ones():
    # CPU Ready = 10 is a quarter of the way through red (8 to 16): it scores 18.75 with weight 8.
    # CPU Run is 0, in its excluded green, so it is left out. The other seven score 100 with weight 1.
    # KPI = (7 x 100 + 18.75 x 8) / (7 + 8) = 850 / 15 = 56.67. A plain average would give 89.8.
    assert collect({**HEALTHY, "cpu|20_sec_peak_readyPct": 10.0})[vp.KPI_NAME] == 56.67


def test_cpu_run_counts_only_above_95_percent():
    # Below 95 % CPU Run is in its excluded green: left out, not scored 100.
    assert collect({**HEALTHY, "cpu|net_run": 90.0})[vp.KPI_NAME] == 100.0
    # 98 % is halfway through orange (97 to 99): it scores 37.5 with weight 4.
    # KPI = (8 x 100 + 37.5 x 4) / (8 + 4) = 950 / 12 = 79.17
    assert collect({**HEALTHY, "cpu|net_run": 98.0})[vp.KPI_NAME] == 79.17


def test_disk_latency_uses_the_new_limits():
    # 30 ms is halfway through orange (20 to 40): it scores 37.5 with weight 4.
    # KPI = (7 x 100 + 37.5 x 4) / (7 + 4) = 850 / 11 = 77.27
    assert collect({**HEALTHY, "virtualDisk|20_sec_peak_totalLatency_average": 30.0})[vp.KPI_NAME] == 77.27


# --- Missing data -----------------------------------------------------------

def test_vm_without_tools_is_scored_on_the_stats_it_has():
    no_tools = {key: value for key, value in HEALTHY.items() if key != vp.GUEST_USED_MEMORY}
    published = collect({**no_tools, "cpu|20_sec_peak_readyPct": 10.0})
    # Memory Zip Swap needs a Tools stat, so it has no data. CPU Run is excluded.
    # That leaves six at 100 and CPU Ready at 18.75 with weight 8.
    # KPI = (6 x 100 + 18.75 x 8) / (6 + 8) = 750 / 14 = 53.57
    assert published == {vp.KPI_NAME: 53.57}


def test_vm_with_no_stats_publishes_nothing():
    assert collect({}) == {}


# --- Reading stats ----------------------------------------------------------

def test_stats_of_both_vm_kpis_are_read_for_all_vms_in_one_go():
    guest_stats = {go.GUEST_DISK_QUEUE: 3.0, go.VCPU_COUNT: 2.0}
    api = FakeSuiteApi({"vm-1": {key: [value] for key, value in {**HEALTHY, **guest_stats}.items()}, "vm-2": {}})
    stats = vp.read_vm_performance_stats(api, [FakeObject("vm-1"), FakeObject("vm-2")])
    assert api.requests == 1
    assert stats["vm-1"] == {**HEALTHY, **guest_stats}
    assert stats["vm-2"] == {}


def test_failed_stats_call_gives_no_stats():
    api = FakeSuiteApi({"vm-1": {key: [value] for key, value in HEALTHY.items()}}, status_code=500)
    assert vp.read_vm_performance_stats(api, [FakeObject("vm-1")]) == {}
