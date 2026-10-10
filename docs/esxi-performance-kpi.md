# ESXi Performance KPI

> **Status: planned.** The sub-metrics and limits below are final. The code that collects them is not written yet, so VCF Operations does not show this KPI.

**ESXi Performance** is a single 0-100 % score for an ESXi host. 100 is perfect. It measures actual contention, not potential. It shows how bad the contention is, not why it happens.

It answers two questions about the VMs on the host:

- **How deep?** The worst VM. Shows a problem that hits one VM hard.
- **How broad?** The 90th percentile across the VMs. Shows a problem that many VMs share. 90 % of the VMs are at or below this value.

Code (stub): [`Management Pack/app/metrics/host/esxi_performance_metrics.py`](../Management%20Pack/app/metrics/host/esxi_performance_metrics.py)

Source of the limits: [`Complex Metrics/vSphere ESXi Performance metric.png`](Complex%20Metrics/vSphere%20ESXi%20Performance%20metric.png)

## The 9 sub-metrics

Every sub-metric is "lower is better", and 0 is perfect. The VM stats are the 20-second peaks.

| Group | Sub-metric | Unit | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| How deep? | Worst VM CPU Ready | % | 4 | 8 | 16 | 32 |
| How deep? | Worst VM CPU Co-Stop | % | 2 | 4 | 8 | 16 |
| How deep? | Worst VM Memory Latency | % | 1 | 2 | 4 | 8 |
| How deep? | Worst VM Disk Latency (read/write, any virtual disk) | ms | 40 | 80 | 160 | 320 |
| How broad? | 90th Percentile VM CPU Ready | % | 1 | 2 | 4 | 8 |
| How broad? | 90th Percentile VM CPU Co-Stop | % | 0.5 | 1 | 2 | 4 |
| How broad? | 90th Percentile VM Memory Latency | % | 0.5 | 1 | 2 | 4 |
| How broad? | 90th Percentile VM Disk Latency (read/write) | ms | 20 | 40 | 60 | 80 |
| ESXi | ESXi Bad Network Packets (errored + dropped) | % | Excluded (exactly 0) | 0.2 | 0.4 | 0.8 |

**Bad network packets:** green is exactly 0, and marked "Excluded" in the source table. Any bad packet is yellow. While it is 0 the sub-metric is skipped (left out of the KPI), because the problem is rare and would otherwise add a free 100.

## How the score is calculated

The same way as every KPI:

1. Each sub-metric value gets a score from 100 to 0, depending on the tier it is in.
2. The KPI is the weighted average of the scores. A sub-metric in the red tier weighs 8×, orange 4×, yellow 2×, green 1×.

The full explanation, with a worked example, is in [Cluster Performance KPI](cluster-performance-kpi.md#step-2-score-each-sub-metric). The code is [`kpi_score.py`](../Management%20Pack/app/metrics/kpi_score.py).

## Same sub-metrics as Cluster Performance

[Cluster Performance](cluster-performance-kpi.md) has the same 9 sub-metrics, measured across the cluster instead of one host. ESXi Performance can reuse its code that reads the VM stats and calculates the worst VM and the 90th percentile.

## Still to do

- Decide which VCF Operations stat each sub-metric is read from, and write the formulas, including the 90th percentile.
- Call the entry point from the host collector.
- Declare the KPI in `adapter.py` with `define_kpi()`.
- Add a test file with worked examples.
- Add the published metrics to the [Metrics & Properties Reference](metrics-reference.md).
