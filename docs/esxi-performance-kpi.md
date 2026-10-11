# ESXi Performance KPI

**ESXi Performance** is a single 0-100 % score for an ESXi host. 100 is perfect. It measures actual contention, not potential. It shows how bad the contention is, not why it happens.

It answers two questions about the powered-on VMs on the host:

- **How deep?** The worst VM. Shows a problem that hits one VM hard.
- **How broad?** The 90th percentile across the VMs. Shows a problem that many VMs share. 90 % of the VMs are at or below this value.

All 10 metrics are published on the host object under `vCommunity|ESXi Performance`.

Code: [`Management Pack/app/metrics/host/esxi_performance_metrics.py`](../Management%20Pack/app/metrics/host/esxi_performance_metrics.py)

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

## How each sub-metric is calculated

They are the same sub-metrics as [Cluster Performance](cluster-performance-kpi.md#step-1-collect-the-9-sub-metrics), measured over the VMs of one host instead of a whole cluster. The formulas exist once, in [`metrics/vm_contention.py`](../Management%20Pack/app/metrics/vm_contention.py).

- The 8 VM sub-metrics are the worst value and the 90th percentile of `cpu|20_sec_peak_readyPct`, `cpu|20_sec_peak_costopPct`, `mem|20_sec_peak_host_contentionPct` and `virtualDisk|20_sec_peak_totalLatency_average`, over the powered-on VMs on the host. A VM runs on the host named in its `summary|parentHost` property, and is powered on when `summary|runtime|powerState` is "Powered On", both read from VCF Operations.
- Bad network packets are `(errorsRx + errorsTx + droppedRx + droppedTx) / (packetsRx + packetsTx) × 100` of the host, in the last collection cycle (5 minutes), the same as the "ESXi Bad Network Packets" super metric. It is never averaged over a longer time, because that would hide a spike. Two of its counters, Total Packets Received and Transmitted, are deactivated by default in VCF Operations. Activate them first: see [Required Policy Settings](../README.md#required-policy-settings).

The stats of all VMs and all hosts are read in bulk, once per collection cycle, not once per host.

## Worked examples

- **Nothing wrong.** Bad packets are 0, in their excluded green, so they are left out. The other 8 score 100. KPI = **100**.
- **One VM with 200 ms disk latency.** Worst VM Disk Latency is a quarter of the way through red (160 to 320): 18.75 with weight 8. The 90th percentile stays 0, because one VM is not a broad problem. KPI = `(7 × 100 + 18.75 × 8) / (7 + 8)` ≈ **56.67**.
- **A host with no powered-on VMs.** No VM sub-metric has data. Bad packets are 0 and left out. Nothing is wrong, so the KPI is **100**.

The same examples are checked by the tests in [`Management Pack/tests/test_esxi_performance_metrics.py`](../Management%20Pack/tests/test_esxi_performance_metrics.py).

## Missing data

A sub-metric with no data is not published for that cycle, and it is left out of the KPI. It is never counted as 0. A host that is not connected gets no KPI.
