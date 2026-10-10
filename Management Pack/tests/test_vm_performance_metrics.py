#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the VM Performance KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.vm import vm_performance_metrics as vp
from fakes import FakeSuiteApi, FakeObject

# A VM with nothing wrong: no contention, 2 GB of free guest memory, nothing compressed or swapped.
HEALTHY = {
    **{stat_key: 0.0 for stat_key in vp.SOURCE_STATS.values()},
    vp.GUEST_FREE_MEMORY_KB: 2048.0 * 1024.0,
    vp.MEM_COMPRESSED: 0.0,
    vp.MEM_SWAPPED: 0.0,
    vp.GUEST_USED_MEMORY: 4000000.0,
}


def collect(vm_stats):
    vm_obj = FakeObject("vm-1")
    vp.collect_vm_performance_metrics(vm_obj, "VM 1", vm_stats)
    return {key.split("|")[-1]: value for key, value in vm_obj.metrics.items()}


# --- Sub-metric formulas ----------------------------------------------------

def test_every_sub_metric_has_a_value():
    assert set(vp.vm_performance_values(HEALTHY)) == {metric.name for metric in vp.METRICS}
    assert None not in vp.vm_performance_values(HEALTHY).values()


def test_memory_zip_swap():
    stats = {vp.MEM_COMPRESSED: 10.0, vp.MEM_SWAPPED: 10.0, vp.GUEST_USED_MEMORY: 1000.0}
    assert vp.memory_compressed_or_swapped_pct(stats) == 2.0                              # 20 / 1000
    assert vp.memory_compressed_or_swapped_pct({**stats, vp.GUEST_USED_MEMORY: 0.0}) is None
    assert vp.memory_compressed_or_swapped_pct({vp.MEM_COMPRESSED: 10.0}) is None         # stats missing


def test_guest_free_memory_is_converted_from_kb_to_mb():
    assert vp.guest_free_memory_mb({vp.GUEST_FREE_MEMORY_KB: 524288.0}) == 512.0
    assert vp.guest_free_memory_mb({}) is None


# --- The KPI ----------------------------------------------------------------

def test_healthy_vm_scores_100_and_publishes_only_what_the_vm_does_not_have():
    assert collect(HEALTHY) == {"Memory Zip Swap": 0.0, vp.KPI_NAME: 100.0}


def test_one_red_metric_is_not_hidden_by_thirteen_good_ones():
    # CPU Ready = 10 is a quarter of the way through red (8 to 16): it scores 18.75 with weight 8.
    # KPI = (13 x 100 + 18.75 x 8) / (13 + 8) = 1450 / 21 = 69.05. A plain average would give 94.2.
    assert collect({**HEALTHY, "cpu|20_sec_peak_readyPct": 10.0})[vp.KPI_NAME] == 69.05


def test_low_free_memory_lowers_the_score():
    # 192 MB free is halfway through orange (256 down to 128): it scores 37.5 with weight 4.
    # KPI = (13 x 100 + 37.5 x 4) / (13 + 4) = 1450 / 17 = 85.29
    assert collect({**HEALTHY, vp.GUEST_FREE_MEMORY_KB: 192.0 * 1024.0})[vp.KPI_NAME] == 85.29


def test_cpu_run_only_counts_above_60_percent():
    assert collect({**HEALTHY, "cpu|net_run": 55.0})[vp.KPI_NAME] == 100.0
    # CPU Run = 85 is halfway through yellow (80 to 90): it scores 62.5 with weight 2.
    # KPI = (13 x 100 + 62.5 x 2) / (13 + 2) = 1425 / 15 = 95.0
    assert collect({**HEALTHY, "cpu|net_run": 85.0})[vp.KPI_NAME] == 95.0


# --- Missing data -----------------------------------------------------------

def test_vm_without_tools_is_scored_on_the_stats_it_has():
    no_guest_stats = {key: value for key, value in HEALTHY.items() if not key.startswith("guest|")}
    published = collect({**no_guest_stats, "cpu|20_sec_peak_readyPct": 10.0})
    # Five sub-metrics need guest stats, so nine are left: eight at 100 and CPU Ready at 18.75 with weight 8.
    # KPI = (8 x 100 + 18.75 x 8) / (8 + 8) = 950 / 16 = 59.38
    assert published == {vp.KPI_NAME: 59.38}


def test_vm_with_no_stats_publishes_nothing():
    assert collect({}) == {}


# --- Reading stats ----------------------------------------------------------

def test_stats_are_read_for_all_vms_in_one_go():
    api = FakeSuiteApi({"vm-1": {key: [value] for key, value in HEALTHY.items()}, "vm-2": {}})
    stats = vp.read_vm_performance_stats(api, [FakeObject("vm-1"), FakeObject("vm-2")])
    assert api.requests == 1
    assert stats["vm-1"] == HEALTHY
    assert stats["vm-2"] == {}


def test_failed_stats_call_gives_no_stats():
    api = FakeSuiteApi({"vm-1": {key: [value] for key, value in HEALTHY.items()}}, status_code=500)
    assert vp.read_vm_performance_stats(api, [FakeObject("vm-1")]) == {}
