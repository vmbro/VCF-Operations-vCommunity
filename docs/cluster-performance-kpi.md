# Cluster Performance KPI

**Cluster Performance** is a single 0-100 % score for a vSphere cluster. 100 is perfect. It measures actual contention, not potential. It combines 9 sub-metrics, and the worse a sub-metric is, the more it pulls the score down.

Use it to watch many clusters at once. When the score drops, open the 9 sub-metrics on that cluster to see which one caused it.

All 10 metrics are published on the cluster object under `vCommunity|Cluster Performance`. The KPI itself is `vCommunity|Cluster Performance|Cluster Performance Score`.

Code: [`Management Pack/app/metrics/cluster/cluster_performance_metrics.py`](../Management%20Pack/app/metrics/cluster/cluster_performance_metrics.py)

Source of the sub-metrics and limits: [`Complex Metrics/vSphere Cluster Performance metric.png`](Complex%20Metrics/vSphere%20Cluster%20Performance%20metric.png)

## Step 1: Collect the 9 sub-metrics

The sub-metrics answer two questions about the powered-on VMs in the cluster:

- **How deep?** The worst VM. Shows a problem that hits one VM hard.
- **How broad?** The 90th percentile across the VMs. Shows a problem that many VMs share.

Every sub-metric is "lower is better", and 0 is perfect.

| Group | Sub-metric | How it is calculated |
| :--- | :--- | :--- |
| How deep? | Worst VM CPU Ready | Highest `cpu\|20_sec_peak_readyPct` of any VM |
| How deep? | Worst VM CPU Co-Stop | Highest `cpu\|20_sec_peak_costopPct` of any VM |
| How deep? | Worst VM Memory Latency | Highest `mem\|20_sec_peak_host_contentionPct` of any VM |
| How deep? | Worst VM Disk Latency | Highest `virtualDisk\|20_sec_peak_totalLatency_average` of any VM |
| How broad? | 90th Percentile VM CPU Ready | 90th percentile of `cpu\|20_sec_peak_readyPct` across the VMs |
| How broad? | 90th Percentile VM CPU Co-Stop | 90th percentile of `cpu\|20_sec_peak_costopPct` across the VMs |
| How broad? | 90th Percentile VM Memory Latency | 90th percentile of `mem\|20_sec_peak_host_contentionPct` across the VMs |
| How broad? | 90th Percentile VM Disk Latency | 90th percentile of `virtualDisk\|20_sec_peak_totalLatency_average` across the VMs |
| ESXi | Highest ESXi Bad Network Packets | Per host: `(errorsRx + errorsTx + droppedRx + droppedTx) / (packetsRx + packetsTx) × 100`, in the last collection cycle (5 minutes). The sub-metric is the highest host. |

Notes:

- **Which VMs count.** The powered-on VMs on the cluster's ESXi hosts. A powered-off VM is left out, because its last stats are old. All of this is read from VCF Operations properties: a host belongs to the cluster named in its `summary|parentCluster`, a VM runs on the host named in its `summary|parentHost`, and it is powered on when `summary|runtime|powerState` is "Powered On". Placement is by name, so do not mix datacenters in one adapter instance.
- **20-second peaks.** The VM stats are the 20-second peaks, not the 5-minute averages. This makes the KPI a leading indicator.
- **90th percentile.** The value that 90 % of the VMs are at or below. The VMs are sorted, and the one at position 90 % of the count, rounded up, is taken. With 20 VMs that is the 18th lowest. With fewer than 10 VMs it is the highest, the same as the worst VM.
- **Bad network packets** use the last collection cycle (5 minutes), the same as the former "Bad Network Packets" super metric, which this metric replaces. They are never averaged or added up over a longer time, because that would hide a spike. Two of its counters, Total Packets Received and Transmitted, are deactivated by default in VCF Operations. Activate them first: see [Required Policy Settings](../README.md#required-policy-settings).

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
- This is deliberate. One bad sub-metric is not hidden by eight good ones.

## Limits per sub-metric

| Sub-metric | Unit | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Worst VM CPU Ready | % | 4 | 8 | 16 | 32 |
| Worst VM CPU Co-Stop | % | 2 | 4 | 8 | 16 |
| Worst VM Memory Latency | % | 1 | 2 | 4 | 8 |
| Worst VM Disk Latency | ms | 40 | 80 | 160 | 320 |
| 90th Percentile VM CPU Ready | % | 1 | 2 | 4 | 8 |
| 90th Percentile VM CPU Co-Stop | % | 0.5 | 1 | 2 | 4 |
| 90th Percentile VM Memory Latency | % | 0.5 | 1 | 2 | 4 |
| 90th Percentile VM Disk Latency | ms | 20 | 40 | 60 | 80 |
| Highest ESXi Bad Network Packets | % | Excluded (exactly 0) | 0.2 | 0.4 | 0.8 |

The worst-VM rows have higher limits than the 90th-percentile rows, because a single VM peaks far above most of the others.


**Excluded.** The green range (exactly 0) of bad network packets is marked "Excluded" in the source table. Bad packets are rare. While they are 0, the sub-metric is left out of the KPI, so it does not add a free 100 that would hide the others. Any bad packet is yellow (green is exactly 0), and then it counts.

## Worked examples

- **All 9 sub-metrics are 0.** Bad network packets are skipped. The other 8 score 100 with weight 1. KPI = **100**.
- **Same, except 90th Percentile VM CPU Ready = 5** (red tier):
  - It is a quarter of the way through red (from 4 to 8), so it scores `25 − (¼ × 25) = 18.75`, with weight 8.
  - Bad network packets are 0, so they are skipped. The other 7 score 100 with weight 1.
  - KPI = `(7 × 100 + 18.75 × 8) / (7 + 8)` = `850 / 15` ≈ **56.67**.
  - A plain average would give about 89.8. The weighting makes the one bad sub-metric show.
- **Same as the first example, except a tiny share of bad packets (0.005 %).** It is yellow, scores about 74.4 with weight 2, and now counts. KPI ≈ **94.88**.
- **One VM has 200 ms disk latency, the others 0.** Worst VM Disk Latency is 200 (orange to red). The 90th percentile stays 0, because one VM is not a broad problem.

The same examples are checked by the tests in [`Management Pack/tests/test_cluster_performance_metrics.py`](../Management%20Pack/tests/test_cluster_performance_metrics.py).

## Missing data

A sub-metric with no data is not published for that collection cycle, and it is left out of the KPI. It is never counted as 0, because 0 means "perfect" and would make the cluster look healthier than it is.

- The adapter log lists the sub-metrics that were left out, per cluster.
- If no sub-metric has data, the KPI itself is not published.

Common reasons for no data: the cluster has no powered-on VMs, the vCenter adapter has not yet collected the source stat, or the stats request to VCF Operations failed.

## Related KPIs

- [ESXi Performance](esxi-performance-kpi.md) uses the same 9 sub-metrics, for the VMs on one host.
- [Cluster Risk](cluster-risk-kpi.md) is the leading indicator: how close the cluster is to contention. Memory ballooning and swapping are scored there.

## Changing the KPI

The sub-metrics, their units and their limits are one table, `METRICS`, at the top of the code file.

The tiers and weights are a second table, `TIERS`, in [`Management Pack/app/metrics/kpi_score.py`](../Management%20Pack/app/metrics/kpi_score.py). That file holds the scoring for every KPI, so a change there changes all of them.

- To change a limit, edit the row.
- To add a VM stat, add a line to `VM_STATS` and its two rows (worst VM and 90th percentile) to `METRICS`.

The adapter definition reads the same table, so there is nothing else to update.
