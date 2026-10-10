#  Copyright 2026 VCF Operations vCommunity Management Pack
"""VM Performance KPI.

What it is
----------
One 0-100 % score per powered-on VM. 100 is perfect. It answers one question:
is the VM, as a virtual motherboard, getting the CPU, memory, disk and network
it asks for from ESXi? It is built from the 9 sub-metrics in METRICS below.
What happens inside the guest OS is scored separately, by the Guest OS
Performance KPI in guest_os_performance_metrics.py.

Published on the VM as:
    vCommunity|VM Performance|VM Performance        the KPI
    vCommunity|VM Performance|Memory Zip Swap       the one calculated sub-metric

The other sub-metrics are stats the VM already has, so publishing them again
would only store every number twice, for every VM.

How it is calculated
--------------------
1. Read the stats of all VMs from VCF Operations, in bulk. The vCenter adapter
   has already collected them. The same request also reads the stats of the
   Guest OS Performance KPI.
2. For each VM, take the 9 sub-metric values from its stats. Eight are stats as
   they are. Memory Zip Swap is calculated.
3. Score each value and combine the scores into the KPI. This step is the same
   for every KPI and is explained in metrics/kpi_score.py.

Where the limits come from
--------------------------
docs/Complex Metrics/Virtual Motherboard Performance metric.png. CPU Run has its
green range marked "Excluded": a VM that runs below 95 % is left out of the
KPI rather than scored 100, see "Skip when green" in metrics/kpi_score.py.

Missing data
------------
A sub-metric with no data is left out of the KPI. A powered-off VM gets no KPI
at all, because its stats are old.

How to change it
----------------
To re-tune a sub-metric, edit its row in METRICS. To add one that is read from
a VM stat as it is, add a row to METRICS and a line to SOURCE_STATS.

Called from: collectors/vm/collectVMData.py. Stats are read once for all VMs,
then the entry point runs once per powered-on VM.
Overall approach for all KPIs: metrics/README.md
Description for people who do not read code: docs/vm-performance-kpi.md
"""
import logging
from typing import Dict, List, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, kpi_score, percent, has_all
from metrics.vm import guest_os_performance_metrics
from utils.ops_stats import read_latest_stats

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "VM Performance"
KPI_NAME = "VM Performance"

# One row per sub-metric. The five numbers are the values where its score is 100, 75, 50, 25 and 0.
# A last value True means "skip when green": the source table marks the green range "Excluded",
# so the row counts in the KPI only when it is outside green.
METRICS = [
    #       name                    unit    best    green   yellow  orange  zero-at  skip-when-green

    # --- VM contention ---
    # Time the VM was held back so that its vCPUs stay in step. Only multi-vCPU VMs have it.
    Metric("CPU Co-Stop",           "%",    0.0,    1.0,    2.0,    4.0,    8.0),
    # Time the VM was ready to run but had to wait for a physical CPU.
    Metric("CPU Ready",             "%",    0.0,    2.0,    4.0,    8.0,    16.0),
    # Time the VM was interrupted so that ESXi could do work for something else.
    Metric("CPU Overlap",           "%",    0.0,    0.5,    1.0,    2.0,    4.0),
    # Time the VM waited for memory that the host had swapped out or compressed.
    Metric("Memory Contention",     "%",    0.0,    0.5,    1.0,    2.0,    4.0),
    # Read and write latency of the VM's virtual disks.
    Metric("Disk Latency",          "ms",   0.0,    10.0,   20.0,   40.0,   80.0),
    # Packets the VM sent that were dropped, as a share of the packets it sent.
    Metric("Network Dropped Tx",    "%",    0.0,    0.25,   0.5,    1.0,    2.0),

    # --- VM utilization ---
    # Time the VM really ran on a physical CPU. Near 100 % the VM itself is too small.
    # Green (below 95 %) is "Excluded": a VM that is not busy says nothing about its performance.
    Metric("CPU Run",               "%",    0.0,    95.0,   97.0,   99.0,   100.0,   True),

    # --- IaaS high utilization: the host is taking memory back from the VM ---
    # VM memory that the host took back through the balloon driver.
    Metric("Memory Ballooned",      "%",    0.0,    2.0,    4.0,    8.0,    16.0),
    # VM memory that the host compressed or swapped out. Calculated, see memory_compressed_or_swapped_pct().
    Metric("Memory Zip Swap",       "%",    0.0,    0.25,   0.5,    1.0,    2.0),
]

# Only the sub-metrics that the VM does not already have as a stat.
PUBLISHED_METRICS = [metric for metric in METRICS if metric.name == "Memory Zip Swap"]


# ---------------------------------------------------------------------------
# The VCF Operations stats that the sub-metrics are built from.
# ---------------------------------------------------------------------------

# Sub-metric -> the VM stat it is read from, as it is.
# The 20-second peak stats are used instead of the 5-minute averages so the KPI is a leading indicator.
SOURCE_STATS = {
    "CPU Co-Stop":          "cpu|20_sec_peak_costopPct",
    "CPU Ready":            "cpu|20_sec_peak_readyPct",
    "CPU Overlap":          "cpu|20_sec_peak_overlap",
    "Memory Contention":    "mem|20_sec_peak_host_contentionPct",
    "Disk Latency":         "virtualDisk|20_sec_peak_totalLatency_average",
    "Network Dropped Tx":   "net|droppedTxPct_max",
    "CPU Run":              "cpu|net_run",
    "Memory Ballooned":     "mem|balloonPct",
}

# Stats Memory Zip Swap is built from.
MEM_COMPRESSED = "mem|compressed_average"
MEM_SWAPPED = "mem|swapped_average"
GUEST_USED_MEMORY = "guest|used_memory"

# Every stat that is asked from VCF Operations, for each VM.
VM_STATS = list(SOURCE_STATS.values()) + [MEM_COMPRESSED, MEM_SWAPPED, GUEST_USED_MEMORY]


# ---------------------------------------------------------------------------
# Sub-metric formulas. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def memory_compressed_or_swapped_pct(vm_stats: Dict[str, float]) -> Optional[float]:
    """Compressed plus swapped memory, as a share of the memory the guest uses."""
    # guest|used_memory comes from VMware Tools, so a VM without Tools has no Memory Zip Swap.
    if not has_all(vm_stats, [MEM_COMPRESSED, MEM_SWAPPED, GUEST_USED_MEMORY]):
        return None
    return percent(vm_stats[MEM_COMPRESSED] + vm_stats[MEM_SWAPPED], vm_stats[GUEST_USED_MEMORY])


def vm_performance_values(vm_stats: Dict[str, float]) -> Dict[str, Optional[float]]:
    """Value of every sub-metric in METRICS for one VM. None means "no data"."""
    # The eight sub-metrics that are a stat as it is. A stat the VM does not have gives None.
    values = {name: vm_stats.get(stat_key) for name, stat_key in SOURCE_STATS.items()}
    # The calculated one.
    values["Memory Zip Swap"] = memory_compressed_or_swapped_pct(vm_stats)
    return values


# ---------------------------------------------------------------------------
# Reading stats from VCF Operations.
# ---------------------------------------------------------------------------

def read_vm_performance_stats(suite_api_client: SuiteApiClient, vms: List[Object]) -> Dict[str, Dict[str, float]]:
    """Returns {VM resource id: {stat key: latest value}} for all VMs, read in bulk instead of one call per VM.

    Reads the stats of both per-VM KPIs, VM Performance and Guest OS Performance, in the same request.
    """
    stat_keys = VM_STATS + [key for key in guest_os_performance_metrics.VM_STATS if key not in VM_STATS]
    try:
        return read_latest_stats(suite_api_client, [vm.get_id() for vm in vms], stat_keys)
    except Exception as e:
        # Without stats there is no score, but the rest of the VM collection must still run.
        logger.warning(f"Failed to read VM Performance stats, so no VM or Guest OS Performance this cycle - {repr(e)}")
        return {}


# ---------------------------------------------------------------------------
# Entry point, called once per powered-on VM.
# ---------------------------------------------------------------------------

def collect_vm_performance_metrics(vm_obj: Object, vm_name: str, vm_stats: Dict[str, float]) -> None:
    """Publishes the sub-metrics in PUBLISHED_METRICS, then the VM Performance KPI.

    vm_stats is the entry of this VM in the result of read_vm_performance_stats().
    """
    try:
        # Step 1: calculate the sub-metric values. None means "no data".
        values = vm_performance_values(vm_stats)

        # Drop the sub-metrics with no data.
        # Round first, so the KPI is computed from exactly the numbers that are published.
        values = {name: round(value, 2) for name, value in values.items() if value is not None}

        # Step 2: publish the calculated sub-metrics, then score all of them and publish the KPI.
        for metric in PUBLISHED_METRICS:
            if metric.name in values:
                vm_obj.with_metric(f"vCommunity|{GROUP}|{metric.name}", values[metric.name])

        kpi = kpi_score(METRICS, values)
        if kpi is not None:
            vm_obj.with_metric(f"vCommunity|{GROUP}|{KPI_NAME}", kpi)

        # Logged at debug level only: there can be thousands of VMs, and no Tools is a normal case.
        no_data = [metric.name for metric in METRICS if metric.name not in values]
        if no_data:
            logger.debug(f"VM Performance for {vm_name}: no data, so left out: {', '.join(no_data)}")

    except Exception as e:
        # A failure here must not stop the collection of the other VM data.
        logger.warning(f"Failed to retrieve VM Performance metrics for : {vm_name} - {repr(e)}")
