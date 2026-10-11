#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the Cluster Risk KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.cluster import cluster_risk_metrics as cr
from utils.vcenter_inventory import HostHardware, VmSize
from fakes import FakeSuiteApi, FakeObject

GB_IN_KB = 1024.0 * 1024.0
HOST_HARDWARE = HostHardware(cores=32.0, memory_mb=512.0 * 1024.0, dram_mb=512.0 * 1024.0)     # 32 cores, 512 GB


def host_stats(cpu_util=40.0, consumed_gb=256.0, ballooned_gb=0.0, zip_swap_gb=0.0,
               cpu_reserved_mhz=0.0, mem_reserved_gb=0.0):
    """The stats of one 512 GB, 64 000 MHz host, as VCF Operations holds them (memory in KB)."""
    return {
        cr.CPU_THREAD_UTIL: [cpu_util],
        cr.CPU_RESERVED: [cpu_reserved_mhz],
        cr.CPU_CAPACITY: [64000.0],
        cr.MEM_CONSUMED: [consumed_gb * GB_IN_KB],
        cr.MEM_BALLOONED: [ballooned_gb * GB_IN_KB],
        cr.MEM_COMPRESSED: [zip_swap_gb * GB_IN_KB],
        cr.MEM_SWAPPED: [0.0],
        cr.MEM_RESERVED: [mem_reserved_gb * GB_IN_KB],
        cr.MEM_CAPACITY: [512.0 * GB_IN_KB],
    }


SMALL_VMS = [VmSize(4.0, 16384.0)] * 4          # 16 vCPU and 64 GB per host


def collect(samples, vms_per_host=(SMALL_VMS, SMALL_VMS), status_code=200):
    hosts = [cr.HostInventory(f"host-{n}", HOST_HARDWARE, list(vms)) for n, vms in enumerate(vms_per_host, start=1)]
    cluster_obj = FakeObject("cluster-1")
    cr.collect_cluster_risk_metrics(cluster_obj, "Cluster 1", hosts, FakeSuiteApi(samples, status_code))
    return {key.split("|")[-1]: value for key, value in cluster_obj.metrics.items()}


HEALTHY = {"host-1": host_stats(), "host-2": host_stats()}


# --- The table --------------------------------------------------------------

def test_limits_match_the_source_table():
    # docs/Complex Metrics/vSphere Cluster Risk metric.png
    limits = {m.name: (m.best, m.green, m.yellow, m.orange, m.zero_at, m.skip_when_green) for m in cr.METRICS}
    assert limits["Highest ESXi CPU Thread Utilization"] == (0, 60, 80, 90, 95, True)
    assert limits["Worst ESXi CPU Imbalance"] == (1, 1, 1.3, 1.6, 2, False)            # green is exactly 1
    assert limits["Highest ESXi Memory Consumed"] == (0, 80, 90, 95, 100, True)
    assert limits["Worst ESXi Memory Ballooned"] == (0, 1, 2, 4, 8, False)
    assert limits["Worst ESXi Memory Zip Swap"] == (0, 0.25, 0.5, 1, 2, False)
    assert limits["Worst ESXi Memory Tiering Latency"] == (0, 150, 300, 450, 600, False)
    assert limits["Highest ESXi CPU Reservation"] == (0, 10, 40, 60, 80, True)
    assert limits["Highest ESXi Memory Reservation"] == (0, 10, 40, 60, 80, True)
    assert limits["Highest ESXi CPU Overcommit Ratio"] == (0, 1, 2, 3, 4, True)
    assert limits["Highest ESXi Memory Overcommit Ratio"] == (0, 1, 1.4, 1.8, 2.2, True)
    assert limits["Highest CPU Monster VM to Host Ratio"] == (0, 1, 2, 3, 4, False)
    assert limits["Highest Memory Monster VM to Host Ratio"] == (0, 1, 2, 3, 4, False)


# --- Sub-metric formulas ----------------------------------------------------

def test_cpu_imbalance_is_the_busiest_host_against_the_average():
    assert cr.cpu_imbalance([40.0, 40.0]) == 1.0
    assert cr.cpu_imbalance([90.0, 30.0]) == 1.5          # average 60
    assert cr.cpu_imbalance([]) is None
    assert cr.cpu_imbalance([0.0, 0.0]) is None


def test_overcommit_is_per_core_and_per_mb_of_the_host():
    host = cr.HostInventory("host-1", HOST_HARDWARE, [VmSize(16.0, 262144.0)] * 4)     # 64 vCPU, 1 TB
    assert cr.cpu_overcommit(host) == 2.0                 # 64 vCPU on 32 cores
    assert cr.memory_overcommit(host) == 2.0              # 1 TB on 512 GB
    assert cr.cpu_overcommit(cr.HostInventory("host-1", None, [])) is None      # hardware unknown


# The examples of the Monster VM definition: a host with 64 cores (128 threads) and 768 GB of DIMM,
# plus 768 GB of NVMe memory tier.
BIG_HOST = HostHardware(cores=64.0, memory_mb=1536.0 * 1024.0, dram_mb=768.0 * 1024.0)


def test_cpu_monster_is_more_than_half_the_physical_cores():
    # 32 vCPU is half of 64 cores: exactly at the monster size. Threads do not count.
    assert cr.cpu_monster_ratio(cr.HostInventory("host-1", BIG_HOST, [VmSize(32.0, 1024.0)])) == 1.0
    assert cr.cpu_monster_ratio(cr.HostInventory("host-1", BIG_HOST, [VmSize(64.0, 1024.0)])) == 2.0
    assert cr.cpu_monster_ratio(cr.HostInventory("host-1", BIG_HOST, [])) is None


def test_memory_monster_is_40_percent_of_dimm_or_256_gb():
    # 40 % of 768 GB is 307 GB, more than 256 GB, so 256 GB is the monster size. The NVMe tier does not count.
    big = cr.HostInventory("host-1", BIG_HOST, [VmSize(4.0, 256.0 * 1024.0)])
    assert cr.memory_monster_ratio(big) == 1.0
    # 40 % of 512 GB is 204.8 GB, less than 256 GB, so 204.8 GB is the monster size.
    small = cr.HostInventory("host-1", HOST_HARDWARE, [VmSize(4.0, 204.8 * 1024.0)])
    assert cr.memory_monster_ratio(small) == 1.0


def test_memory_shares_are_of_the_host_capacity():
    stats = {cr.MEM_BALLOONED: 5.0 * GB_IN_KB, cr.MEM_CAPACITY: 512.0 * GB_IN_KB}
    assert cr.share_of_memory(stats, [cr.MEM_BALLOONED]) == 5.0 / 512.0 * 100.0
    assert cr.share_of_memory({cr.MEM_BALLOONED: 1.0}, [cr.MEM_BALLOONED]) is None      # capacity missing


# --- The KPI ----------------------------------------------------------------

def test_healthy_cluster():
    published = collect(HEALTHY)
    # Six rows are in their excluded green, and Memory Tiering Latency has no stat, so they are not scored.
    # Counted: imbalance 1 (100), ballooned 0 (100), zip swap 0 (100),
    # CPU monster 4 vCPU / (half of 32 cores) = 0.25 (93.75),
    # memory monster 16 GB / (40 % of 512 GB) = 0.08 after rounding (98.0).
    # KPI = (100 + 100 + 100 + 93.75 + 98) / 5 = 98.35
    assert published["Worst ESXi CPU Imbalance"] == 1.0
    assert published["Highest CPU Monster VM to Host Ratio"] == 0.25
    assert "Worst ESXi Memory Tiering Latency" not in published
    assert published[cr.KPI_NAME] == 98.35


def test_the_worst_host_is_taken():
    samples = {"host-1": host_stats(), "host-2": host_stats(ballooned_gb=10.24)}     # 2 % ballooned
    assert collect(samples)["Worst ESXi Memory Ballooned"] == 2.0


def test_a_busy_host_leaves_its_excluded_green_and_counts():
    samples = {"host-1": host_stats(cpu_util=90.0), "host-2": host_stats(cpu_util=30.0)}
    published = collect(samples)
    assert published["Highest ESXi CPU Thread Utilization"] == 90.0      # start of red: 25 with weight 8
    assert published["Worst ESXi CPU Imbalance"] == 1.5                  # orange: 33.33 with weight 4
    # The other counted rows: ballooned and zip swap (100), CPU monster (93.75), memory monster (98.0).
    # KPI = (25 x 8 + 33.33 x 4 + 100 + 100 + 93.75 + 98) / (8 + 4 + 4) = 725.08 / 16 = 45.32
    assert published[cr.KPI_NAME] == 45.32


def test_failed_stats_call_still_scores_what_vcenter_knows():
    published = collect(HEALTHY, status_code=500)
    # Without stats only the vCenter-based rows are left: overcommit (excluded green) and monster VM.
    assert set(published) == {
        "Highest ESXi CPU Overcommit Ratio", "Highest ESXi Memory Overcommit Ratio",
        "Highest CPU Monster VM to Host Ratio", "Highest Memory Monster VM to Host Ratio", cr.KPI_NAME,
    }
