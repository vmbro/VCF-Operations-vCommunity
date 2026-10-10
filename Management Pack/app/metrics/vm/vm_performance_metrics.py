#  Copyright 2026 VCF Operations vCommunity Management Pack
"""VM Performance KPI.

What it is
----------
One 0-100 % score per powered-on VM. 100 is perfect. It answers one question:
is this VM getting the CPU, memory, disk and network it asks for?
It is built from the 14 sub-metrics in METRICS below.

Published on the VM as:
    vCommunity|VM Performance|VM Performance        the KPI
    vCommunity|VM Performance|Memory Zip Swap       the one calculated sub-metric

The other sub-metrics are stats the VM already has, so publishing them again
would only store every number twice, for every VM.

How it is calculated
--------------------
1. Read the stats of all VMs from VCF Operations, in bulk. The vCenter adapter
   has already collected them.
2. For each VM, take the 14 sub-metric values from its stats. Twelve are stats
   as they are. Two are calculated.
3. Score each value and combine the scores into the KPI. This step is the same
   for every KPI and is explained in metrics/kpi_score.py.

Where the limits come from
--------------------------
They are the values used by the "VM Performance" super metric in
content/supermetrics, which this code replaces. Two rows are not "0 is perfect,
lower is better": CPU Run only counts above 60 %, and Guest Free Memory is
"higher is better".

Missing data
------------
A sub-metric with no data is left out of the KPI. A VM without VMware Tools has
no guest stats, so its KPI is built from the remaining sub-metrics. A
powered-off VM gets no KPI at all, because its stats are old.

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
from utils.ops_stats import read_latest_stats

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "VM Performance"
KPI_NAME = "VM Performance"

# One row per sub-metric. The five numbers are the values where its score is 100, 75, 50, 25 and 0.
# "Guest" sub-metrics are measured inside the guest OS by VMware Tools. The others are measured by ESXi.
METRICS = [
    #       name                    unit    best    green   yellow  orange  zero-at

    # --- CPU ---
    # Time the VM was ready to run but had to wait for a physical CPU.
    Metric("CPU Ready",             "%",    0.0,    2.0,    4.0,    8.0,    16.0),
    # Time the VM was held back so that its vCPUs stay in step. Only multi-vCPU VMs have it.
    Metric("CPU Co-Stop",           "%",    0.0,    1.0,    2.0,    4.0,    8.0),
    # Time a vCPU sat idle because it was waiting for disk or network IO.
    Metric("CPU IO Wait",           "%",    0.0,    1.0,    2.0,    4.0,    8.0),
    # Time the VM was interrupted so that ESXi could do work for something else.
    Metric("CPU Overlap",           None,   0.0,    0.5,    1.0,    2.0,    4.0),
    # Time the VM really ran on a physical CPU. Up to 60 % is fine. Near 100 % the VM itself is too small.
    Metric("CPU Run",               "%",    60.0,   80.0,   90.0,   95.0,   100.0),
    # Threads inside the guest OS that wait for a vCPU.
    Metric("Guest CPU Queue",       None,   0.0,    1.0,    2.0,    4.0,    8.0),

    # --- Memory ---
    # Time the VM waited for memory that the host had swapped out or compressed.
    Metric("Memory Contention",     "%",    0.0,    0.5,    1.0,    2.0,    4.0),
    # VM memory that the host took back through the balloon driver.
    Metric("Memory Ballooned",      "%",    0.0,    2.0,    4.0,    8.0,    16.0),
    # VM memory that the host compressed or swapped out. Calculated, see memory_compressed_or_swapped_pct().
    Metric("Memory Zip Swap",       "%",    0.0,    0.5,    1.0,    2.0,    4.0),
    # How fast the guest OS moves memory pages out to its own page file.
    Metric("Guest Page-Out Rate",   None,   0.0,    1000.0, 2000.0, 4000.0, 8000.0),
    # Free memory inside the guest OS. Higher is better, so the limits go down. 1 GB or more scores 100.
    Metric("Guest Free Memory",     "MB",   1024.0, 512.0,  256.0,  128.0,  0.0),

    # --- Disk ---
    # Read and write latency of the VM's virtual disks.
    Metric("Disk Latency",          "ms",   0.0,    20.0,   40.0,   80.0,   160.0),
    # Disk IOs inside the guest OS that wait to be sent.
    Metric("Guest Disk Queue",      None,   0.0,    20.0,   40.0,   80.0,   160.0),

    # --- Network ---
    # Packets the VM sent that were dropped, as a share of the packets it sent.
    Metric("Network Dropped Tx",    "%",    0.0,    0.25,   0.5,    1.0,    2.0),
]

# Only the sub-metrics that the VM does not already have as a stat.
PUBLISHED_METRICS = [metric for metric in METRICS if metric.name == "Memory Zip Swap"]


# ---------------------------------------------------------------------------
# The VCF Operations stats that the sub-metrics are built from.
# ---------------------------------------------------------------------------

# Sub-metric -> the VM stat it is read from, as it is.
# The 20-second peak stats are used instead of the 5-minute averages so the KPI is a leading indicator.
SOURCE_STATS = {
    "CPU Ready":            "cpu|20_sec_peak_readyPct",
    "CPU Co-Stop":          "cpu|20_sec_peak_costopPct",
    "CPU IO Wait":          "cpu|20_sec_peak_iowaitPct",
    "CPU Overlap":          "cpu|20_sec_peak_overlap",
    "CPU Run":              "cpu|net_run",
    "Guest CPU Queue":      "guest|20_sec_peak_cpu_queue",
    "Memory Contention":    "mem|20_sec_peak_host_contentionPct",
    "Memory Ballooned":     "mem|balloonPct",
    "Guest Page-Out Rate":  "guest|page.outRate_latest",
    "Disk Latency":         "virtualDisk|20_sec_peak_totalLatency_average",
    "Guest Disk Queue":     "guest|20_sec_peak_disk_queue",
    "Network Dropped Tx":   "net|droppedTxPct_max",
}

# Stats the two calculated sub-metrics are built from.
GUEST_FREE_MEMORY_KB = "guest|mem.free_latest"      # for Guest Free Memory
MEM_COMPRESSED = "mem|compressed_average"           # for Memory Zip Swap
MEM_SWAPPED = "mem|swapped_average"                 # for Memory Zip Swap
GUEST_USED_MEMORY = "guest|used_memory"             # for Memory Zip Swap

# Every stat that is asked from VCF Operations, for each VM.
VM_STATS = list(SOURCE_STATS.values()) + [GUEST_FREE_MEMORY_KB, MEM_COMPRESSED, MEM_SWAPPED, GUEST_USED_MEMORY]


# ---------------------------------------------------------------------------
# Sub-metric formulas. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def memory_compressed_or_swapped_pct(vm_stats: Dict[str, float]) -> Optional[float]:
    """Compressed plus swapped memory, as a share of the memory the guest uses."""
    # guest|used_memory comes from VMware Tools, so a VM without Tools has no Memory Zip Swap.
    if not has_all(vm_stats, [MEM_COMPRESSED, MEM_SWAPPED, GUEST_USED_MEMORY]):
        return None
    return percent(vm_stats[MEM_COMPRESSED] + vm_stats[MEM_SWAPPED], vm_stats[GUEST_USED_MEMORY])


def guest_free_memory_mb(vm_stats: Dict[str, float]) -> Optional[float]:
    """Free memory inside the guest OS, in MB. The stat is in KB, and the limits in METRICS are in MB."""
    if GUEST_FREE_MEMORY_KB not in vm_stats:
        return None
    return vm_stats[GUEST_FREE_MEMORY_KB] / 1024.0


def vm_performance_values(vm_stats: Dict[str, float]) -> Dict[str, Optional[float]]:
    """Value of every sub-metric in METRICS for one VM. None means "no data"."""
    # The twelve sub-metrics that are a stat as it is. A stat the VM does not have gives None.
    values = {name: vm_stats.get(stat_key) for name, stat_key in SOURCE_STATS.items()}
    # The two calculated ones.
    values["Memory Zip Swap"] = memory_compressed_or_swapped_pct(vm_stats)
    values["Guest Free Memory"] = guest_free_memory_mb(vm_stats)
    return values


# ---------------------------------------------------------------------------
# Reading stats from VCF Operations.
# ---------------------------------------------------------------------------

def read_vm_performance_stats(suite_api_client: SuiteApiClient, vms: List[Object]) -> Dict[str, Dict[str, float]]:
    """Returns {VM resource id: {stat key: latest value}} for all VMs, read in bulk instead of one call per VM."""
    try:
        return read_latest_stats(suite_api_client, [vm.get_id() for vm in vms], VM_STATS)
    except Exception as e:
        # Without stats there is no score, but the rest of the VM collection must still run.
        logger.warning(f"Failed to read VM Performance stats, so no VM Performance this cycle - {repr(e)}")
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
