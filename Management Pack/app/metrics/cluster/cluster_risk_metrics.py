#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Risk KPI.

What it is
----------
One 0-100 % score per vSphere cluster. 100 is no risk. It is a leading
indicator: it warns before the VMs feel contention. It covers both capacity
and performance. It is built from the 12 sub-metrics in METRICS below.

Cluster Performance shows contention that is happening now. Cluster Risk shows
how close the cluster is to it. Every sub-metric takes the highest or worst
ESXi host, because one full host can hurt its VMs while the cluster average
still looks fine.

Published on the cluster as:
    vCommunity|Cluster Risk|Cluster Risk            the KPI
    vCommunity|Cluster Risk|<sub-metric name>       each of the 12 sub-metrics

How it is calculated
--------------------
1. For each host of the cluster:
   - read its CPU and memory stats from VCF Operations, in one request for all
     hosts of the cluster;
   - take its size (cores, threads) and the size of its powered-on VMs from
     VCF Operations properties, which the cluster collector reads once for
     all objects (utils/ops_inventory.py). DIMM memory still comes from
     vCenter, see utils/vcenter_inventory.py.
2. Calculate every sub-metric for each host (host_risk_values), then keep the
   highest host for each sub-metric (cluster_risk_values).
3. Score each value and combine the scores into the KPI. This step is the same
   for every KPI and is explained in metrics/kpi_score.py.

Where the limits come from
--------------------------
docs/Complex Metrics/vSphere Cluster Risk metric.png. Six green ranges are
marked "Excluded": while green, those rows are left out of the KPI rather than
scored 100, see "Skip when green" in metrics/kpi_score.py.

Missing data
------------
A sub-metric with no data is not published and is left out of the KPI. It is
never treated as 0, because 0 means "no risk". Memory Tiering Latency has no
source stat yet, see MEM_TIERING_LATENCY below, so it is always left out.

Called from: collectors/cluster/collectClusterData.py, once per cluster.
Overall approach for all KPIs: metrics/README.md
Description for people who do not read code: docs/cluster-risk-kpi.md
"""
import logging
from typing import Dict, List, NamedTuple, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, percent, has_all, publish_kpi
from utils.ops_stats import read_latest_stats
from utils.ops_inventory import VmInfo

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "Cluster Risk"
KPI_NAME = "Cluster Risk"

# One row per sub-metric. The five numbers are the values where its score is 100, 75, 50, 25 and 0.
# Every sub-metric here is "lower is better".
# A last value True means "skip when green": the source table marks the green range "Excluded",
# so the row counts in the KPI only when it is outside green.
METRICS = [
    #       name                                      unit   best  green  yellow  orange  zero-at  skip-when-green

    # --- Utilization: how busy the busiest host is ---
    # Green (below 60 %) and Memory Consumed green (below 80 %) are "Excluded": a host that is not busy
    # says nothing about risk, so it is left out rather than scored 100.
    Metric("Highest ESXi CPU Thread Utilization",     "%",   0.0,  60.0,  80.0,   90.0,   95.0,   True),
    # Per host: running CPU threads divided by running CPU cores. 1 means one thread runs on each busy core.
    # 2 means both hyper-threads run on every busy core. The worst host is kept.
    # Green is exactly 1, as in the source table: any imbalance is yellow.
    Metric("Worst ESXi CPU Imbalance",                None,  1.0,  1.0,   1.3,    1.6,    2.0),
    Metric("Highest ESXi Memory Consumed",            "%",   0.0,  80.0,  90.0,   95.0,   100.0,  True),

    # --- Saturation: the host is already reclaiming memory from its VMs ---
    Metric("Worst ESXi Memory Ballooned",             "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    Metric("Worst ESXi Memory Zip Swap",              "%",   0.0,  0.25,  0.5,    1.0,    2.0),
    Metric("Worst ESXi Memory Tiering Latency",       "µs",  0.0,  150.0, 300.0,  450.0,  600.0),

    # --- Reservation: capacity that is promised to VMs, even when they do not use it ---
    # Green (below 10 %) is "Excluded": little reservation says nothing about risk.
    Metric("Highest ESXi CPU Reservation",            "%",   0.0,  10.0,  40.0,   60.0,   80.0,   True),
    Metric("Highest ESXi Memory Reservation",         "%",   0.0,  10.0,  40.0,   60.0,   80.0,   True),

    # --- Allocation: vCPU and memory allocated to the powered-on VMs, against what the host has ---
    # Green (below 1, no overcommit) is "Excluded": it says nothing about risk.
    Metric("Highest ESXi CPU Overcommit Ratio",       None,  0.0,  1.0,   2.0,    3.0,    4.0,    True),
    Metric("Highest ESXi Memory Overcommit Ratio",    None,  0.0,  1.0,   1.4,    1.8,    2.2,    True),

    # --- Monster VM: the largest VM against the size where a VM becomes a monster on its host ---
    # 1 means the largest VM is exactly at that size. See MONSTER_VM_* below.
    Metric("Highest CPU Monster VM to Host Ratio",    None,  0.0,  1.0,   2.0,    3.0,    4.0),
    Metric("Highest Memory Monster VM to Host Ratio", None,  0.0,  1.0,   2.0,    3.0,    4.0),
]

# Every sub-metric is published on the cluster, because none of them exists there as a stat already.
PUBLISHED_METRICS = METRICS


# ---------------------------------------------------------------------------
# The VCF Operations stats of each host that the sub-metrics are built from.
# Memory stats are in KB, CPU capacity in MHz.
# ---------------------------------------------------------------------------

CPU_THREAD_UTIL = "cpu|utilization_average"             # cpu.utilization: % of the host's CPU threads in use
CPU_CORE_UTIL = "cpu|coreUtilization_average"           # cpu.coreUtilization: % of the host's CPU cores in use
CPU_RESERVED = "cpu|reservedCapacity_average"           # MHz reserved for VMs
CPU_CAPACITY = "cpu|totalCapacity_average"              # MHz
MEM_CONSUMED = "mem|consumed_average"
MEM_BALLOONED = "mem|vmmemctl_average"
MEM_COMPRESSED = "mem|compressed_average"
MEM_SWAPPED = "mem|swapused_average"
MEM_RESERVED = "mem|reservedCapacity_average"
MEM_CAPACITY = "mem|totalCapacity_average"
# Allocated to all powered-on VMs of the host. VCF Operations adds them up, so the code does not have to.
VCPUS_ALLOCATED = "cpu|vcpus_allocated_on_all_powered_on_vms"            # number of vCPUs
MEM_ALLOCATED = "mem|memory_allocated_on_all_powered_on_vms"             # KB, like MEM_CAPACITY
# Memory Tiering Latency: the VCF Operations stat is not known yet. Set the key here once it is,
# and the sub-metric starts to count. Until then it has no data and is left out of the KPI.
MEM_TIERING_LATENCY = None

# Every stat that is asked from VCF Operations, for each host. Memory Tiering Latency only once its key is set.
HOST_STATS = [
    CPU_THREAD_UTIL, CPU_CORE_UTIL, CPU_RESERVED, CPU_CAPACITY,
    MEM_CONSUMED, MEM_BALLOONED, MEM_COMPRESSED, MEM_SWAPPED, MEM_RESERVED, MEM_CAPACITY,
    VCPUS_ALLOCATED, MEM_ALLOCATED,
] + ([MEM_TIERING_LATENCY] if MEM_TIERING_LATENCY else [])


# When a VM is a monster, on a given host.
# CPU: more than half of the host's physical cores. Cores, not threads: on a host with 64 cores and
# 128 threads, a VM with more than 32 vCPUs is a monster.
MONSTER_VM_SHARE_OF_CORES = 0.5
# Memory: more than 40 % of the host's DIMM memory, or 256 GB, whichever is smaller. A memory tier such
# as NVMe does not count. On a host with 768 GB of DIMM and 768 GB of NVMe, a VM of 256 GB is a monster.
MONSTER_VM_SHARE_OF_DRAM = 0.4
MONSTER_VM_MEMORY_MB = 256.0 * 1024.0


class HostInventory(NamedTuple):
    """What the collector knows about one host of the cluster. See utils/ops_inventory.py."""
    host_id: str                    # VCF Operations resource id, for the stats API
    cores: Optional[float]          # physical cores
    threads: Optional[float]        # CPU threads
    dram_mb: Optional[float]        # DIMM memory, without a memory tier such as NVMe
    vms: List[VmInfo]               # its powered-on VMs


# ---------------------------------------------------------------------------
# Sub-metric formulas for ONE host. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def memory_share(stats: Dict[str, float], memory_kb: float) -> Optional[float]:
    """memory_kb as a share (%) of the host's memory capacity."""
    if MEM_CAPACITY not in stats:
        return None
    return percent(memory_kb, stats[MEM_CAPACITY])


def memory_consumed_pct(stats: Dict[str, float]) -> Optional[float]:
    if MEM_CONSUMED not in stats:
        return None
    return memory_share(stats, stats[MEM_CONSUMED])


def memory_ballooned_pct(stats: Dict[str, float]) -> Optional[float]:
    if MEM_BALLOONED not in stats:
        return None
    return memory_share(stats, stats[MEM_BALLOONED])


def memory_zip_swap_pct(stats: Dict[str, float]) -> Optional[float]:
    """Compressed (zipped) plus swapped memory of the host, added up, as a share of its memory capacity."""
    if not has_all(stats, [MEM_COMPRESSED, MEM_SWAPPED]):
        return None
    zipped_plus_swapped = stats[MEM_COMPRESSED] + stats[MEM_SWAPPED]
    return memory_share(stats, zipped_plus_swapped)


def memory_tiering_latency(stats: Dict[str, float]) -> Optional[float]:
    """None until MEM_TIERING_LATENCY is set: the source stat is not known yet."""
    if MEM_TIERING_LATENCY is None:
        return None
    return stats.get(MEM_TIERING_LATENCY)


def cpu_reservation_pct(stats: Dict[str, float]) -> Optional[float]:
    """CPU reserved for VMs, as a share of the host's CPU capacity."""
    if not has_all(stats, [CPU_RESERVED, CPU_CAPACITY]):
        return None
    return percent(stats[CPU_RESERVED], stats[CPU_CAPACITY])


def memory_reservation_pct(stats: Dict[str, float]) -> Optional[float]:
    """Memory reserved for VMs, as a share of the host's memory capacity."""
    if MEM_RESERVED not in stats:
        return None
    return memory_share(stats, stats[MEM_RESERVED])


def cpu_imbalance(stats: Dict[str, float], host: HostInventory) -> Optional[float]:
    """ESXi CPU Imbalance of one host: count of running CPU threads / count of running CPU cores."""
    if not host.cores or not host.threads or not has_all(stats, [CPU_THREAD_UTIL, CPU_CORE_UTIL]):
        return None
    running_threads = stats[CPU_THREAD_UTIL] / 100.0 * host.threads
    running_cores = stats[CPU_CORE_UTIL] / 100.0 * host.cores
    # None when no core is running: an idle host has no imbalance to speak of.
    if running_cores <= 0:
        return None
    return running_threads / running_cores


def cpu_overcommit(stats: Dict[str, float], host: HostInventory) -> Optional[float]:
    """vCPUs allocated to the powered-on VMs, per physical core of the host."""
    if not host.cores or VCPUS_ALLOCATED not in stats:
        return None
    return stats[VCPUS_ALLOCATED] / host.cores


def memory_overcommit(stats: Dict[str, float]) -> Optional[float]:
    """Memory allocated to the powered-on VMs, per unit of host memory capacity. Both are in KB."""
    if not has_all(stats, [MEM_ALLOCATED, MEM_CAPACITY]) or stats[MEM_CAPACITY] <= 0:
        return None
    return stats[MEM_ALLOCATED] / stats[MEM_CAPACITY]


def cpu_monster_ratio(host: HostInventory) -> Optional[float]:
    """vCPUs of the largest VM, against the vCPUs at which a VM becomes a monster on this host."""
    vcpus = [vm.vcpus for vm in host.vms if vm.vcpus]
    if not host.cores or not vcpus:
        return None
    monster_vcpus = MONSTER_VM_SHARE_OF_CORES * host.cores
    return max(vcpus) / monster_vcpus


def memory_monster_ratio(host: HostInventory) -> Optional[float]:
    """Memory of the largest VM, against the memory at which a VM becomes a monster on this host."""
    memory = [vm.memory_mb for vm in host.vms if vm.memory_mb]
    if not host.dram_mb or not memory:
        return None
    monster_mb = min(MONSTER_VM_SHARE_OF_DRAM * host.dram_mb, MONSTER_VM_MEMORY_MB)
    return max(memory) / monster_mb


def host_risk_values(host: HostInventory, stats: Dict[str, float]) -> Dict[str, Optional[float]]:
    """Step 2a: the value of every sub-metric in METRICS for ONE host. None means "no data"."""
    return {
        "Highest ESXi CPU Thread Utilization": stats.get(CPU_THREAD_UTIL),
        "Worst ESXi CPU Imbalance": cpu_imbalance(stats, host),
        "Highest ESXi Memory Consumed": memory_consumed_pct(stats),
        "Worst ESXi Memory Ballooned": memory_ballooned_pct(stats),
        "Worst ESXi Memory Zip Swap": memory_zip_swap_pct(stats),
        "Worst ESXi Memory Tiering Latency": memory_tiering_latency(stats),
        "Highest ESXi CPU Reservation": cpu_reservation_pct(stats),
        "Highest ESXi Memory Reservation": memory_reservation_pct(stats),
        "Highest ESXi CPU Overcommit Ratio": cpu_overcommit(stats, host),
        "Highest ESXi Memory Overcommit Ratio": memory_overcommit(stats),
        "Highest CPU Monster VM to Host Ratio": cpu_monster_ratio(host),
        "Highest Memory Monster VM to Host Ratio": memory_monster_ratio(host),
    }


def cluster_risk_values(
    hosts: List[HostInventory], stats_by_host: Dict[str, Dict[str, float]]
) -> Dict[str, Optional[float]]:
    """Step 2b: the value of every sub-metric for the cluster: the highest host. None means "no data"."""
    per_host = [host_risk_values(host, stats_by_host.get(host.host_id, {})) for host in hosts]

    cluster_values = {}
    for metric in METRICS:
        host_values = [values[metric.name] for values in per_host if values[metric.name] is not None]
        cluster_values[metric.name] = max(host_values) if host_values else None
    return cluster_values


# ---------------------------------------------------------------------------
# Entry point, called once per cluster.
# ---------------------------------------------------------------------------

def collect_cluster_risk_metrics(
    cluster_obj: Object, cluster_name: str, hosts: List[HostInventory], suite_api_client: SuiteApiClient
) -> None:
    """Publishes the sub-metrics in METRICS, then the Cluster Risk KPI computed from them.

    hosts holds one HostInventory per ESXi host of the cluster that VCF Operations knows about.
    """
    try:
        # Step 1: read the stats of all hosts of the cluster, in one request.
        stats_by_host = read_latest_stats(suite_api_client, [host.host_id for host in hosts], HOST_STATS)

        # Step 2: calculate each sub-metric per host, then keep the highest host.
        values = cluster_risk_values(hosts, stats_by_host)

        # Step 3: publish the sub-metrics, then score them and publish the KPI.
        no_data = publish_kpi(cluster_obj, GROUP, KPI_NAME, METRICS, PUBLISHED_METRICS, values)
        if no_data:
            logger.info(f"Cluster Risk for {cluster_name}: no data, so left out: {', '.join(no_data)}")

    except Exception as e:
        # A failure here must not stop the collection of the other cluster data.
        logger.warning(f"Failed to retrieve vSphere Cluster Risk metrics for : {cluster_name} - {repr(e)}")
