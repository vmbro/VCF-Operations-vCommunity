#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the Guest OS Performance KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.vm import guest_os_performance_metrics as go
from fakes import FakeObject

# A guest OS with nothing wrong: no queues, 2 GB free, no paging.
HEALTHY = {
    go.GUEST_CPU_QUEUE: 0.0,
    go.GUEST_DISK_QUEUE: 0.0,
    go.GUEST_FREE_MEMORY_KB: 2048.0 * 1024.0,
    go.GUEST_PAGE_OUT_RATE: 0.0,
}


def collect(vm_stats):
    vm_obj = FakeObject("vm-1")
    go.collect_guest_os_performance_metrics(vm_obj, "VM 1", vm_stats)
    return {key.split("|")[-1]: value for key, value in vm_obj.metrics.items()}


def test_limits_match_the_source_table():
    # docs/Complex Metrics/Guest OS Performance metric.png
    limits = {m.name: (m.best, m.green, m.yellow, m.orange, m.zero_at) for m in go.METRICS}
    assert limits["Guest CPU Run Queue per vCPU"] == (0, 2, 4, 8, 16)
    assert limits["Guest Disk Queue"] == (0, 20, 40, 80, 160)
    assert limits["Guest Free Memory"] == (1024, 512, 256, 128, 0)       # higher is better
    assert limits["Guest Page-Out Rate"] == (0, 1000, 2000, 4000, 8000)


def test_cpu_queue_is_used_as_it_is():
    # The stat is already per vCPU: no division by the number of vCPUs.
    assert go.guest_os_performance_values({go.GUEST_CPU_QUEUE: 3.0})["Guest CPU Run Queue per vCPU"] == 3.0


def test_guest_free_memory_is_converted_from_kb_to_mb():
    assert go.guest_free_memory_mb({go.GUEST_FREE_MEMORY_KB: 524288.0}) == 512.0
    assert go.guest_free_memory_mb({}) is None


def test_healthy_guest_scores_100_and_publishes_only_the_kpi():
    assert collect(HEALTHY) == {go.KPI_KEY: 100.0}


def test_cpu_queue_lowers_the_score():
    # A queue of 3 per vCPU is halfway through yellow (2 to 4): 62.5 with weight 2.
    # KPI = (3 x 100 + 62.5 x 2) / (3 + 2) = 425 / 5 = 85.0
    assert collect({**HEALTHY, go.GUEST_CPU_QUEUE: 3.0})[go.KPI_KEY] == 85.0


def test_low_free_memory_lowers_the_score():
    # 192 MB free is halfway through orange (256 down to 128): it scores 37.5 with weight 4.
    # KPI = (3 x 100 + 37.5 x 4) / (3 + 4) = 450 / 7 = 64.29
    assert collect({**HEALTHY, go.GUEST_FREE_MEMORY_KB: 192.0 * 1024.0})[go.KPI_KEY] == 64.29


def test_vm_without_tools_gets_no_guest_os_kpi():
    # Without VMware Tools there are no guest stats.
    assert collect({}) == {}
