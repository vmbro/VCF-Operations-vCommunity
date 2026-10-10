#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Performance KPI.

What it is
----------
One 0-100 % score per vSphere cluster. 100 is perfect. It answers one question:
are the VMs in this cluster getting the CPU, memory and network they ask for?
It is built from the 10 sub-metrics in METRICS below.

Published on the cluster as:
    vCommunity|Cluster Performance|Cluster Performance      the KPI
    vCommunity|Cluster Performance|<sub-metric name>        each of the 10 sub-metrics

How it is calculated
--------------------
1. Read the stats from VCF Operations: for the cluster itself, for its VMs and
   for its ESXi hosts. The vCenter adapter has already collected them.
2. Calculate the 10 sub-metric values from those stats.
3. Score each value and combine the scores into the KPI. This step is the same
   for every KPI and is explained in metrics/kpi_score.py.

Where the limits come from
--------------------------
They are the values used by the "Cluster Performance" super metric in
content/supermetrics, which this code replaces. In every row each limit is
double the previous one. The worst-VM rows use higher limits than the
cluster-average rows, because a single VM peaks far above the average.

Missing data
------------
A sub-metric with no data is not published and is left out of the KPI. It is
never treated as 0, because 0 means "perfect".

How to change it
----------------
To re-tune a sub-metric, edit its row in METRICS. To add one, add a row and one
line in collect_cluster_performance_metrics() that supplies its value.

Called from: collectors/cluster/collectClusterData.py, once per cluster.
Overall approach for all KPIs: metrics/README.md
Description for people who do not read code: docs/cluster-performance-kpi.md
"""
import logging
from typing import Dict, List, Optional, Tuple
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, kpi_score, percent, has_all
from utils.ops_stats import read_latest_stats, read_stat_totals

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "Cluster Performance"
KPI_NAME = "Cluster Performance"

# One row per sub-metric. The five numbers are the values where its score is 100, 75, 50, 25 and 0.
# Every sub-metric here is "lower is better", and 0 is perfect.
METRICS = [
    #       name                                unit   best  green  yellow  orange  zero-at

    # --- Average across the cluster's VMs. Shows a problem that many VMs share. ---
    # Time the VMs were ready to run but had to wait for a physical CPU.
    Metric("CPU Ready",                         "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    # Time multi-vCPU VMs were held back so that their vCPUs stay in step.
    Metric("CPU Co-Stop",                       "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    # Time the VMs waited for memory that the host had swapped out or compressed.
    Metric("Memory Contention",                 "%",   0.0,  0.5,   1.0,    2.0,    4.0),

    # --- Worst VM in the cluster. Shows a problem that the average hides. ---
    Metric("Worst VM CPU Ready",                "%",   0.0,  4.0,   8.0,    16.0,   32.0),
    Metric("Worst VM CPU Co-Stop",              "%",   0.0,  2.0,   4.0,    8.0,    16.0),
    Metric("Worst VM Memory Contention",        "%",   0.0,  1.0,   2.0,    4.0,    8.0),

    # --- Worst ESXi host in the cluster ---
    # Errored and dropped packets as a share of all packets, on the host where that share is highest.
    Metric("Worst ESXi Bad Network Packets",    "%",   0.0,  0.2,   0.4,    0.8,    1.6),

    # --- Cluster as a whole ---
    # Many vMotions mean DRS keeps moving VMs to find them resources. It is a rate, not a percentage.
    Metric("vMotions per 100 Running VMs",      None,  0.0,  1.0,   2.0,    4.0,    8.0),
    # VM memory that the hosts compressed or swapped out. The last resort when memory runs short.
    Metric("Memory Zip Swap",                   "%",   0.0,  0.25,  0.5,    1.0,    2.0),
    # VM memory that the hosts took back through the balloon driver. An earlier sign than Zip Swap.
    Metric("Memory Ballooned",                  "%",   0.0,  1.0,   2.0,    4.0,    8.0),
]

# Every sub-metric is published on the cluster, because none of them exists there as a stat already.
PUBLISHED_METRICS = METRICS


# ---------------------------------------------------------------------------
# The VCF Operations stats that the sub-metrics are built from.
# ---------------------------------------------------------------------------

# Read from each VM in the cluster.
# VM stat -> (sub-metric holding the average of all VMs, sub-metric holding the worst VM).
# The 20-second peak stats are used instead of the 5-minute averages so the KPI is a leading indicator.
VM_STATS = {
    "cpu|20_sec_peak_readyPct":           ("CPU Ready",         "Worst VM CPU Ready"),
    "cpu|20_sec_peak_costopPct":          ("CPU Co-Stop",       "Worst VM CPU Co-Stop"),
    "mem|20_sec_peak_host_contentionPct": ("Memory Contention", "Worst VM Memory Contention"),
}

# Read from the cluster itself.
# summary|number_vmotion is the count for the last collection cycle, not a running total.
VMOTION_COUNT = "summary|number_vmotion"
RUNNING_VMS = "summary|number_running_vms"
MEM_COMPRESSED = "mem|compressed_average"
MEM_SWAPPED_OUT = "mem|swapout_average"
MEM_CONSUMED = "mem|consumed_average"
MEM_SYSTEM_USAGE = "mem|sysUsage_average"
MEM_BALLOONED = "mem|vmmemctl_average"
CLUSTER_STATS = [
    VMOTION_COUNT, RUNNING_VMS, MEM_COMPRESSED, MEM_SWAPPED_OUT, MEM_CONSUMED, MEM_SYSTEM_USAGE, MEM_BALLOONED,
]

# Read from each ESXi host in the cluster. These are packet counts per collection cycle.
HOST_BAD_PACKET_STATS = [
    "net|errorsRx_summation_sum", "net|errorsTx_summation_sum",
    "net|droppedRx_summation_sum", "net|droppedTx_summation_sum",
]
HOST_PACKET_STATS = ["net|packetsRx_summation_sum", "net|packetsTx_summation_sum"]

# Bad packets are added up over this window. A single collection cycle is too noisy:
# one burst of drops would push the sub-metric into the red tier, where its weight is 8.
BAD_PACKET_WINDOW_MINUTES = 30


# ---------------------------------------------------------------------------
# Sub-metric formulas. Each returns None when it has no data to work with.
# ---------------------------------------------------------------------------

def average_and_max(numbers: List[float]) -> Tuple[Optional[float], Optional[float]]:
    """Returns (average, highest), or (None, None) when the list is empty."""
    if not numbers:
        return None, None
    return sum(numbers) / len(numbers), max(numbers)


def vmotion_rate(cluster_stats: Dict[str, float]) -> Optional[float]:
    """vMotions in the last collection cycle, per 100 running VMs."""
    if not has_all(cluster_stats, [VMOTION_COUNT, RUNNING_VMS]):
        return None
    return percent(cluster_stats[VMOTION_COUNT], cluster_stats[RUNNING_VMS])


def memory_compressed_or_swapped_pct(cluster_stats: Dict[str, float]) -> Optional[float]:
    """Share of VM memory that is compressed or swapped out."""
    if not has_all(cluster_stats, [MEM_COMPRESSED, MEM_SWAPPED_OUT, MEM_CONSUMED, MEM_SYSTEM_USAGE]):
        return None
    zipped_or_swapped = cluster_stats[MEM_COMPRESSED] + cluster_stats[MEM_SWAPPED_OUT]
    # Consumed memory includes what ESXi uses for itself. Take that out, so only VM memory is left.
    consumed_by_vms = cluster_stats[MEM_CONSUMED] - cluster_stats[MEM_SYSTEM_USAGE]
    # The whole is what the VMs hold in RAM plus what was zipped or swapped away from them.
    return percent(zipped_or_swapped, zipped_or_swapped + consumed_by_vms)


def memory_ballooned_pct(cluster_stats: Dict[str, float]) -> Optional[float]:
    """Share of VM memory that is ballooned."""
    if not has_all(cluster_stats, [MEM_BALLOONED, MEM_CONSUMED, MEM_SYSTEM_USAGE]):
        return None
    ballooned = cluster_stats[MEM_BALLOONED]
    # Same whole as in memory_compressed_or_swapped_pct(): VM memory in RAM plus what was taken away.
    consumed_by_vms = cluster_stats[MEM_CONSUMED] - cluster_stats[MEM_SYSTEM_USAGE]
    return percent(ballooned, ballooned + consumed_by_vms)


def vm_contention_stats(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Optional[float]]:
    """Average and worst-VM value of each stat in VM_STATS."""
    # One request for all VMs of the cluster.
    latest_by_vm = read_latest_stats(suite_api_client, vm_ids, list(VM_STATS))
    values = {}

    for stat_key, (average_name, worst_name) in VM_STATS.items():
        # A VM that does not have this stat is left out of the average.
        per_vm = [vm_stats[stat_key] for vm_stats in latest_by_vm.values() if stat_key in vm_stats]
        values[average_name], values[worst_name] = average_and_max(per_vm)
    return values


def worst_host_bad_packet_pct(suite_api_client: SuiteApiClient, host_ids: List[str]) -> Optional[float]:
    """Highest share of errored or dropped packets on any one host, over BAD_PACKET_WINDOW_MINUTES."""
    totals_by_host = read_stat_totals(
        suite_api_client, host_ids, HOST_BAD_PACKET_STATS + HOST_PACKET_STATS, BAD_PACKET_WINDOW_MINUTES
    )
    per_host = []

    for totals in totals_by_host.values():
        # A host with one of the six counters missing would give a wrong share, so it is skipped.
        if not has_all(totals, HOST_BAD_PACKET_STATS + HOST_PACKET_STATS):
            continue
        bad_packets = sum(totals[key] for key in HOST_BAD_PACKET_STATS)
        all_packets = sum(totals[key] for key in HOST_PACKET_STATS)
        # None when the host sent and received no packets at all.
        bad_pct = percent(bad_packets, all_packets)
        if bad_pct is not None:
            per_host.append(bad_pct)

    _, worst = average_and_max(per_host)
    return worst


# ---------------------------------------------------------------------------
# Reading stats from VCF Operations.
# ---------------------------------------------------------------------------

def read_cluster_stats(suite_api_client: SuiteApiClient, cluster_id: str) -> Dict[str, float]:
    """Latest value of each stat in CLUSTER_STATS. Stats with no data are absent."""
    return read_latest_stats(suite_api_client, [cluster_id], CLUSTER_STATS).get(cluster_id, {})


def _child_resource_ids(vcenter_children, objects_by_moid: Dict[str, Object]) -> List[str]:
    """VCF Operations resource ids of the vCenter children (VMs or hosts) that VCF Operations knows about."""
    resource_ids = []
    for child in vcenter_children:
        # vCenter names an object by its MoRef id. VCF Operations uses its own id, which the stats API needs.
        child_obj = objects_by_moid.get(getattr(child, "_moId", ""))
        if child_obj:
            resource_ids.append(child_obj.get_id())
    return resource_ids


# ---------------------------------------------------------------------------
# Entry point, called once per cluster.
# ---------------------------------------------------------------------------

def collect_cluster_performance_metrics(
    cluster_obj: Object,
    cluster_name: str,
    cluster_ref,
    vms_by_uuid: Dict[str, Object],
    hosts_by_uuid: Dict[str, Object],
    suite_api_client: SuiteApiClient
) -> None:
    """Publishes the sub-metrics in METRICS, then the Cluster Performance KPI computed from them."""
    try:
        if not cluster_obj or not cluster_obj.get_id():
            return

        # Step 1: read the cluster's own stats, and find the ids of its VMs and hosts.
        cluster_stats = read_cluster_stats(suite_api_client, cluster_obj.get_id())
        vm_ids = _child_resource_ids(getattr(cluster_ref, "vm", []), vms_by_uuid)
        host_ids = _child_resource_ids(getattr(cluster_ref, "host", []), hosts_by_uuid)

        # Step 2: calculate the sub-metric values. None means "no data".
        values = vm_contention_stats(suite_api_client, vm_ids)
        values["Worst ESXi Bad Network Packets"] = worst_host_bad_packet_pct(suite_api_client, host_ids)
        values["vMotions per 100 Running VMs"] = vmotion_rate(cluster_stats)
        values["Memory Zip Swap"] = memory_compressed_or_swapped_pct(cluster_stats)
        values["Memory Ballooned"] = memory_ballooned_pct(cluster_stats)

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
            logger.info(f"Cluster Performance for {cluster_name}: no data, so left out: {', '.join(no_data)}")

        logger.debug(f"Successfully collected vSphere Cluster Performance metrics for the cluster: {cluster_name}")

    except Exception as e:
        # A failure here must not stop the collection of the other cluster data.
        logger.warning(f"Failed to retrieve vSphere Cluster Performance metrics for : {cluster_name} - {repr(e)}")
