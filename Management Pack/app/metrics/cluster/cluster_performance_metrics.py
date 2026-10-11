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
to VM_STATS in metrics/vm_contention.py and its two rows to METRICS here and in
host/esxi_performance_metrics.py.

Called from: collectors/cluster/collectClusterData.py, once per cluster.
Overall approach for all KPIs: metrics/README.md
Description for people who do not read code: docs/cluster-performance-kpi.md
"""
import logging
from typing import Dict, List, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, publish_kpi
from metrics.vm_contention import worst_and_percentile, bad_packet_pct, read_vm_contention_stats, read_host_packet_stats

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "Cluster Performance"
KPI_NAME = "Cluster Performance"
# The key of the KPI metric. It must differ from GROUP: VCF Operations rejects a metric key that equals
# the key of its group. The metric is still shown as KPI_NAME.
KPI_KEY = "Cluster Performance Score"

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
# Sub-metric formulas. The worst-VM, 90th-percentile and bad-packet formulas are shared
# with ESXi Performance, so they are in metrics/vm_contention.py.
# ---------------------------------------------------------------------------

def vm_contention_values(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Optional[float]]:
    """Worst-VM and 90th-percentile value of each stat in VM_STATS, over the cluster's VMs."""
    # One request for all VMs of the cluster.
    return worst_and_percentile(read_vm_contention_stats(suite_api_client, vm_ids), vm_ids)


def highest_host_bad_packet_pct(suite_api_client: SuiteApiClient, host_ids: List[str]) -> Optional[float]:
    """Highest share of errored or dropped packets on any one host, in the last collection cycle (5 minutes)."""
    packets_by_host = read_host_packet_stats(suite_api_client, host_ids)
    # The share of each host first, then the highest host.
    per_host = [bad_packet_pct(packets) for packets in packets_by_host.values()]
    per_host = [pct for pct in per_host if pct is not None]
    return max(per_host) if per_host else None


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
        # Step 1 and 2: read the stats and calculate the sub-metric values. None means "no data".
        values = vm_contention_values(suite_api_client, vm_ids)
        values["Highest ESXi Bad Network Packets"] = highest_host_bad_packet_pct(suite_api_client, host_ids)

        # Step 3: publish the sub-metrics, then score them and publish the KPI.
        no_data = publish_kpi(cluster_obj, GROUP, KPI_KEY, METRICS, PUBLISHED_METRICS, values).no_data
        if no_data:
            logger.info(f"Cluster Performance for {cluster_name}: no data, so left out: {', '.join(no_data)}")

    except Exception as e:
        # A failure here must not stop the collection of the other cluster data.
        logger.warning(f"Failed to retrieve vSphere Cluster Performance metrics for : {cluster_name} - {repr(e)}")
