# Cluster Performance KPI

**Cluster Performance** is a single 0-100 % score for a vSphere cluster. 100 is perfect. It combines 10 sub-metrics, and the worse a sub-metric is, the more it pulls the score down.

Use it to watch many clusters at once. When the score drops, open the 10 sub-metrics on that cluster to see which one caused it.

All 11 metrics are published on the cluster object under `vCommunity|Cluster Performance`.

Code: [`Management Pack/app/metrics/cluster/cluster_performance_metrics.py`](../Management%20Pack/app/metrics/cluster/cluster_performance_metrics.py)

## Step 1: Collect the 10 sub-metrics

Every sub-metric is "lower is better", and 0 is perfect.

| Sub-metric | What it is | How it is calculated |
| :--- | :--- | :--- |
| CPU Ready | Average across the cluster's VMs | Average of `cpu\|20_sec_peak_readyPct` |
| CPU Co-Stop | Average across the cluster's VMs | Average of `cpu\|20_sec_peak_costopPct` |
| Memory Contention | Average across the cluster's VMs | Average of `mem\|20_sec_peak_host_contentionPct` |
| Worst VM CPU Ready | The worst VM | Highest `cpu\|20_sec_peak_readyPct` |
| Worst VM CPU Co-Stop | The worst VM | Highest `cpu\|20_sec_peak_costopPct` |
| Worst VM Memory Contention | The worst VM | Highest `mem\|20_sec_peak_host_contentionPct` |
| Worst ESXi Bad Network Packets | The worst host | Per host: `(errorsRx + errorsTx + droppedRx + droppedTx) / (packetsRx + packetsTx) × 100`, added up over the last 30 minutes. The sub-metric is the highest host. |
| vMotions per 100 Running VMs | Cluster as a whole | `number_vmotion / number_running_vms × 100`, for the last collection cycle |
| Memory Zip Swap | Cluster as a whole | `(compressed + swapout) / (compressed + swapout + consumed − sysUsage) × 100` |
| Memory Ballooned | Cluster as a whole | `vmmemctl / (vmmemctl + consumed − sysUsage) × 100` |

Notes:

- The VM stats are the 20-second peaks, not the 5-minute averages. This makes the KPI a leading indicator.
- Bad network packets are added up over 30 minutes because one collection cycle is too noisy. A single burst of drops would otherwise push the sub-metric into the red tier.

## Step 2: Score each sub-metric

Each sub-metric has four limits. They split its values into four tiers. Inside a tier, the score drops in a straight line by 25 points.

| Tier | Value range | Score goes from → to | Weight |
| :--- | :--- | :--- | :--- |
| Green | 0 up to the green limit | 100 → 75 | 1 |
| Yellow | green limit up to the yellow limit | 75 → 50 | 2 |
| Orange | yellow limit up to the orange limit | 50 → 25 | 4 |
| Red | orange limit up to the zero-at limit | 25 → 0 | 8 |

Above the zero-at limit the score stays at 0.

## Step 3: Combine

```
KPI = Σ(score × weight) / Σ(weight)
```

- This is a weighted average. The weight of each sub-metric depends on the tier it is in.
- A sub-metric in the red tier counts 8× more than one in the green tier.
- This is deliberate. One bad sub-metric is not hidden by nine good ones.

## Limits per sub-metric

| Sub-metric | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- |
| CPU Ready | 1 | 2 | 4 | 8 |
| CPU Co-Stop | 1 | 2 | 4 | 8 |
| Memory Contention | 0.5 | 1 | 2 | 4 |
| Worst VM CPU Ready | 4 | 8 | 16 | 32 |
| Worst VM CPU Co-Stop | 2 | 4 | 8 | 16 |
| Worst VM Memory Contention | 1 | 2 | 4 | 8 |
| Worst ESXi Bad Network Packets | 0.2 | 0.4 | 0.8 | 1.6 |
| vMotions per 100 Running VMs | 1 | 2 | 4 | 8 |
| Memory Zip Swap | 0.25 | 0.5 | 1 | 2 |
| Memory Ballooned | 1 | 2 | 4 | 8 |

Each limit is double the one before it. The worst-VM rows have higher limits than the cluster-average rows, because a single VM peaks far above the average.

## Worked examples

- **All 10 sub-metrics are 0.** Each scores 100 with weight 1. KPI = **100**.
- **Same, except CPU Ready = 5** (red tier):
  - CPU Ready is a quarter of the way through red (from 4 to 8), so it scores `25 − (¼ × 25) = 18.75`, with weight 8.
  - KPI = `(9 × 100 + 18.75 × 8) / (9 + 8)` = `1050 / 17` ≈ **61.76**.
  - A plain average would give about 91.9. The weighting makes the one bad sub-metric show.

The same examples are checked by the tests in [`Management Pack/tests/test_cluster_performance_metrics.py`](../Management%20Pack/tests/test_cluster_performance_metrics.py) and [`test_kpi_score.py`](../Management%20Pack/tests/test_kpi_score.py).

## Missing data

A sub-metric with no data is not published for that collection cycle, and it is left out of the KPI. It is never counted as 0, because 0 means "perfect" and would make the cluster look healthier than it is.

- The adapter log lists the sub-metrics that were left out, per cluster.
- If no sub-metric has data, the KPI itself is not published.

Common reasons for no data: the cluster has no running VMs, the vCenter adapter has not yet collected the source stat, or the stats request to VCF Operations failed.

## Changing the KPI

The sub-metrics, their units and their limits are one table, `METRICS`, at the top of the code file. Each row starts with the value where the score is 100, which is 0 for every sub-metric here.

The tiers and weights are a second table, `TIERS`, in [`Management Pack/app/metrics/kpi_score.py`](../Management%20Pack/app/metrics/kpi_score.py). That file holds the scoring for every KPI, so a change there also changes [VM Performance](vm-performance-kpi.md).

- To change a limit, edit the row.
- To remove a sub-metric, delete its row and the line that supplies its value.
- To add one, add a row and one line in `collect_cluster_performance_metrics()` that supplies its value.

The adapter definition reads the same table, so there is nothing else to update.
