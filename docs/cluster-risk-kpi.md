# Cluster Risk KPI

**Cluster Risk** is a single 0-100 % score for a vSphere cluster. 100 means no risk. It is a leading indicator: it warns before the VMs feel contention. It covers both capacity and performance.

- [Cluster Performance](cluster-performance-kpi.md) shows contention that is happening now.
- Cluster Risk shows how close the cluster is to it.

Every sub-metric takes the highest or worst ESXi host in the cluster. One full host can hurt its VMs while the cluster average still looks fine.

All 13 metrics are published on the cluster object under `vCommunity|Cluster Risk`.

Code: [`Management Pack/app/metrics/cluster/cluster_risk_metrics.py`](../Management%20Pack/app/metrics/cluster/cluster_risk_metrics.py)

Source of the limits: [`Complex Metrics/vSphere Cluster Risk metric.png`](Complex%20Metrics/vSphere%20Cluster%20Risk%20metric.png)

## The 12 sub-metrics and their limits

Every sub-metric is "lower is better".

| Group | Sub-metric | Unit | Green ends at | Yellow ends at | Orange ends at | Score hits 0 at |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Utilization | Highest ESXi CPU Thread Utilization | % | Excluded (below 60) | 80 | 90 | 95 |
| Utilization | Worst ESXi CPU Imbalance | ratio | 1 (exactly) | 1.3 | 1.6 | 2 |
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

The score is 100 at 0 for every row, except CPU Imbalance, where it is 100 at 1 (a perfectly even load). Any imbalance is yellow.

**Excluded.** Six green ranges are marked "Excluded" in the source table. A host that is not busy, has little reserved or is not overcommitted says nothing about risk. So while they are green, these sub-metrics are left out of the KPI instead of scoring 100. They count once they leave green.

## How each sub-metric is calculated

Each sub-metric is calculated per host, then the highest host is kept. CPU Imbalance is the one exception: it compares hosts.

| Sub-metric | Per host | Source |
| :--- | :--- | :--- |
| CPU Thread Utilization | `cpu.utilization`: the share of the host's CPU threads in use, hyper-threading aware | VCF Operations: `cpu\|utilization_average` |
| CPU Imbalance | The busiest host's CPU thread utilization, divided by the average of all hosts in the cluster | VCF Operations: `cpu\|utilization_average` |
| Memory Consumed | Consumed memory, as a share of host memory | VCF Operations: `mem\|consumed_average` / `mem\|totalCapacity_average` |
| Memory Ballooned | Ballooned memory, as a share of host memory | VCF Operations: `mem\|vmmemctl_average` / `mem\|totalCapacity_average` |
| Memory Zip Swap | Compressed plus swapped memory, as a share of host memory | VCF Operations: (`mem\|compressed_average` + `mem\|swapused_average`) / `mem\|totalCapacity_average` |
| Memory Tiering Latency | Not available yet: no source stat. Always left out. | — |
| CPU Reservation | Reserved CPU, as a share of host CPU capacity | VCF Operations: `cpu\|reservedCapacity_average` / `cpu\|totalCapacity_average` |
| Memory Reservation | Reserved memory, as a share of host memory | VCF Operations: `mem\|reservedCapacity_average` / `mem\|totalCapacity_average` |
| CPU Overcommit Ratio | vCPUs of the powered-on VMs, per physical core | vCenter: VM `config.hardware.numCPU`, host `hardware.cpuInfo.numCpuCores` |
| Memory Overcommit Ratio | Configured memory of the powered-on VMs, per MB of host memory, memory tier included | vCenter: VM `config.hardware.memoryMB`, host `hardware.memorySize` |
| CPU Monster VM to Host Ratio | vCPUs of the largest powered-on VM, against the monster size of its host (see below) | vCenter: VM `config.hardware.numCPU`, host `hardware.cpuInfo.numCpuCores` |
| Memory Monster VM to Host Ratio | Memory of the largest powered-on VM, against the monster size of its host (see below) | vCenter: VM `config.hardware.memoryMB`, host `hardware.memoryTierInfo` (DRAM tiers), or `hardware.memorySize` without memory tiering |

### When a VM is a monster

The Monster VM ratios compare the largest VM with the size at which a VM becomes a monster on its host. 1 means the largest VM is exactly that size. Above 1 it is a monster.

| | A VM is a monster when it has | Example |
| :--- | :--- | :--- |
| CPU | More than 50 % of the host's physical cores. Cores, not threads. | A host with 64 cores and 128 threads: more than 32 vCPU. |
| Memory | More than 40 % of the host's DIMM memory, or 256 GB, whichever is smaller. A memory tier such as NVMe does not count. | A host with 768 GB of DIMM and 768 GB of NVMe: 40 % is 307 GB, so 256 GB. |

## How the score is calculated

The same way as every KPI:

1. Each sub-metric value gets a score from 100 to 0, depending on the tier it is in.
2. The KPI is the weighted average of the scores. A sub-metric in the red tier weighs 8×, orange 4×, yellow 2×, green 1×.

The full explanation, with a worked example, is in [Cluster Performance KPI](cluster-performance-kpi.md#step-2-score-each-sub-metric). The code is [`kpi_score.py`](../Management%20Pack/app/metrics/kpi_score.py).

## Worked examples

Two hosts, each with 32 cores and 512 GB. Each runs four VMs of 4 vCPU and 16 GB. The monster size of these hosts is 16 vCPU (half of 32 cores) and 204.8 GB (40 % of 512 GB, less than 256 GB).

- **Healthy.** Both hosts at 40 % CPU and 50 % memory consumed, nothing ballooned, swapped or reserved.
  - Left out: the six rows in their excluded green, and Memory Tiering Latency (no data).
  - Counted: CPU Imbalance 1 (100), Ballooned 0 (100), Zip Swap 0 (100), CPU Monster VM `4 / 16` = 0.25 (93.75), Memory Monster VM `16 / 204.8` = 0.08 (98).
  - KPI = `(100 + 100 + 100 + 93.75 + 98) / 5` = **98.35**.
- **One busy host.** Host 1 at 90 % CPU, host 2 at 30 %.
  - CPU Thread Utilization 90 leaves its excluded green. It is at the start of red: 25 with weight 8.
  - CPU Imbalance is `90 / 60` = 1.5, in orange: 33.33 with weight 4.
  - KPI = `(25 × 8 + 33.33 × 4 + 100 + 100 + 93.75 + 98) / (8 + 4 + 4)` = **45.32**.

The same examples are checked by the tests in [`Management Pack/tests/test_cluster_risk_metrics.py`](../Management%20Pack/tests/test_cluster_risk_metrics.py).

## Missing data

A sub-metric with no data is not published for that cycle, and it is left out of the KPI. It is never counted as 0, because 0 means "no risk".

- If the stats request to VCF Operations fails, only the vCenter-based rows (Overcommit and Monster VM) are scored.
- A host that VCF Operations does not know is left out.

## To verify on a live system

- **CPU Thread Utilization** reads `cpu|utilization_average`, the VCF Operations key expected for vCenter's `cpu.utilization`. Confirm the key on your hosts.
- **Memory stat keys:** `mem|totalCapacity_average`, `mem|swapused_average` and the two `reservedCapacity_average` keys are the expected names. Confirm they exist on your hosts.
- **Memory Tiering Latency** needs its stat key. Set `MEM_TIERING_LATENCY` in the code once it is known.
- **Overcommit and Monster VM** count powered-on VMs only.
- **Memory tiering** is read from `hardware.memoryTierInfo`, which needs vCenter 8.0 Update 3 or later. On an older vCenter, all host memory counts as DIMM.
