# Metrics

This folder holds the code that calculates metrics and publishes them to VCF Operations. Read this page before you change a metric or add one.

There are two kinds of metric here:

- **Plain metrics.** One value, read from vCenter and published. Example: DRS Score.
- **KPIs.** One 0-100 % score per object, built from many sub-metrics. Most of this page is about KPIs.

## The five KPIs

All five use the same scoring, in `kpi_score.py`. Each has its own table of sub-metrics and limits.

| KPI | Object | Sub-metrics | Status | Source of the limits |
| :--- | :--- | :--- | :--- | :--- |
| Cluster Performance | Cluster | 9 | Working | `docs/Complex Metrics/vSphere Cluster Performance metric.png` |
| VM Performance | VM | 9 | Working | `docs/Complex Metrics/Virtual Motherboard Performance metric.png` |
| Guest OS Performance | VM | 4 | Working | `docs/Complex Metrics/Guest OS Performance metric.png` |
| Cluster Risk | Cluster | 12 | Working | `docs/Complex Metrics/vSphere Cluster Risk metric.png` |
| ESXi Performance | ESXi host | 9 | Working | `docs/Complex Metrics/vSphere ESXi Performance metric.png` |

All five are called by a collector and declared in `adapter.py`. A few VCF Operations stat keys still need to be confirmed on a live system. Each user page lists them under "To verify on a live system".

## What is in this folder

| File | What it does |
| :--- | :--- |
| `kpi_score.py` | The scoring shared by every KPI. It turns sub-metric values into one 0-100 % score. It makes no API calls. |
| `cluster/cluster_performance_metrics.py` | Cluster Performance KPI. One score per cluster, from 9 sub-metrics. |
| `cluster/cluster_risk_metrics.py` | Cluster Risk KPI. One score per cluster, from 12 sub-metrics. |
| `cluster/drs_metrics.py` | DRS Score. A plain metric, not a KPI. |
| `vm/vm_performance_metrics.py` | VM Performance KPI. One score per powered-on VM, from 9 sub-metrics. Also reads the stats of Guest OS Performance. |
| `vm/guest_os_performance_metrics.py` | Guest OS Performance KPI. One score per powered-on VM with VMware Tools, from 4 sub-metrics. |
| `host/esxi_performance_metrics.py` | ESXi Performance KPI. One score per connected ESXi host, from 9 sub-metrics. |
| `vm_contention.py` | The worst-VM, 90th-percentile and bad-packet formulas, shared by Cluster Performance and ESXi Performance. |

Two files outside this folder belong to the same design:

| File | What it does |
| :--- | :--- |
| `../utils/ops_stats.py` | Reads stats from VCF Operations, for many objects in one request. |
| `../utils/vcenter_inventory.py` | Reads from vCenter which VMs run on which host, VM sizes and host hardware, once per cycle. |
| `../adapter.py` | Declares each metric to VCF Operations. `define_kpi()` does this for a KPI. A unit used in a KPI table must be listed in `KPI_UNITS` there. |

## Where the numbers come from

The KPIs do not measure anything themselves. The vCenter adapter of VCF Operations already collects stats such as CPU Ready for every VM. A KPI reads those stored stats back through the VCF Operations API, calculates a score, and publishes the score on the same object.

This has two consequences:

- A KPI is at most one collection cycle behind the stats it is built from.
- If the vCenter adapter has not collected a stat, the KPI has no data for it. See [Missing data](#missing-data).

Every metric is published under the `vCommunity` group of the object. A KPI gets its own group below that, for example `vCommunity|VM Performance|VM Performance`.

## How a KPI works

A KPI replaces a super metric. A super metric repeats the same long formula once per input, which is hard to read and easy to get wrong. Here the formula exists once, in `kpi_score.py`, and each KPI is a table.

### One table per KPI

Each KPI module has a table named `METRICS`. One row is one sub-metric: its name, its unit and five limits.

```python
METRICS = [
    #       name                 unit   best    green  yellow  orange  zero-at
    Metric("CPU Ready",          "%",   0.0,    2.0,   4.0,    8.0,    16.0),
    Metric("CPU Run",            "%",   60.0,   80.0,  90.0,   95.0,   100.0),
    Metric("Guest Free Memory",  "MB",  1024.0, 512.0, 256.0,  128.0,  0.0),
]
```

The five limits are the values where the score of that sub-metric is 100, 75, 50, 25 and 0.

- **Lower is better** (CPU Ready): the limits go up.
- **Higher is better** (Guest Free Memory): the limits go down. The same code handles both.
- **The first limit does not have to be 0** (CPU Run): every value up to 60 scores 100.

### From value to score

The five limits split the values into four tiers. Inside a tier the score drops in a straight line.

| Tier | Value range | Score goes from → to | Weight |
| :--- | :--- | :--- | :--- |
| Green | best up to the green limit | 100 → 75 | 1 |
| Yellow | green limit up to the yellow limit | 75 → 50 | 2 |
| Orange | yellow limit up to the orange limit | 50 → 25 | 4 |
| Red | orange limit up to the zero-at limit | 25 → 0 | 8 |

Beyond the zero-at limit the score stays at 0. Before the best limit it stays at 100.

### From scores to the KPI

```
KPI = Σ(score × weight) / Σ(weight)
```

The weight of a sub-metric depends on the tier it is in, and doubles with each tier. This is deliberate. With a plain average, one sub-metric in the red tier would be hidden by nine healthy ones. With the weights it shows.

Example with 10 sub-metrics, nine at 100 and one at 18.75 (red):

- Plain average: about 91.9. The problem is hidden.
- Weighted: `(9 × 100 + 18.75 × 8) / (9 + 8)` ≈ 61.76. The problem shows.

### Green as a single value

A source table sometimes gives green as one value, such as "0 %", not a range. Write the green limit equal to best:

```python
#       name                   unit  best  green  yellow  orange  zero-at
Metric("Bad Network Packets",  "%",  0.0,  0.0,   0.2,    0.4,    0.8),
```

Only exactly 0 is green and scores 100. Any other value starts in yellow, at 75 with weight 2. Values are rounded to two decimals first, so noise below 0.005 still counts as 0.

### Skip when green

The source tables mark some green ranges "Excluded". Being green there says nothing about health: dropped packets are rare, and low CPU or memory utilization is not a sign of good performance. Scored as 100 every cycle, these rows would add a free pass that hides the other sub-metrics. Set the last value of their row to `True`:

```python
#       name                                  unit  best  green  yellow  orange  zero-at  skip-when-green
Metric("Highest ESXi CPU Thread Utilization", "%",  0.0,  60.0,  80.0,   90.0,   95.0,    True),
```

- While the sub-metric is green, it is left out of the KPI, the same as missing data.
- Once it leaves green, it counts like any other sub-metric.
- If every sub-metric with data was skipped this way, nothing is wrong, and the KPI is 100.

Rows with skip when green today, as marked "Excluded" in the source tables:

| KPI | Sub-metrics |
| :--- | :--- |
| Cluster Performance | Highest ESXi Bad Network Packets |
| VM Performance | CPU Overlap (below 0.5 %), Network Dropped Tx (exactly 0), CPU Run (below 95 %) |
| Cluster Risk | Highest ESXi CPU Thread Utilization (below 60 %), Highest ESXi Memory Consumed (below 80 %), Highest ESXi CPU and Memory Reservation (below 10 %), Highest ESXi CPU and Memory Overcommit Ratio (below 1) |
| ESXi Performance | ESXi Bad Network Packets |

### Missing data

A sub-metric with no data is left out of the KPI. It is never counted as 0, because for most sub-metrics 0 means "perfect" and would make the object look healthier than it is.

- If no sub-metric has data, the KPI is not published for that cycle. (If some had data but all were skipped when green, the KPI is 100.)
- A sub-metric formula returns `None` to say "no data". It does not return 0.

### What is published

Each KPI module has a list named `PUBLISHED_METRICS`. The KPI itself is always published. A sub-metric is published only if the object does not already have it as a stat.

- **Cluster Performance** publishes all 9 sub-metrics. They are worst values and 90th percentiles over the cluster's VMs and hosts, so the cluster does not have them.
- **VM Performance** publishes one sub-metric, Memory Zip Swap, because it is calculated. The other 8 are read from stats the VM already has. Publishing them again would store every number twice, for every VM.
- **Guest OS Performance** publishes only the KPI. Its 4 sub-metrics are stats the VM already has, or a simple conversion of one.

## What happens in one collection cycle

1. `adapter.py` starts one collector per object type: cluster, host, VM, datastore, vCenter.
2. The collector asks VCF Operations for the stats it needs, through `utils/ops_stats.py`. It asks for many objects in one request, not one request per object.
3. For each object, the KPI module calculates the value of every sub-metric.
4. The values are rounded to two decimals. The KPI is calculated from the rounded values, so it matches the numbers a user sees.
5. The KPI module publishes the sub-metrics in `PUBLISHED_METRICS`, then the KPI.

A failure in one KPI never stops the collection. Each entry point catches its own errors and writes a warning to the adapter log.

## The parts of a KPI module

Every KPI module has the same parts, in the same order. Keep to this when you add one.

| Part | What it is |
| :--- | :--- |
| File docstring | What the KPI is, where its limits come from, what is published, how missing data is handled. |
| `GROUP`, `KPI_NAME` | The names used in VCF Operations. |
| `METRICS` | The table of sub-metrics and limits. |
| `PUBLISHED_METRICS` | The sub-metrics that are published. |
| Stat keys | The VCF Operations stats the sub-metrics are built from. |
| Sub-metric formulas | One short function per calculated sub-metric. Each returns `None` when it has no data. |
| Reading stats | The functions that call `utils/ops_stats.py`. |
| Entry point | `collect_..._metrics()`, called by the collector once per object. |

## How to change a KPI

- **Change a limit:** edit the row in `METRICS`. Nothing else.
- **Remove a sub-metric:** delete its row, and the line that supplies its value.
- **Add a sub-metric:** add a row, and supply its value. In `vm_performance_metrics.py` that is one line in `SOURCE_STATS` when the value is a VM stat as it is.
- **Change tiers or weights:** edit `TIERS` in `kpi_score.py`. This changes every KPI.

The adapter definition reads the same tables, so there is nothing to update in `adapter.py`.

## How to add a KPI

1. Create the module under the folder of its object type, for example `host/host_performance_metrics.py`. Copy the structure of `vm/vm_performance_metrics.py` when every object is scored on its own stats. Copy `cluster/cluster_performance_metrics.py` when the score is built from child objects.
2. Fill in `GROUP`, `KPI_NAME`, `METRICS` and `PUBLISHED_METRICS`.
3. Write the formulas and the entry point.
4. Call the entry point from the collector of that object type, under `../collectors/`. Read the stats once, before the loop over the objects.
5. Add one line to `adapter.py`: `define_kpi(vCommunity, <your module>)`, in the section of that object type.
6. Add the module to `KPI_MODULES` in `tests/test_kpi_score.py`. Two tests then check every row of your table.
7. Add a test file with worked examples, and a page under `docs/`.

## Tests

The tests are in `Management Pack/tests`. They use a fake VCF Operations, so they need no live system. Run them from the `Management Pack` folder:

```
python -m pytest tests
```

| File | What it checks |
| :--- | :--- |
| `test_kpi_score.py` | The scoring, the batching of stats requests, and the tables of every KPI. |
| `test_cluster_performance_metrics.py` | Cluster Performance formulas and worked examples. |
| `test_vm_performance_metrics.py` | VM Performance formulas and worked examples. |
| `test_cluster_risk_metrics.py` | Cluster Risk formulas and worked examples. |
| `test_esxi_performance_metrics.py` | ESXi Performance formulas and worked examples. |
| `test_vcenter_inventory.py` | Reading VMs per host, VM sizes and host hardware from vCenter answers. |
| `test_guest_os_performance_metrics.py` | Guest OS Performance formulas and worked examples. |

## Pages for users

- [Cluster Performance KPI](../../../docs/cluster-performance-kpi.md)
- [VM Performance KPI](../../../docs/vm-performance-kpi.md)
- [Guest OS Performance KPI](../../../docs/guest-os-performance-kpi.md)
- [Cluster Risk KPI](../../../docs/cluster-risk-kpi.md)
- [ESXi Performance KPI](../../../docs/esxi-performance-kpi.md)
- [Metrics & Properties Reference](../../../docs/metrics-reference.md)
