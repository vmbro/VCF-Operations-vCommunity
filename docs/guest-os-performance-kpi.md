# Guest OS Performance KPI

**Guest OS Performance** is a single 0-100 % score for the operating system inside a VM, Windows or Linux. 100 is perfect. It answers: is the guest OS getting the CPU, disk and memory it needs? It combines 4 sub-metrics.

[VM Performance](vm-performance-kpi.md) scores the virtual motherboard. This KPI scores what runs on it.

It is published on every powered-on VM with VMware Tools as `vCommunity|Guest OS Performance|Guest OS Performance`.

Code: [`Management Pack/app/metrics/vm/guest_os_performance_metrics.py`](../Management%20Pack/app/metrics/vm/guest_os_performance_metrics.py)

Source of the sub-metrics and limits: [`Complex Metrics/Guest OS Performance metric.png`](Complex%20Metrics/Guest%20OS%20Performance%20metric.png)

## The 4 sub-metrics

All four come from VMware Tools. They are stats the VM already has, or a simple conversion of one, so only the KPI is published.

| Group | Sub-metric | Source | Unit | Score is 100 at | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Guest OS contention | Guest CPU Run Queue per vCPU | `guest\|20_sec_peak_cpu_queue` | threads | 0 | 2 | 4 | 8 | 16 |
| Guest OS contention | Guest Disk Queue | `guest\|20_sec_peak_disk_queue` | IOs | 0 | 20 | 40 | 80 | 160 |
| Guest OS utilization | Guest Free Memory | `guest\|mem.free_latest / 1024` (KB to MB) | MB | 1024 | 512 | 256 | 128 | 0 |
| Guest OS utilization | Guest Page-Out Rate | `guest\|page.outRate_latest` | pages/s | 0 | 1000 | 2000 | 4000 | 8000 |

- Guest Free Memory is "higher is better", so its limits go down. 1 GB or more free scores 100.
- The CPU run queue stat is already per vCPU, so it is used as it is.

## How the score is calculated

The same way as every KPI: each sub-metric gets a score from 100 to 0 by tier, and the KPI is the weighted average, with weights 1, 2, 4 and 8 for green, yellow, orange and red. See [Cluster Performance KPI](cluster-performance-kpi.md#step-2-score-each-sub-metric).

## Worked examples

- **Nothing wrong.** All 4 score 100. KPI = **100**.
- **CPU run queue of 3 per vCPU.** Halfway through yellow (2 to 4): 62.5 with weight 2. KPI = `(3 × 100 + 62.5 × 2) / (3 + 2)` = **85.0**.
- **192 MB free memory.** Halfway through orange (256 down to 128): 37.5 with weight 4. KPI = `(3 × 100 + 37.5 × 4) / (3 + 4)` ≈ **64.29**.

The same examples are checked by the tests in [`Management Pack/tests/test_guest_os_performance_metrics.py`](../Management%20Pack/tests/test_guest_os_performance_metrics.py).

## Missing data

- A VM without VMware Tools has none of the 4 stats, so it gets no Guest OS Performance KPI.
- A sub-metric with no data is left out of the KPI. It is never counted as perfect.
- A powered-off VM gets no KPI.
