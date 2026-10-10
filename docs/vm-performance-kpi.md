# VM Performance KPI

**VM Performance** is a single 0-100 % score for a virtual machine. 100 is perfect. It combines 14 sub-metrics, and the worse a sub-metric is, the more it pulls the score down.

Use it to watch many VMs at once. When the score drops, open the sub-metrics on that VM to see which one caused it.

It is published on every powered-on VM as `vCommunity|VM Performance|VM Performance`. A powered-off VM gets no score.

Code: [`Management Pack/app/metrics/vm/vm_performance_metrics.py`](../Management%20Pack/app/metrics/vm/vm_performance_metrics.py)

## Step 1: Collect the 14 sub-metrics

Twelve sub-metrics are stats the VM already has. They are read as they are, and are not published a second time. Two are calculated.

| Sub-metric | Source |
| :--- | :--- |
| CPU Ready | `cpu\|20_sec_peak_readyPct` |
| CPU Co-Stop | `cpu\|20_sec_peak_costopPct` |
| CPU IO Wait | `cpu\|20_sec_peak_iowaitPct` |
| CPU Overlap | `cpu\|20_sec_peak_overlap` |
| CPU Run | `cpu\|net_run` |
| Guest CPU Queue | `guest\|20_sec_peak_cpu_queue` |
| Memory Contention | `mem\|20_sec_peak_host_contentionPct` |
| Memory Ballooned | `mem\|balloonPct` |
| Memory Zip Swap | Calculated: `(mem\|compressed_average + mem\|swapped_average) / guest\|used_memory × 100`. Published as `vCommunity\|VM Performance\|Memory Zip Swap`. |
| Guest Page-Out Rate | `guest\|page.outRate_latest` |
| Guest Free Memory | Calculated: `guest\|mem.free_latest / 1024`, which converts KB to MB |
| Disk Latency | `virtualDisk\|20_sec_peak_totalLatency_average` |
| Guest Disk Queue | `guest\|20_sec_peak_disk_queue` |
| Network Dropped Tx | `net\|droppedTxPct_max` |

The 20-second peaks are used where they exist, not the 5-minute averages. This makes the KPI a leading indicator.

## Step 2 and 3: Score each sub-metric, then combine

The scoring is the same for every KPI. It is described in [Cluster Performance KPI](cluster-performance-kpi.md#step-2-score-each-sub-metric): four tiers, 25 points per tier, and a weight that doubles with each tier.

## Limits per sub-metric

| Sub-metric | Score is 100 at | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CPU Ready | 0 | 2 | 4 | 8 | 16 |
| CPU Co-Stop | 0 | 1 | 2 | 4 | 8 |
| CPU IO Wait | 0 | 1 | 2 | 4 | 8 |
| CPU Overlap | 0 | 0.5 | 1 | 2 | 4 |
| CPU Run | 60 | 80 | 90 | 95 | 100 |
| Guest CPU Queue | 0 | 1 | 2 | 4 | 8 |
| Memory Contention | 0 | 0.5 | 1 | 2 | 4 |
| Memory Ballooned | 0 | 2 | 4 | 8 | 16 |
| Memory Zip Swap | 0 | 0.5 | 1 | 2 | 4 |
| Guest Page-Out Rate | 0 | 1000 | 2000 | 4000 | 8000 |
| Guest Free Memory (MB) | 1024 | 512 | 256 | 128 | 0 |
| Disk Latency | 0 | 20 | 40 | 80 | 160 |
| Guest Disk Queue | 0 | 20 | 40 | 80 | 160 |
| Network Dropped Tx | 0 | 0.25 | 0.5 | 1 | 2 |

Two rows are different from the rest:

- **Guest Free Memory** is "higher is better", so its limits go down. 1 GB or more of free memory scores 100.
- **CPU Run** only starts to count above 60 %. A VM that runs at 60 % or less scores 100 on this sub-metric.

## Worked examples

- **All 14 sub-metrics are at their best.** Each scores 100 with weight 1. KPI = **100**.
- **Same, except CPU Ready = 10** (red tier):
  - CPU Ready is a quarter of the way through red (from 8 to 16), so it scores `25 − (¼ × 25) = 18.75`, with weight 8.
  - KPI = `(13 × 100 + 18.75 × 8) / (13 + 8)` = `1450 / 21` ≈ **69.05**.
- **Same, except Guest Free Memory = 192 MB** (orange tier):
  - It is halfway through orange (from 256 down to 128), so it scores `37.5`, with weight 4.
  - KPI = `(13 × 100 + 37.5 × 4) / (13 + 4)` = `1450 / 17` ≈ **85.29**.

The same examples are checked by the tests in [`Management Pack/tests/test_vm_performance_metrics.py`](../Management%20Pack/tests/test_vm_performance_metrics.py).

## Missing data

A sub-metric with no data is left out of the KPI. It is never counted as perfect.

- A VM without VMware Tools has no guest stats. Five sub-metrics need them: Guest CPU Queue, Guest Disk Queue, Guest Page-Out Rate, Guest Free Memory and Memory Zip Swap. The KPI of such a VM is built from the other nine.
- If no sub-metric has data, the KPI is not published.

This is different from the "VM Performance" super metric that this KPI replaces. The super metric returned no value at all when one input was missing.

## Changing the KPI

The sub-metrics and their limits are one table, `METRICS`, at the top of the code file.

- To change a limit, edit the row.
- To add a sub-metric that is read from a VM stat as it is, add a row to `METRICS` and a line to `SOURCE_STATS`.
- To remove one, delete the row and its line in `SOURCE_STATS`.
