# Cluster Risk KPI

> **Status: planned.** The sub-metrics and limits below are final. The code that collects them is not written yet, so VCF Operations does not show this KPI.

**Cluster Risk** is a single 0-100 % score for a vSphere cluster. 100 means no risk. It is a leading indicator: it warns before the VMs feel contention. It covers both capacity and performance.

- [Cluster Performance](cluster-performance-kpi.md) shows contention that is happening now.
- Cluster Risk shows how close the cluster is to it.

Most sub-metrics take the highest or worst ESXi host in the cluster. One full host can hurt its VMs while the cluster average still looks fine.

Code (stub): [`Management Pack/app/metrics/cluster/cluster_risk_metrics.py`](../Management%20Pack/app/metrics/cluster/cluster_risk_metrics.py)

Source of the limits: [`Complex Metrics/vSphere Cluster Risk metric.png`](Complex%20Metrics/vSphere%20Cluster%20Risk%20metric.png)

## The 12 sub-metrics

Every sub-metric is "lower is better".

| Group | Sub-metric | Unit | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Utilization | Highest ESXi CPU Thread Utilization | % | Excluded (below 60) | 80 | 90 | 95 |
| Utilization | Worst ESXi CPU Imbalance | ratio | 1 (exactly) | 1.25 | 2 | 2.75 * |
| Utilization | Highest ESXi Memory Consumed | % | Excluded (below 80) | 90 | 95 | 100 |
| Saturation | Worst ESXi Memory Ballooned | % | 1 | 2 | 4 | 8 |
| Saturation | Worst ESXi Memory Zip Swap (swapped + compressed) | % | 0.25 | 0.5 | 1 | 2 |
| Saturation | Worst ESXi Memory Tiering Latency | µs | 150 | 300 | 450 | 600 |
| Reservation | Highest ESXi CPU Reservation | % | Excluded (below 10) | 40 | 60 | 80 |
| Reservation | Highest ESXi Memory Reservation | % | Excluded (below 10) | 40 | 60 | 80 |
| Allocation | Highest ESXi CPU Overcommit Ratio | ratio | Excluded (below 1) | 2 | 3 | 4 |
| Allocation | Highest ESXi Memory Overcommit Ratio | ratio | Excluded (below 1) | 1.4 | 1.8 | 2.2 |
| Monster VM | Highest CPU Monster VM to Host Ratio | ratio | 1 | 2 | 3 | 4 |
| Monster VM | Highest Memory Monster VM to Host Ratio | ratio | 1 | 2 | 3 | 4 |

The score is 100 at 0 for every row, except CPU Imbalance, where it is 100 at 1 (a perfectly even load).

**CPU Imbalance:** green is exactly 1, as in the source table. Any imbalance is yellow.

\* **Assumed limit.** The source table gives red for CPU Imbalance as "2" only, so where red ends is not given. It is set to 2.75, so red is as wide as orange. Confirm or change this value before the KPI is built.

**Excluded.** Six green ranges are marked "Excluded" in the source table: CPU Thread Utilization, Memory Consumed, CPU and Memory Reservation, and CPU and Memory Overcommit. A host that is not busy, has little reserved or is not overcommitted says nothing about risk. So while they are green, these sub-metrics are left out of the KPI instead of scoring 100. They count once they leave green.

## How the score is calculated

The same way as every KPI:

1. Each sub-metric value gets a score from 100 to 0, depending on the tier it is in.
2. The KPI is the weighted average of the scores. A sub-metric in the red tier weighs 8×, orange 4×, yellow 2×, green 1×.

The full explanation, with a worked example, is in [Cluster Performance KPI](cluster-performance-kpi.md#step-2-score-each-sub-metric). The code is [`kpi_score.py`](../Management%20Pack/app/metrics/kpi_score.py).

## Still to do

- Decide which VCF Operations stat each sub-metric is read from, and write the formulas.
- Call the entry point from the cluster collector.
- Declare the KPI in `adapter.py` with `define_kpi()`.
- Add a test file with worked examples.
- Add the published metrics to the [Metrics & Properties Reference](metrics-reference.md).
