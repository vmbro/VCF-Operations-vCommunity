#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Worked examples for the Cluster Risk KPI. They double as documentation.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.cluster import cluster_risk_metrics as cr
from utils.ops_inventory import VmInfo
from fakes import FakeSuiteApi, FakeObject

GB_IN_KB = 1024.0 * 1024.0
# 32 cores with hyper-threading (64 threads), 512 GB.
def vm(vcpus, memory_mb):
    """A powered-on VM of the given size."""
    return VmInfo("vm", "vm", "vm-1", "host-1", True, vcpus, memory_mb)


def host(host_id="host-1", cores=32.0, threads=64.0, vms=()):
    """A host as the cluster collector builds it. By default 32 cores and 64 threads."""
    return cr.HostInventory(host_id, cores, threads, list(vms))


HOST = host()


def host_stats(cpu_util=40.0, core_util=80.0, consumed_gb=256.0, ballooned_gb=0.0, zip_swap_gb=0.0,
               cpu_reserved_mhz=0.0, mem_reserved_gb=0.0, vcpus_allocated=16.0, mem_allocated_gb=64.0):
    """The stats of one 512 GB, 64 000 MHz host, as VCF Operations holds them (memory in KB)."""
    return {
        cr.CPU_THREAD_UTIL: [cpu_util],
        cr.CPU_CORE_UTIL: [core_util],
        cr.CPU_RESERVED: [cpu_reserved_mhz],
        cr.CPU_CAPACITY: [64000.0],
        cr.MEM_CONSUMED: [consumed_gb * GB_IN_KB],
        cr.MEM_BALLOONED: [ballooned_gb * GB_IN_KB],
        cr.MEM_COMPRESSED: [zip_swap_gb * GB_IN_KB],
        cr.MEM_SWAPPED: [0.0],
        cr.MEM_RESERVED: [mem_reserved_gb * GB_IN_KB],
        cr.MEM_DRAM_CAPACITY: [512.0 * GB_IN_KB],
        cr.VCPUS_ALLOCATED: [vcpus_allocated],
        cr.MEM_ALLOCATED: [mem_allocated_gb * GB_IN_KB],
    }


SMALL_VMS = [vm(4.0, 16384.0)] * 4          # 16 vCPU and 64 GB per host


def collect(samples, vms_per_host=(SMALL_VMS, SMALL_VMS), status_code=200):
    hosts = [host(f"host-{n}", vms=vms) for n, vms in enumerate(vms_per_host, start=1)]
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

def stats(thread_util, core_util):
    return {cr.CPU_THREAD_UTIL: thread_util, cr.CPU_CORE_UTIL: core_util}


def test_cpu_imbalance_is_running_threads_per_running_core():
    # 32 cores, 64 threads. 40 % of threads is 25.6 threads, 80 % of cores is 25.6 cores: one thread per core.
    assert cr.cpu_imbalance(stats(40.0, 80.0), HOST) == 1.0
    # Both threads run on every busy core: 50 % of threads is 32, 50 % of cores is 16.
    assert cr.cpu_imbalance(stats(50.0, 50.0), HOST) == 2.0
    # 90 % of threads is 57.6, all 32 cores run: 1.8.
    assert cr.cpu_imbalance(stats(90.0, 100.0), HOST) == 1.8


def test_cpu_imbalance_without_data():
    assert cr.cpu_imbalance(stats(0.0, 0.0), HOST) is None           # idle host
    assert cr.cpu_imbalance({cr.CPU_THREAD_UTIL: 40.0}, HOST) is None  # core utilization missing
    assert cr.cpu_imbalance(stats(40.0, 80.0), host(cores=None, threads=None)) is None   # cores unknown


def test_overcommit_uses_what_vcf_operations_allocated_to_the_powered_on_vms():
    stats = {cr.VCPUS_ALLOCATED: 64.0, cr.MEM_ALLOCATED: 1024.0 * GB_IN_KB, cr.MEM_DRAM_CAPACITY: 512.0 * GB_IN_KB}
    assert cr.cpu_overcommit(stats, HOST) == 2.0          # 64 vCPU on 32 cores
    assert cr.memory_overcommit(stats) == 2.0                      # 1 TB on 512 GB
    assert cr.cpu_overcommit(stats, host(cores=None)) is None      # cores unknown
    assert cr.cpu_overcommit({}, HOST) is None            # stat missing
    assert cr.memory_overcommit({cr.MEM_ALLOCATED: 1.0}) is None   # capacity missing


# The examples of the Monster VM definition: a host with 64 cores (128 threads) and 768 GB of DIMM,
# plus 768 GB of NVMe memory tier.



def big_host(vms):
    """The host of the Monster VM examples: 64 cores (128 threads) and 768 GB of DIMM."""
    return host(cores=64.0, threads=128.0, vms=vms)


def test_cpu_monster_is_more_than_half_the_physical_cores():
    # 32 vCPU is half of 64 cores: exactly at the monster size. Threads do not count.
    assert cr.cpu_monster_ratio(big_host([vm(32.0, 1024.0)])) == 1.0
    assert cr.cpu_monster_ratio(big_host([vm(64.0, 1024.0)])) == 2.0
    assert cr.cpu_monster_ratio(big_host([])) is None


def test_memory_monster_is_40_percent_of_dimm_or_256_gb():
    # 40 % of 768 GB is 307 GB, more than 256 GB, so 256 GB is the monster size. The NVMe tier does not count.
    # The host's DRAM is 768 GB. Its 768 GB NVMe tier does not count.
    tiered = {cr.MEM_DRAM_CAPACITY: 768.0 * GB_IN_KB}
    assert cr.memory_monster_ratio(tiered, big_host([vm(4.0, 256.0 * 1024.0)])) == 1.0
    # 40 % of 512 GB is 204.8 GB, less than 256 GB, so 204.8 GB is the monster size.
    untiered = {cr.MEM_DRAM_CAPACITY: 512.0 * GB_IN_KB}
    assert cr.memory_monster_ratio(untiered, host(vms=[vm(4.0, 204.8 * 1024.0)])) == 1.0


def test_memory_shares_are_of_the_host_capacity():
    stats = {cr.MEM_BALLOONED: 5.12 * GB_IN_KB, cr.MEM_DRAM_CAPACITY: 512.0 * GB_IN_KB}
    assert cr.memory_ballooned_pct(stats) == 1.0
    assert cr.memory_ballooned_pct({cr.MEM_BALLOONED: 1.0}) is None      # capacity missing


def test_zip_swap_adds_zipped_and_swapped_per_host_then_takes_the_highest_host():
    # host-1: 3 GB zipped + 2 GB swapped = 5 GB of 100 GB = 5 %. host-2: 4 GB zipped + 0 swapped = 4 %.
    # Taking the highest of zipped and swapped separately would give 4 GB. Adding them per host gives 5 %.
    gb = GB_IN_KB
    host_1 = {cr.MEM_COMPRESSED: 3 * gb, cr.MEM_SWAPPED: 2 * gb, cr.MEM_DRAM_CAPACITY: 100 * gb}
    host_2 = {cr.MEM_COMPRESSED: 4 * gb, cr.MEM_SWAPPED: 0.0, cr.MEM_DRAM_CAPACITY: 100 * gb}
    assert cr.memory_zip_swap_pct(host_1) == 5.0
    assert cr.memory_zip_swap_pct(host_2) == 4.0
    hosts = [host("host-1"), host("host-2")]
    assert cr.cluster_risk_values(hosts, {"host-1": host_1, "host-2": host_2})["Worst ESXi Memory Zip Swap"] == 5.0


# --- The KPI ----------------------------------------------------------------

def test_healthy_cluster():
    published = collect(HEALTHY)
    # Six rows are in their excluded green, and these hosts have no memory tiering, so they are not scored.
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
    samples = {"host-1": host_stats(cpu_util=90.0, core_util=100.0), "host-2": host_stats(cpu_util=30.0, core_util=60.0)}
    published = collect(samples)
    assert published["Highest ESXi CPU Thread Utilization"] == 90.0      # start of red: 25 with weight 8
    # host-1: 57.6 running threads on 32 running cores = 1.8. host-2: 19.2 on 19.2 = 1.0. The worst is kept.
    assert published["Worst ESXi CPU Imbalance"] == 1.8                  # halfway through red: 12.5 with weight 8
    # The other counted rows: ballooned and zip swap (100), CPU monster (93.75), memory monster (98.0).
    # KPI = (25 x 8 + 12.5 x 8 + 100 + 100 + 93.75 + 98) / (8 + 8 + 4) = 691.75 / 20 = 34.59
    assert published[cr.KPI_NAME] == 34.59


def test_failed_stats_call_still_scores_what_the_properties_give():
    published = collect(HEALTHY, status_code=500)
    # Without stats only CPU Monster VM is left: it needs only properties (VM vCPUs, host cores).
    assert set(published) == {"Highest CPU Monster VM to Host Ratio", cr.KPI_NAME}


def test_memory_tiering_latency_counts_only_on_hosts_with_memory_tiering():
    # host-2 has an NVMe memory tier with 300 µs read latency: the start of orange. host-1 has no tier.
    samples = {"host-1": host_stats(), "host-2": {**host_stats(), cr.MEM_TIERING_LATENCY: [300.0]}}
    assert collect(samples)["Worst ESXi Memory Tiering Latency"] == 300.0
    assert "Worst ESXi Memory Tiering Latency" not in collect(HEALTHY)


def test_dram_capacity_falls_back_to_host_provisioned_memory():
    assert cr.dram_capacity_kb({cr.MEM_DRAM_CAPACITY: 768.0, cr.MEM_DRAM_CAPACITY_FALLBACK: 1536.0}) == 768.0
    assert cr.dram_capacity_kb({cr.MEM_DRAM_CAPACITY_FALLBACK: 512.0}) == 512.0     # DRAM stat missing
    assert cr.dram_capacity_kb({cr.MEM_DRAM_CAPACITY: 0.0, cr.MEM_DRAM_CAPACITY_FALLBACK: 512.0}) == 512.0
    assert cr.dram_capacity_kb({}) is None
    # The memory shares use the fallback too: 5.12 GB ballooned of 512 GB is 1 %.
    assert cr.memory_ballooned_pct({cr.MEM_BALLOONED: 5.12 * GB_IN_KB, cr.MEM_DRAM_CAPACITY_FALLBACK: 512.0 * GB_IN_KB}) == 1.0
