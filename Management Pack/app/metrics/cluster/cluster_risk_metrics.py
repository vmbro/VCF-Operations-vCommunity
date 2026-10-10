#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Cluster Risk KPI. STUB: the table is final, the collection is not written yet.

What it is
----------
One 0-100 % score per vSphere cluster. 100 is no risk. It is a leading
indicator: it warns before the VMs feel contention. It covers both capacity
and performance. It is built from the 12 sub-metrics in METRICS below.

Cluster Performance shows contention that is happening now. Cluster Risk shows
how close the cluster is to it. Most sub-metrics take the highest or worst ESXi
host, because one full host can hurt its VMs while the cluster average looks fine.

Status
------
METRICS holds the limits from docs/Complex Metrics/vSphere Cluster Risk metric.png.
Not written yet:
    - reading the host and VM stats, and the sub-metric formulas
    - the call from collectors/cluster/collectClusterData.py
    - the line define_kpi(vCommunity, cluster_risk_metrics) in adapter.py
Until then the entry point publishes nothing, and VCF Operations does not show this KPI.

Scoring: the same as every KPI, see metrics/kpi_score.py.
Overall approach for all KPIs: metrics/README.md
Description for people who do not read code: docs/cluster-risk-kpi.md
"""
import logging
from metrics.kpi_score import Metric

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
    # Ratio between the busiest and the least busy host. 1 means the load is spread evenly.
    # Green is exactly 1, as in the source table: any imbalance is yellow. The source table gives red as
    # "2" only, so where red ends is an assumption: 2.75, as wide as orange.
    Metric("Worst ESXi CPU Imbalance",                None,  1.0,  1.0,   1.25,   2.0,    2.75),
    Metric("Highest ESXi Memory Consumed",            "%",   0.0,  80.0,  90.0,   95.0,   100.0,  True),

    # --- Saturation: the host is already reclaiming memory from its VMs ---
    Metric("Worst ESXi Memory Ballooned",             "%",   0.0,  1.0,   2.0,    4.0,    8.0),
    Metric("Worst ESXi Memory Zip Swap",              "%",   0.0,  0.25,  0.5,    1.0,    2.0),
    Metric("Worst ESXi Memory Tiering Latency",       "µs",  0.0,  150.0, 300.0,  450.0,  600.0),

    # --- Reservation: capacity that is promised to VMs, even when they do not use it ---
    Metric("Highest ESXi CPU Reservation",            "%",   0.0,  30.0,  60.0,   80.0,   90.0),
    Metric("Highest ESXi Memory Reservation",         "%",   0.0,  30.0,  60.0,   80.0,   90.0),

    # --- Allocation: configured vCPU and vRAM against what the host has ---
    Metric("Highest ESXi CPU Overcommit Ratio",       None,  0.0,  1.0,   2.0,    3.0,    4.0),
    Metric("Highest ESXi Memory Overcommit Ratio",    None,  0.0,  1.0,   1.4,    1.8,    2.2),

    # --- Monster VM: the largest VM against the size of a host ---
    Metric("Highest CPU Monster VM to Host Ratio",    None,  0.0,  1.0,   2.0,    3.0,    4.0),
    Metric("Highest Memory Monster VM to Host Ratio", None,  0.0,  1.0,   2.0,    3.0,    4.0),
]

# Every sub-metric will be published on the cluster, because none of them exists there as a stat already.
PUBLISHED_METRICS = METRICS


# ---------------------------------------------------------------------------
# Entry point, called once per cluster. STUB.
# ---------------------------------------------------------------------------

def collect_cluster_risk_metrics(cluster_obj, cluster_name: str) -> None:
    """Not written yet. Publishes nothing. The arguments will change when the collection is written."""
    logger.debug(f"Cluster Risk for {cluster_name}: not implemented yet, nothing published")
