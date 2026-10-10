#  Copyright 2026 VCF Operations vCommunity Management Pack
"""ESXi Performance KPI. STUB: the table is final, the collection is not written yet.

What it is
----------
One 0-100 % score per ESXi host. 100 is perfect. It answers one question:
are the VMs on this host getting the CPU, memory, disk and network they ask for?
It measures actual contention, not potential. It shows how bad the contention
is, not why it happens. It is built from the 9 sub-metrics in METRICS below.

The sub-metrics answer two questions:
    How deep?   The worst VM on the host. Shows a problem that hits one VM hard.
    How broad?  The 90th percentile across the VMs on the host. Shows a problem
                that many VMs share. 90 % of the VMs are at or below this value.

Status
------
METRICS holds the limits from docs/Complex Metrics/vSphere ESXi Performance metric.png.
Not written yet:
    - reading the VM and host stats, and the sub-metric formulas
    - the call from collectors/host/collectHostData.py
    - the line define_kpi(vCommunity, esxi_performance_metrics) in adapter.py
Until then the entry point publishes nothing, and VCF Operations does not show this KPI.

Scoring: the same as every KPI, see metrics/kpi_score.py.
Overall approach for all KPIs: metrics/README.md
Description for people who do not read code: docs/esxi-performance-kpi.md
"""
import logging
from metrics.kpi_score import Metric

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
    # Errored and dropped packets as a share of all packets.
    # Green (exactly 0) is "Excluded" in the source table: skipped while 0, because it is rare. Any bad packet is yellow.
    Metric("ESXi Bad Network Packets",                "%",   0.0,  0.0,   0.2,    0.4,    0.8,    True),
]

# Every sub-metric will be published on the host, because none of them exists there as a stat already.
PUBLISHED_METRICS = METRICS


# ---------------------------------------------------------------------------
# Entry point, called once per ESXi host. STUB.
# ---------------------------------------------------------------------------

def collect_esxi_performance_metrics(host_obj, host_name: str) -> None:
    """Not written yet. Publishes nothing. The arguments will change when the collection is written."""
    logger.debug(f"ESXi Performance for {host_name}: not implemented yet, nothing published")
