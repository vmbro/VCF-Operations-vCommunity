#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Guest OS Performance KPI.

What it is
----------
One 0-100 % score per powered-on VM. 100 is perfect. It answers one question:
is the guest OS (Windows or Linux) getting the CPU, disk and memory it needs?
VM Performance scores the virtual motherboard. This KPI scores what runs on it.
It is built from the 4 sub-metrics in METRICS below.

All 4 come from VMware Tools. A VM without Tools has none of them, so it gets
no Guest OS Performance KPI.

Published on the VM as:
    vCommunity|Guest OS Performance|Guest OS Performance        the KPI

The sub-metrics are stats the VM already has, or a simple conversion of one, so
they are not published again.

How it is calculated
--------------------
1. The stats are read together with those of VM Performance, in one bulk
   request for all VMs, by vm_performance_metrics.read_vm_performance_stats().
2. For each VM, take the 4 sub-metric values from its stats.
3. Score each value and combine the scores into the KPI. This step is the same
   for every KPI and is explained in metrics/kpi_score.py.

Where the limits come from
--------------------------
docs/Complex Metrics/Guest OS Performance metric.png. Free Memory is "higher is
better", so its limits go down.

Called from: collectors/vm/collectVMData.py, once per powered-on VM.
Overall approach for all KPIs: metrics/README.md
Description for people who do not read code: docs/guest-os-performance-kpi.md
"""
import logging
from typing import Dict, Optional
from aria.ops.object import Object
from metrics.kpi_score import Metric, publish_kpi

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "Guest OS Performance"
KPI_NAME = "Guest OS Performance"
# The key of the KPI metric. It must differ from GROUP: VCF Operations rejects a metric key that equals
# the key of its group. The metric is still shown as KPI_NAME.
KPI_KEY = "Guest OS Performance Score"

# One row per sub-metric. The five numbers are the values where its score is 100, 75, 50, 25 and 0.
METRICS = [
    #       name                            unit    best    green   yellow  orange  zero-at

    # --- Guest OS contention ---
    # Threads waiting for a vCPU, per vCPU. The stat is already per vCPU, so it is used as it is.
    Metric("Guest CPU Run Queue per vCPU",  None,   0.0,    2.0,    4.0,    8.0,    16.0),
    # Disk IOs inside the guest OS that wait to be sent.
    Metric("Guest Disk Queue",              None,   0.0,    20.0,   40.0,   80.0,   160.0),

    # --- Guest OS utilization ---
    # Free memory inside the guest OS. Higher is better, so the limits go down. 1 GB or more scores 100.
    Metric("Guest Free Memory",             "MB",   1024.0, 512.0,  256.0,  128.0,  0.0),
    # How fast the guest OS moves memory pages out to its own page file, in pages per second.
    Metric("Guest Page-Out Rate",           None,   0.0,    1000.0, 2000.0, 4000.0, 8000.0),
]

# Every sub-metric is a stat the VM already has, or a simple conversion of one. Only the KPI is published.
PUBLISHED_METRICS = []


# ---------------------------------------------------------------------------
# The VCF Operations stats that the sub-metrics are built from.
# ---------------------------------------------------------------------------

GUEST_CPU_QUEUE = "guest|20_sec_peak_cpu_queue"           # already per vCPU
GUEST_DISK_QUEUE = "guest|20_sec_peak_disk_queue"
GUEST_FREE_MEMORY_KB = "guest|mem.free_latest"
GUEST_PAGE_OUT_RATE = "guest|page.outRate_latest"

# Every stat that is asked from VCF Operations, for each VM. Read by vm_performance_metrics.
VM_STATS = [GUEST_CPU_QUEUE, GUEST_DISK_QUEUE, GUEST_FREE_MEMORY_KB, GUEST_PAGE_OUT_RATE]


# ---------------------------------------------------------------------------
# Sub-metric formulas. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def guest_free_memory_mb(vm_stats: Dict[str, float]) -> Optional[float]:
    """Free memory inside the guest OS, in MB. The stat is in KB, and the limits in METRICS are in MB."""
    if GUEST_FREE_MEMORY_KB not in vm_stats:
        return None
    return vm_stats[GUEST_FREE_MEMORY_KB] / 1024.0


def guest_os_performance_values(vm_stats: Dict[str, float]) -> Dict[str, Optional[float]]:
    """Value of every sub-metric in METRICS for one VM. None means "no data"."""
    return {
        "Guest CPU Run Queue per vCPU": vm_stats.get(GUEST_CPU_QUEUE),
        "Guest Disk Queue": vm_stats.get(GUEST_DISK_QUEUE),
        "Guest Free Memory": guest_free_memory_mb(vm_stats),
        "Guest Page-Out Rate": vm_stats.get(GUEST_PAGE_OUT_RATE),
    }


# ---------------------------------------------------------------------------
# Entry point, called once per powered-on VM.
# ---------------------------------------------------------------------------

def collect_guest_os_performance_metrics(vm_obj: Object, vm_name: str, vm_stats: Dict[str, float]) -> Optional[float]:
    """Publishes the Guest OS Performance KPI. Returns it, or None.

    vm_stats is the entry of this VM in the result of vm_performance_metrics.read_vm_performance_stats().
    """
    try:
        # Step 1 (reading the stats) was done once for all VMs, by vm_performance_metrics.read_vm_performance_stats().
        # Step 2: calculate the sub-metric values. None means "no data".
        values = guest_os_performance_values(vm_stats)

        # Step 3: score them and publish the KPI. The sub-metrics are not published, see PUBLISHED_METRICS.
        published = publish_kpi(vm_obj, GROUP, KPI_KEY, METRICS, PUBLISHED_METRICS, values)
        # Logged at debug level only: there can be thousands of VMs, and no Tools is a normal case.
        if published.no_data:
            logger.debug(f"Guest OS Performance for {vm_name}: no data, so left out: {', '.join(published.no_data)}")
        return published.score

    except Exception as e:
        # A failure here must not stop the collection of the other VM data.
        logger.warning(f"Failed to retrieve Guest OS Performance metrics for : {vm_name} - {repr(e)}")
        return None
