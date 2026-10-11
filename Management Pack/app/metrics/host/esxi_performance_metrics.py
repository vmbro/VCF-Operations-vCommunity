#  Copyright 2026 VCF Operations vCommunity Management Pack
"""ESXi Performance KPI.

What it is
----------
One 0-100 % score per ESXi host. 100 is perfect. It answers one question:
are the VMs on this host getting the CPU, memory, disk and network they ask for?
It measures actual contention, not potential. It shows how bad the contention
is, not why it happens. It is built from the 9 sub-metrics in METRICS below.

The sub-metrics answer two questions about the powered-on VMs on the host:
    How deep?   The worst VM. Shows a problem that hits one VM hard.
    How broad?  The 90th percentile across the VMs. Shows a problem that many
                VMs share. 90 % of the VMs are at or below this value.
A ninth sub-metric covers the network of the host itself.

They are the same sub-metrics as Cluster Performance, measured for one host
instead of a whole cluster. The formulas are shared, in metrics/vm_contention.py.

Published on the host as:
    vCommunity|ESXi Performance|ESXi Performance        the KPI
    vCommunity|ESXi Performance|<sub-metric name>       each of the 9 sub-metrics

How it is calculated
--------------------
1. Read the stats of all powered-on VMs, and the packet counters of all hosts,
   from VCF Operations, in bulk, once per collection cycle.
2. For each host, calculate the 9 sub-metric values from the stats of its VMs
   and its own packet counters.
3. Score each value and combine the scores into the KPI. This step is the same
   for every KPI and is explained in metrics/kpi_score.py.

Where the limits come from
--------------------------
docs/Complex Metrics/vSphere ESXi Performance metric.png.

Missing data
------------
A sub-metric with no data is not published and is left out of the KPI. It is
never treated as 0, because 0 means "perfect".

Called from: collectors/host/collectHostData.py. Stats are read once for all
hosts, then the entry point runs once per connected host.
Overall approach for all KPIs: metrics/README.md
Description for people who do not read code: docs/esxi-performance-kpi.md
"""
import logging
from typing import Dict, List, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from metrics.kpi_score import Metric, kpi_score
from metrics.vm_contention import (
    worst_and_percentile, bad_packet_pct, read_vm_contention_stats, read_host_packet_totals,
)

logger = logging.getLogger(__name__)

# The names shown in VCF Operations: the group that holds the metrics, and the KPI inside it.
GROUP = "ESXi Performance"
KPI_NAME = "ESXi Performance"

# One row per sub-metric. The five numbers are the values where its score is 100, 75, 50, 25 and 0.
# Every sub-metric here is "lower is better", and 0 is perfect.
# A last value True means "skip when green": the source table marks the green range "Excluded",
# so the row counts in the KPI only when it is outside green.
METRICS = [
    #       name                                      unit   best  green  yellow  orange  zero-at  skip-when-green

    # --- How deep? The worst VM on the host. ---
    Metric("Worst VM CPU Ready",                      "%",   0.0,  4.0,   8.0,    16.0,   32.0),
    Metric("Worst VM CPU Co-Stop",                    "%",   0.0,  2.0,   4.0,    8.0,    16.0),
    Metric("Worst VM Memory Latency",                 "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    Metric("Worst VM Disk Latency",                   "ms",  0.0,  40.0,  80.0,   160.0,  320.0),

    # --- How broad? The 90th percentile across the VMs on the host. ---
    Metric("90th Percentile VM CPU Ready",            "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    Metric("90th Percentile VM CPU Co-Stop",          "%",   0.0,  0.5,   1.0,    2.0,    4.0),
    Metric("90th Percentile VM Memory Latency",       "%",   0.0,  0.5,   1.0,    2.0,    4.0),
    Metric("90th Percentile VM Disk Latency",         "ms",  0.0,  20.0,  40.0,   60.0,   80.0),

    # --- The host itself ---
    # Errored and dropped packets as a share of all packets, over the last 30 minutes.
    # Green (exactly 0) is "Excluded" in the source table: skipped while 0, because it is rare. Any bad packet is yellow.
    Metric("ESXi Bad Network Packets",                "%",   0.0,  0.0,   0.2,    0.4,    0.8,    True),
]

# Every sub-metric is published on the host, because none of them exists there as a stat already.
PUBLISHED_METRICS = METRICS


# ---------------------------------------------------------------------------
# Reading stats from VCF Operations, once for all hosts.
# ---------------------------------------------------------------------------

class EsxiPerformanceStats:
    """The stats of one collection cycle: of every powered-on VM, and the packet totals of every host."""

    def __init__(self, vm_stats: Dict[str, Dict[str, float]], host_packet_totals: Dict[str, Dict[str, float]]):
        self.vm_stats = vm_stats
        self.host_packet_totals = host_packet_totals


def read_esxi_performance_stats(
    suite_api_client: SuiteApiClient, vm_ids: List[str], host_ids: List[str]
) -> EsxiPerformanceStats:
    """Reads the stats of all VMs and all hosts in bulk, instead of one call per host."""
    try:
        return EsxiPerformanceStats(
            read_vm_contention_stats(suite_api_client, vm_ids),
            read_host_packet_totals(suite_api_client, host_ids),
        )
    except Exception as e:
        # Without stats there is no score, but the rest of the host collection must still run.
        logger.warning(f"Failed to read ESXi Performance stats, so no ESXi Performance this cycle - {repr(e)}")
        return EsxiPerformanceStats({}, {})


# ---------------------------------------------------------------------------
# Entry point, called once per connected ESXi host.
# ---------------------------------------------------------------------------

def esxi_performance_values(stats: EsxiPerformanceStats, host_id: str, vm_ids: List[str]) -> Dict[str, Optional[float]]:
    """Value of every sub-metric in METRICS for one host. None means "no data"."""
    values = worst_and_percentile(stats.vm_stats, vm_ids)
    values["ESXi Bad Network Packets"] = bad_packet_pct(stats.host_packet_totals.get(host_id, {}))
    return values


def collect_esxi_performance_metrics(
    host_obj: Object, host_name: str, vm_ids: List[str], stats: EsxiPerformanceStats
) -> None:
    """Publishes the sub-metrics in METRICS, then the ESXi Performance KPI computed from them.

    vm_ids are the VCF Operations ids of the powered-on VMs on this host.
    stats is the result of read_esxi_performance_stats().
    """
    try:
        if not host_obj or not host_obj.get_id():
            return

        # Step 2: calculate the sub-metric values. None means "no data".
        values = esxi_performance_values(stats, host_obj.get_id(), vm_ids)

        # Drop the sub-metrics with no data.
        # Round first, so the KPI is computed from exactly the numbers that are published.
        values = {name: round(value, 2) for name, value in values.items() if value is not None}

        # Step 3: publish the sub-metrics, then score them and publish the KPI.
        for name, value in values.items():
            host_obj.with_metric(f"vCommunity|{GROUP}|{name}", value)

        kpi = kpi_score(METRICS, values)
        if kpi is not None:
            host_obj.with_metric(f"vCommunity|{GROUP}|{KPI_NAME}", kpi)

        no_data = [metric.name for metric in METRICS if metric.name not in values]
        if no_data:
            logger.debug(f"ESXi Performance for {host_name}: no data, so left out: {', '.join(no_data)}")

    except Exception as e:
        # A failure here must not stop the collection of the other host data.
        logger.warning(f"Failed to retrieve ESXi Performance metrics for : {host_name} - {repr(e)}")
