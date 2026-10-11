# VM Performance KPI

**VM Performance** is a single 0-100 % score for a virtual machine. 100 is perfect. It scores the VM as a virtual motherboard: is ESXi giving it the CPU, memory, disk and network it asks for? It combines 9 sub-metrics, and the worse a sub-metric is, the more it pulls the score down.

What happens inside Windows or Linux is scored separately, by [Guest OS Performance](guest-os-performance-kpi.md).

It is published on every powered-on VM as `vCommunity|VM Performance|VM Performance`. A powered-off VM gets no score.

Code: [`Management Pack/app/metrics/vm/vm_performance_metrics.py`](../Management%20Pack/app/metrics/vm/vm_performance_metrics.py)

Source of the sub-metrics and limits: [`Complex Metrics/Virtual Motherboard Performance metric.png`](Complex%20Metrics/Virtual%20Motherboard%20Performance%20metric.png)

## Step 1: Collect the 9 sub-metrics

Eight sub-metrics are stats the VM already has. They are read as they are, and are not published a second time. Memory Zip Swap is calculated.

| Group | Sub-metric | Source |
| :--- | :--- | :--- |
| VM contention | CPU Co-Stop | `cpu\|20_sec_peak_costopPct` |
| VM contention | CPU Ready | `cpu\|20_sec_peak_readyPct` |
| VM contention | CPU Overlap | `cpu\|20_sec_peak_overlap` |
| VM contention | Memory Contention | `mem\|20_sec_peak_host_contentionPct` |
| VM contention | Disk Latency | `virtualDisk\|20_sec_peak_totalLatency_average` |
| VM contention | Network Dropped Tx | `net\|droppedTxPct_max` |
| VM utilization | CPU Run | `cpu\|net_run` |
| IaaS high utilization | Memory Ballooned | `mem\|balloonPct` |
| IaaS high utilization | Memory Zip Swap | Calculated: `(mem\|compressed_average + mem\|swapped_average) / guest\|used_memory × 100`. Published as `vCommunity\|VM Performance\|Memory Zip Swap`. |

The 20-second peaks are used where they exist, not the 5-minute averages. This makes the KPI a leading indicator.

## Step 2 and 3: Score each sub-metric, then combine

The scoring is the same for every KPI. It is described in [Cluster Performance KPI](cluster-performance-kpi.md#step-2-score-each-sub-metric): four tiers, 25 points per tier, and a weight that doubles with each tier.

## Limits per sub-metric

| Sub-metric | Unit | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CPU Co-Stop | % | 1 | 2 | 4 | 8 |
| CPU Ready | % | 2 | 4 | 8 | 16 |
| CPU Overlap | % | Excluded (below 0.5) | 1 | 2 | 4 |
| Memory Contention | % | 0.5 | 1 | 2 | 4 |
| Disk Latency | ms | 10 | 20 | 40 | 80 |
| Network Dropped Tx | % | Excluded (exactly 0) | 0.5 | 1 | 2 |
| CPU Run | % | Excluded (below 95) | 97 | 99 | 100 |
| Memory Ballooned | % | 2 | 4 | 8 | 16 |
| Memory Zip Swap | % | 0.25 | 0.5 | 1 | 2 |

Every sub-metric is "lower is better", and 0 is perfect.

**Excluded.** Three green ranges are marked "Excluded" in the source table. While a sub-metric is in its excluded green, it is left out of the KPI instead of scoring 100. Once it leaves green, it counts like any other sub-metric.

- **CPU Overlap below 0.5 %.** Some overlap is normal and says nothing about performance.
- **Network Dropped Tx at exactly 0.** Dropped packets are rare. Any dropped packet is yellow.
- **CPU Run below 95 %.** A VM that is not busy says nothing about its performance. Above 95 %, the VM itself is too small.

## Worked examples

- **Nothing wrong.** CPU Overlap, Network Dropped Tx and CPU Run are in their excluded green, so they are left out. The other 6 score 100 with weight 1. KPI = **100**.
- **Same, except CPU Ready = 10** (red tier):
  - CPU Ready is a quarter of the way through red (from 8 to 16), so it scores `25 − (¼ × 25) = 18.75`, with weight 8.
  - KPI = `(5 × 100 + 18.75 × 8) / (5 + 8)` = `650 / 13` = **50.0**.
- **Same as the first, except CPU Run = 98 %** (orange tier):
  - It is halfway through orange (from 97 to 99), so it scores `37.5`, with weight 4.
  - KPI = `(6 × 100 + 37.5 × 4) / (6 + 4)` = `750 / 10` = **75.0**.
- **Same as the first, except 0.25 % dropped packets** (yellow tier):
  - It is halfway through yellow (from 0 to 0.5), so it scores `62.5`, with weight 2.
  - KPI = `(6 × 100 + 62.5 × 2) / (6 + 2)` = `725 / 8` ≈ **90.62**.

The same examples are checked by the tests in [`Management Pack/tests/test_vm_performance_metrics.py`](../Management%20Pack/tests/test_vm_performance_metrics.py).

## Missing data

A sub-metric with no data is left out of the KPI. It is never counted as perfect.

- A VM without VMware Tools has no Memory Zip Swap, because that needs `guest|used_memory`. The KPI of such a VM is built from the other sub-metrics.
- If no sub-metric has data, the KPI is not published.
- A powered-off VM gets no KPI, because its stats are old.

## Changing the KPI

The sub-metrics, their units and their limits are one table, `METRICS`, at the top of the code file.

- To change a limit, edit the row.
- To add a sub-metric that is a VM stat as it is, add a row to `METRICS` and a line to `SOURCE_STATS`.
- To exclude a green range, set the last value of the row to `True`. For a green that is exactly 0, also set the green limit to 0.

The adapter definition reads the same table, so there is nothing else to update.
