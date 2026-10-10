#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Performance KPI.

What it is
----------
One 0-100 % score per vSphere cluster. 100 is perfect. It answers one question:
are the VMs in this cluster getting the CPU, memory, disk and network they ask for?
It measures actual contention, not potential. It is built from the 9 sub-metrics
in METRICS below.

The sub-metrics answer two questions about the powered-on VMs in the cluster:
    How deep?   The worst VM. Shows a problem that hits one VM hard.
    How broad?  The 90th percentile across the VMs. Shows a problem that many
                VMs share. 90 % of the VMs are at or below this value.
A ninth sub-metric covers the network of the worst ESXi host.

Published on the cluster as:
    vCommunity|Cluster Performance|Cluster Performance      the KPI
    vCommunity|Cluster Performance|<sub-metric name>        each of the 9 sub-metrics

How it is calculated
--------------------
1. Read the stats of the cluster's powered-on VMs and of its ESXi hosts from
   VCF Operations. The vCenter adapter has already collected them.
2. Calculate the 9 sub-metric values from those stats.
3. Score each value and combine the scores into the KPI. This step is the same
   for every KPI and is explained in metrics/kpi_score.py.

Where the limits come from
--------------------------
docs/Complex Metrics/vSphere Cluster Performance metric.png. The worst-VM rows
have higher limits than the 90th-percentile rows, because a single VM peaks far
above most of the others.

Missing data
------------
A sub-metric with no data is not published and is left out of the KPI. It is
never treated as 0, because 0 means "perfect".

How to change it
----------------
To re-tune a sub-metric, edit its row in METRICS. To add a VM stat, add a line
to VM_STATS and its two rows to METRICS.

Called from: collectors/cluster/collectClusterData.py, once per cluster.
Overall approach for all KPIs: metrics/README.md
Description for people who do not read code: docs/cluster-performance-kpi.md
"""
import logging
import math
from typing import Dict, List, Optional
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
# A last value True means "skip when green": the source table marks the green range "Excluded",
# so the row counts in the KPI only when it is outside green.
METRICS = [
    #       name                                      unit   best  green  yellow  orange  zero-at  skip-when-green

    # --- How deep? The worst VM in the cluster. ---
    # Time the VM was ready to run but had to wait for a physical CPU.
    Metric("Worst VM CPU Ready",                      "%",   0.0,  4.0,   8.0,    16.0,   32.0),
    # Time a multi-vCPU VM was held back so that its vCPUs stay in step.
    Metric("Worst VM CPU Co-Stop",                    "%",   0.0,  2.0,   4.0,    8.0,    16.0),
    # Time the VM waited for memory that the host had swapped out or compressed.
    Metric("Worst VM Memory Latency",                 "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    # Read and write latency of the VM's virtual disks.
    Metric("Worst VM Disk Latency",                   "ms",  0.0,  40.0,  80.0,   160.0,  320.0),

    # --- How broad? The 90th percentile across the VMs in the cluster. ---
    Metric("90th Percentile VM CPU Ready",            "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    Metric("90th Percentile VM CPU Co-Stop",          "%",   0.0,  0.5,   1.0,    2.0,    4.0),
    Metric("90th Percentile VM Memory Latency",       "%",   0.0,  0.5,   1.0,    2.0,    4.0),
    Metric("90th Percentile VM Disk Latency",         "ms",  0.0,  20.0,  40.0,   60.0,   80.0),

    # --- The worst ESXi host in the cluster ---
    # Errored and dropped packets as a share of all packets, on the host where that share is highest.
    # Green (exactly 0) is "Excluded" in the source table: dropped packets are rare, so while it is 0 it is
    # left out of the KPI instead of giving it a free 100 (skip when green). Any bad packet is yellow.
    Metric("Highest ESXi Bad Network Packets",        "%",   0.0,  0.0,   0.2,    0.4,    0.8,    True),
]

# Every sub-metric is published on the cluster, because none of them exists there as a stat already.
PUBLISHED_METRICS = METRICS


# ---------------------------------------------------------------------------
# The VCF Operations stats that the sub-metrics are built from.
# ---------------------------------------------------------------------------

# Read from each powered-on VM in the cluster.
# VM stat -> (sub-metric holding the worst VM, sub-metric holding the 90th percentile).
# The 20-second peak stats are used instead of the 5-minute averages so the KPI is a leading indicator.
VM_STATS = {
    "cpu|20_sec_peak_readyPct":                     ("Worst VM CPU Ready",       "90th Percentile VM CPU Ready"),
    "cpu|20_sec_peak_costopPct":                    ("Worst VM CPU Co-Stop",     "90th Percentile VM CPU Co-Stop"),
    "mem|20_sec_peak_host_contentionPct":           ("Worst VM Memory Latency",  "90th Percentile VM Memory Latency"),
    "virtualDisk|20_sec_peak_totalLatency_average": ("Worst VM Disk Latency",    "90th Percentile VM Disk Latency"),
}

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

def percentile_90(numbers: List[float]) -> Optional[float]:
    """The value that 90 % of the numbers are at or below. None when the list is empty.

    Nearest-rank method: sort the numbers and take the one at position 90 % of the count, rounded up.
    With 20 VMs that is the 18th lowest. With fewer than 10 VMs it is the highest.
    """
    if not numbers:
        return None
    position = math.ceil(0.9 * len(numbers))
    return sorted(numbers)[position - 1]


def vm_contention_values(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Optional[float]]:
    """Worst-VM and 90th-percentile value of each stat in VM_STATS."""
    # One request for all VMs of the cluster.
    latest_by_vm = read_latest_stats(suite_api_client, vm_ids, list(VM_STATS))
    values = {}

    for stat_key, (worst_name, percentile_name) in VM_STATS.items():
        # A VM that does not have this stat is left out.
        per_vm = [vm_stats[stat_key] for vm_stats in latest_by_vm.values() if stat_key in vm_stats]
        values[worst_name] = max(per_vm) if per_vm else None
        values[percentile_name] = percentile_90(per_vm)
    return values


def highest_host_bad_packet_pct(suite_api_client: SuiteApiClient, host_ids: List[str]) -> Optional[float]:
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

    return max(per_host) if per_host else None


# ---------------------------------------------------------------------------
# Finding the cluster's VMs and hosts.
# ---------------------------------------------------------------------------

def powered_on_vms_by_host(vm_props) -> Dict[str, List[str]]:
    """{host MoRef id: [MoRef ids of the powered-on VMs on that host]}.

    vm_props is the vCenter answer for every VM, with the properties runtime.host and runtime.powerState.
    A powered-off VM is left out: its last stats in VCF Operations are old and would skew the KPI.
    """
    vms_by_host = {}
    for vm_data in vm_props:
        props = {prop.name: prop.val for prop in vm_data.propSet}
        host = props.get("runtime.host")
        if host is None or props.get("runtime.powerState") != "poweredOn":
            continue
        vms_by_host.setdefault(host._moId, []).append(vm_data.obj._moId)
    return vms_by_host


def resource_ids(moids: List[str], objects_by_moid: Dict[str, Object]) -> List[str]:
    """VCF Operations resource ids of the vCenter objects (VMs or hosts) that VCF Operations knows about."""
    # vCenter names an object by its MoRef id. VCF Operations uses its own id, which the stats API needs.
    return [objects_by_moid[moid].get_id() for moid in moids if moid in objects_by_moid]


# ---------------------------------------------------------------------------
# Entry point, called once per cluster.
# ---------------------------------------------------------------------------

def collect_cluster_performance_metrics(
    cluster_obj: Object,
    cluster_name: str,
    vm_ids: List[str],
    host_ids: List[str],
    suite_api_client: SuiteApiClient
) -> None:
    """Publishes the sub-metrics in METRICS, then the Cluster Performance KPI computed from them.

    vm_ids are the VCF Operations ids of the cluster's powered-on VMs, host_ids those of its ESXi hosts.
    """
    try:
        if not cluster_obj or not cluster_obj.get_id():
            return

        # Step 1 and 2: read the stats and calculate the sub-metric values. None means "no data".
        values = vm_contention_values(suite_api_client, vm_ids)
        values["Highest ESXi Bad Network Packets"] = highest_host_bad_packet_pct(suite_api_client, host_ids)

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
