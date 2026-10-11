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

The score is 100 at 0 for every row, except CPU Imbalance, where it is 100 at 1 (one running thread per running core). Any imbalance is yellow.

**Excluded.** Six green ranges are marked "Excluded" in the source table. A host that is not busy, has little reserved or is not overcommitted says nothing about risk. So while they are green, these sub-metrics are left out of the KPI instead of scoring 100. They count once they leave green.

## How each sub-metric is calculated

Each sub-metric is calculated per host, then the highest (worst) host is kept.

| Sub-metric | Per host | Source |
| :--- | :--- | :--- |
| CPU Thread Utilization | `cpu.utilization`: the share of the host's CPU threads in use, hyper-threading aware | VCF Operations: `cpu\|utilization_average` |
| CPU Imbalance | Count of running CPU threads ÷ count of running CPU cores. Running threads = `cpu.utilization` % × threads. Running cores = `cpu.coreUtilization` % × cores. | VCF Operations: `cpu\|utilization_average`, `cpu\|coreUtilization_average`, `hardware\|cpuInfo\|numCpuCores`. Threads: see below. |
| Memory Consumed | Consumed memory, as a share of host memory | VCF Operations: `mem\|consumed_average` / `mem\|totalCapacity_average` |
| Memory Ballooned | Ballooned memory, as a share of host memory | VCF Operations: `mem\|vmmemctl_average` / `mem\|totalCapacity_average` |
| Memory Zip Swap | Compressed plus swapped memory, as a share of host memory | VCF Operations: (`mem\|compressed_average` + `mem\|swapused_average`) / `mem\|totalCapacity_average` |
| Memory Tiering Latency | Read latency of the NVMe memory tier. Only hosts with memory tiering have it; for the others it is left out. | VCF Operations: `mem:NVMe\|latency.read_latest` |
| CPU Reservation | Reserved CPU, as a share of host CPU capacity | VCF Operations: `cpu\|reservedCapacity_average` / `cpu\|totalCapacity_average` |
| Memory Reservation | Reserved memory, as a share of host memory | VCF Operations: `mem\|reservedCapacity_average` / `mem\|totalCapacity_average` |
| CPU Overcommit Ratio | vCPUs allocated to the powered-on VMs, per physical core | VCF Operations: `cpu\|vcpus_allocated_on_all_powered_on_vms`, `hardware\|cpuInfo\|numCpuCores` |
| Memory Overcommit Ratio | Memory allocated to the powered-on VMs, divided by host memory capacity. Both stats are in KB, so they divide directly. | VCF Operations: `mem\|memory_allocated_on_all_powered_on_vms` / `mem\|totalCapacity_average` |
| CPU Monster VM to Host Ratio | vCPUs of the largest powered-on VM, against the monster size of its host (see below) | VCF Operations: VM `config\|hardware\|numCpu`, host `hardware\|cpuInfo\|numCpuCores` |
| Memory Monster VM to Host Ratio | Memory of the largest powered-on VM, against the monster size of its host (see below) | VCF Operations: VM `config\|hardware\|memoryKB`. Host DIMM memory: `mem:DRAM\|memory_tier_total_capacity`, or `mem\|totalCapacity_average` on a host without memory tiering. |

### Where each host's data comes from

Everything comes from VCF Operations, read once per collection cycle for all objects, so nothing is collected twice. Nothing is read from vCenter.

| Data | VCF Operations source |
| :--- | :--- |
| Hosts of the cluster | Host property `summary\|parentCluster`, matched to the cluster name |
| Powered-on VMs of a host | VM properties `summary\|parentHost`, matched to the host name, and `summary\|runtime\|powerState` = "Powered On" |
| Physical cores | Host property `hardware\|cpuInfo\|numCpuCores` |
| Threads | 2 × cores when both `config\|hyperThread\|available` and `config\|hyperThread\|active` are "true". Otherwise the cores. |
| VM size | VM properties `config\|hardware\|numCpu` and `config\|hardware\|memoryKB` |
| DIMM memory | Host stat `mem:DRAM\|memory_tier_total_capacity` (the DRAM tier). Without memory tiering, `mem\|totalCapacity_average`. |

Placement is by name, because `summary|parentCluster` and `summary|parentHost` hold the name shown in vCenter, not an id. Names are unique inside one datacenter, so do not mix datacenters in one adapter instance.

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

Two hosts, each with 32 cores (64 threads) and 512 GB. Each runs four VMs of 4 vCPU and 16 GB. The monster size of these hosts is 16 vCPU (half of 32 cores) and 204.8 GB (40 % of 512 GB, less than 256 GB).

- **Healthy.** Both hosts at 40 % thread and 80 % core utilization (one running thread per running core), 50 % memory consumed, nothing ballooned, swapped or reserved.
  - Left out: the six rows in their excluded green, and Memory Tiering Latency (these hosts have no memory tiering).
  - Counted: CPU Imbalance 1 (100), Ballooned 0 (100), Zip Swap 0 (100), CPU Monster VM `4 / 16` = 0.25 (93.75), Memory Monster VM `16 / 204.8` = 0.08 (98).
  - KPI = `(100 + 100 + 100 + 93.75 + 98) / 5` = **98.35**.
- **One busy host.** Host 1 at 90 % thread and 100 % core utilization. Host 2 at 30 % and 60 %.
  - CPU Thread Utilization 90 leaves its excluded green. It is at the start of red: 25 with weight 8.
  - CPU Imbalance of host 1 is `57.6 running threads / 32 running cores` = 1.8. Host 2 is 1.0. The worst, 1.8, is halfway through red: 12.5 with weight 8.
  - KPI = `(25 × 8 + 12.5 × 8 + 100 + 100 + 93.75 + 98) / (8 + 8 + 4)` = **34.59**.

The same examples are checked by the tests in [`Management Pack/tests/test_cluster_risk_metrics.py`](../Management%20Pack/tests/test_cluster_risk_metrics.py).

## Missing data

A sub-metric with no data is not published for that cycle, and it is left out of the KPI. It is never counted as 0, because 0 means "no risk".

- If the stats request to VCF Operations fails, only the property-based rows (the two Monster VM ratios) are scored.
- A host that VCF Operations does not know is left out.

## To verify on a live system

- **CPU Thread Utilization and CPU Imbalance** read `cpu|utilization_average` and `cpu|coreUtilization_average`, the VCF Operations keys expected for vCenter's `cpu.utilization` and `cpu.coreUtilization`. Confirm the keys on your hosts.
- **Memory stat keys:** `mem|totalCapacity_average`, `mem|swapused_average` and the two `reservedCapacity_average` keys are the expected names. Confirm they exist on your hosts.
- **Memory Tiering Latency** reads `mem:NVMe|latency.read_latest` and assumes it is in µs, the unit of the limits.
- **Overcommit and Monster VM** count powered-on VMs only.
- **DIMM memory** reads `mem:DRAM|memory_tier_total_capacity` and assumes it is in KB, like `mem|totalCapacity_average`. A host without it (no memory tiering) counts all its memory as DIMM.
