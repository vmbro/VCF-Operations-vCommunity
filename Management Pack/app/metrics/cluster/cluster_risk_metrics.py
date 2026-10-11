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
   - take its size (cores, memory) and the size of its powered-on VMs from
     vCenter, which the cluster collector reads once for all objects.
2. Calculate each sub-metric per host, then keep the highest host. CPU
   Imbalance compares the busiest host with the average of the hosts.
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
from metrics.kpi_score import Metric, kpi_score, percent, has_all
from utils.ops_stats import read_latest_stats
from utils.vcenter_inventory import HostHardware, VmSize

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
    # The busiest host, divided by the average of the hosts. 1 means the load is spread evenly.
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

    # --- Allocation: configured vCPU and vRAM of the powered-on VMs, against what the host has ---
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
CPU_RESERVED = "cpu|reservedCapacity_average"           # MHz reserved for VMs
CPU_CAPACITY = "cpu|totalCapacity_average"              # MHz
MEM_CONSUMED = "mem|consumed_average"
MEM_BALLOONED = "mem|vmmemctl_average"
MEM_COMPRESSED = "mem|compressed_average"
MEM_SWAPPED = "mem|swapused_average"
MEM_RESERVED = "mem|reservedCapacity_average"
MEM_CAPACITY = "mem|totalCapacity_average"
# Memory Tiering Latency: the VCF Operations stat is not known yet. Set the key here once it is,
# and the sub-metric starts to count. Until then it has no data and is left out of the KPI.
MEM_TIERING_LATENCY = None

HOST_STATS = [key for key in [
    CPU_THREAD_UTIL, CPU_RESERVED, CPU_CAPACITY, MEM_CONSUMED, MEM_BALLOONED, MEM_COMPRESSED,
    MEM_SWAPPED, MEM_RESERVED, MEM_CAPACITY, MEM_TIERING_LATENCY,
] if key]


# When a VM is a monster, on a given host.
# CPU: more than half of the host's physical cores. Cores, not threads: on a host with 64 cores and
# 128 threads, a VM with more than 32 vCPUs is a monster.
MONSTER_VM_SHARE_OF_CORES = 0.5
# Memory: more than 40 % of the host's DIMM memory, or 256 GB, whichever is smaller. A memory tier such
# as NVMe does not count. On a host with 768 GB of DIMM and 768 GB of NVMe, a VM of 256 GB is a monster.
MONSTER_VM_SHARE_OF_DRAM = 0.4
MONSTER_VM_MEMORY_MB = 256.0 * 1024.0


class HostInventory(NamedTuple):
    """What the collector knows about one host of the cluster, from vCenter."""
    host_id: str                    # VCF Operations resource id, for the stats API
    hardware: Optional[HostHardware]
    vm_sizes: List[VmSize]          # its powered-on VMs


# ---------------------------------------------------------------------------
# Sub-metric formulas, per host. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def share_of_memory(stats: Dict[str, float], keys: List[str]) -> Optional[float]:
    """The sum of the memory stats in keys, as a share (%) of the host's memory capacity."""
    if not has_all(stats, keys + [MEM_CAPACITY]):
        return None
    return percent(sum(stats[key] for key in keys), stats[MEM_CAPACITY])


def cpu_reservation_pct(stats: Dict[str, float]) -> Optional[float]:
    if not has_all(stats, [CPU_RESERVED, CPU_CAPACITY]):
        return None
    return percent(stats[CPU_RESERVED], stats[CPU_CAPACITY])


def cpu_overcommit(host: HostInventory) -> Optional[float]:
    """vCPUs of the powered-on VMs, per physical core."""
    if not host.hardware:
        return None
    return sum(vm.vcpus for vm in host.vm_sizes) / host.hardware.cores


def memory_overcommit(host: HostInventory) -> Optional[float]:
    """Configured memory of the powered-on VMs, per MB of host memory."""
    if not host.hardware:
        return None
    return sum(vm.memory_mb for vm in host.vm_sizes) / host.hardware.memory_mb


def cpu_monster_ratio(host: HostInventory) -> Optional[float]:
    """vCPUs of the largest VM, against the vCPUs at which a VM becomes a monster on this host."""
    if not host.hardware or not host.vm_sizes:
        return None
    monster_vcpus = MONSTER_VM_SHARE_OF_CORES * host.hardware.cores
    return max(vm.vcpus for vm in host.vm_sizes) / monster_vcpus


def memory_monster_ratio(host: HostInventory) -> Optional[float]:
    """Memory of the largest VM, against the memory at which a VM becomes a monster on this host."""
    if not host.hardware or not host.vm_sizes:
        return None
    monster_mb = min(MONSTER_VM_SHARE_OF_DRAM * host.hardware.dram_mb, MONSTER_VM_MEMORY_MB)
    return max(vm.memory_mb for vm in host.vm_sizes) / monster_mb


def cpu_imbalance(cpu_util_per_host: List[float]) -> Optional[float]:
    """The busiest host, divided by the average of the hosts. 1 means an even load."""
    if not cpu_util_per_host:
        return None
    average = sum(cpu_util_per_host) / len(cpu_util_per_host)
    if average <= 0:
        return None
    return max(cpu_util_per_host) / average


def highest(numbers: List[Optional[float]]) -> Optional[float]:
    """The highest of the numbers that have data, or None when none has."""
    known = [number for number in numbers if number is not None]
    return max(known) if known else None


def cluster_risk_values(
    hosts: List[HostInventory], stats_by_host: Dict[str, Dict[str, float]]
) -> Dict[str, Optional[float]]:
    """Value of every sub-metric in METRICS for one cluster. None means "no data"."""
    host_stats = [stats_by_host.get(host.host_id, {}) for host in hosts]
    cpu_util = [stats[CPU_THREAD_UTIL] for stats in host_stats if CPU_THREAD_UTIL in stats]

    return {
        "Highest ESXi CPU Thread Utilization": highest(cpu_util),
        "Worst ESXi CPU Imbalance": cpu_imbalance(cpu_util),
        "Highest ESXi Memory Consumed": highest([share_of_memory(s, [MEM_CONSUMED]) for s in host_stats]),
        "Worst ESXi Memory Ballooned": highest([share_of_memory(s, [MEM_BALLOONED]) for s in host_stats]),
        "Worst ESXi Memory Zip Swap": highest([share_of_memory(s, [MEM_COMPRESSED, MEM_SWAPPED]) for s in host_stats]),
        "Worst ESXi Memory Tiering Latency": highest([s.get(MEM_TIERING_LATENCY) for s in host_stats]),
        "Highest ESXi CPU Reservation": highest([cpu_reservation_pct(s) for s in host_stats]),
        "Highest ESXi Memory Reservation": highest([share_of_memory(s, [MEM_RESERVED]) for s in host_stats]),
        "Highest ESXi CPU Overcommit Ratio": highest([cpu_overcommit(host) for host in hosts]),
        "Highest ESXi Memory Overcommit Ratio": highest([memory_overcommit(host) for host in hosts]),
        "Highest CPU Monster VM to Host Ratio": highest([cpu_monster_ratio(host) for host in hosts]),
        "Highest Memory Monster VM to Host Ratio": highest([memory_monster_ratio(host) for host in hosts]),
    }


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
        if not cluster_obj or not cluster_obj.get_id():
            return

        # Step 1: read the stats of all hosts of the cluster, in one request.
        stats_by_host = read_latest_stats(suite_api_client, [host.host_id for host in hosts], HOST_STATS)

        # Step 2: calculate the sub-metric values. None means "no data".
        values = cluster_risk_values(hosts, stats_by_host)

        # Drop the sub-metrics with no data.
        # Round first, so the KPI is computed from exactly the numbers that are published.
        values = {name: round(value, 2) for name, value in values.items() if value is not None}

        # Step 3: publish the sub-metrics, then score them and publish the KPI.
        for name, value in values.items():
            cluster_obj.with_metric(f"vCommunity|{GROUP}|{name}", value)

        kpi = kpi_score(METRICS, values)
        if kpi is not None:
            cluster_obj.with_metric(f"vCommunity|{GROUP}|{KPI_NAME}", kpi)

        no_data = [metric.name for metric in METRICS if metric.name not in values]
        if no_data:
            logger.info(f"Cluster Risk for {cluster_name}: no data, so left out: {', '.join(no_data)}")

    except Exception as e:
        # A failure here must not stop the collection of the other cluster data.
        logger.warning(f"Failed to retrieve vSphere Cluster Risk metrics for : {cluster_name} - {repr(e)}")
