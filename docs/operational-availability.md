# Operational Availability

**Operational Availability** shows whether ESXi hosts and clusters are available to run workloads. It is published on the host, the cluster, the vCenter and the vSphere World object, in %.

It replaces the "ESXi Host Operational Availability" and "Cluster Operational Availability" super metrics, and fixes three problems in their formulas. See [Changes from the super metrics](#changes-from-the-super-metrics).

Code: [`Management Pack/app/metrics/availability/operational_availability.py`](../Management%20Pack/app/metrics/availability/operational_availability.py)

## Known limitations

> **Read this before using the metrics.**

- **No HA host failover level counts as N+0.** This applies when vSphere HA is off, when admission control uses a percentage of resources or a dedicated failover host, or when the value was not collected. The cluster value is then lower than the real availability, never higher. A collection failure can therefore cause a false alarm, but never false assurance.
- **A cluster where HA tolerates the failure of every host has no value.** For example, a 2-host cluster with a failover level of 2: N − k is 0.
- **Worst Cluster leaves out a cluster with no value.** There is no number to compare. Such a cluster is not shown as the worst, even if it is unavailable.
- **The vSphere World values can be up to one collection cycle old (5 minutes).** They are built from the values already stored in VCF Operations, like the other [vSphere World metrics](vsphere-world-metrics.md#known-limitations). Every account publishes the same values.
- **vSphere World leaves out hosts and clusters without a stored value.** For example, those of a vCenter that has no account of this pack.
- **When VCF Operations returns no data for any host, nothing is published for that cycle.** The request has failed. Publishing every host and cluster at 0 % would be a false alarm across the estate.

## The metrics

| Object | Metric | Calculation |
| :--- | :--- | :--- |
| ESXi host | `vCommunity\|Availability\|ESXi Host Operational Availability` | 25 points for each condition met: powered on, connected, not in maintenance, not in quarantine. So 0, 25, 50, 75 or 100 %. |
| Cluster | `vCommunity\|Availability\|Cluster Operational Availability` | `min(100, (sum of the host values − the k lowest host values) ÷ (N − k))` |
| vCenter | `vCommunity\|Availability\|Worst Cluster Operational Availability` | The lowest Cluster Operational Availability of the clusters of this vCenter. Calculated in the same cycle, so it is never old. |
| vSphere World | `vCommunity\|Availability\|Worst Cluster Operational Availability` | The lowest Cluster Operational Availability of all clusters, of all vCenters. |
| vSphere World | `vCommunity\|Availability\|ESXi Hosts Operational Availability` | The average ESXi Host Operational Availability of all hosts, of all vCenters. |

**Host conditions.** Each is compared with the exact value:

| Condition | VCF Operations source | Met when |
| :--- | :--- | :--- |
| Powered on | `sys\|poweredOn` (stat) | 1 |
| Connected | `runtime\|connectionState` (property) | `connected` |
| Not in maintenance | `runtime\|maintenanceState` (property) | `notInMaintenance` |
| Not in quarantine | `runtime\|quarantineState` (property) | `notInQuarantine` (new in VCF 9) |

Hardware redundancy is not part of it. Workloads can run fine on a host that has lost a redundant component. Operational availability and hardware availability complement each other.

**Cluster.** N is the number of hosts, `summary|total_number_hosts`. k is the number of host failures vSphere HA tolerates, `configuration|dasConfig|hostFailoverLevel` (N+k). The k spare hosts are assumed to be the k worst hosts, so any other degraded host counts against the cluster. The value is capped at 100 %, so a cluster with more spare capacity does not look better than one with less, and the values can be averaged over time and across clusters.

The host average is not rolled up to the cluster, because a cluster has to consider vSphere HA.

## Design considerations

The design is strict: a problem must never be hidden.

- **A host with no data counts as 0 %.** It is not left out, because leaving it out would make its cluster look better than it is.
- **A host that VCF Operations counts in the cluster but that has no data also counts as 0 %.** N is `summary|total_number_hosts`, so a missing host cannot shrink the cluster. Only when VCF Operations has no host count are the hosts found in the cluster used.
- **No failover level counts as k = 0 (N+0).** This lowers the value, never raises it. See [Known limitations](#known-limitations).
- **A failed request publishes nothing.** If no host has any data at all, the request to VCF Operations failed. The metrics are left out for that cycle, rather than showing every host at 0 %.
- **Read once per cycle per vCenter.** The host, cluster and vCenter values come from one set of requests to VCF Operations, made before the collection starts.
- All inputs come from VCF Operations. Nothing is read from vCenter.

## Examples

| Cluster | Host values | N+k | Value |
| :--- | :--- | :--- | :--- |
| 4 hosts, all healthy | 100, 100, 100, 100 | N+0 | 100 |
| 4 hosts, one in maintenance | 100, 100, 100, 75 | N+0 | 93.75 |
| 4 hosts, one down | 100, 100, 100, 0 | N+1 | 100 |
| 4 hosts, two down | 100, 100, 0, 0 | N+1 | 66.67 |
| 4 hosts, two degraded | 100, 100, 75, 75 | N+1 | (350 − 75) ÷ 3 = 91.67 |
| 10 hosts, two down | 8 × 100, 2 × 0 | N+2 | 100 |
| 10 hosts, three degraded | 7 × 100, 3 × 50 | N+2 | (850 − 100) ÷ 8 = 93.75 |
| 4 counted, 3 found | 100, 100, 100, (missing = 0) | N+0 | 75 |

The same examples are checked by the tests in [`Management Pack/tests/test_operational_availability.py`](../Management%20Pack/tests/test_operational_availability.py).

## Changes from the super metrics

| Problem in the super metric | Fix |
| :--- | :--- |
| `contains 'connected'` also matched "disconnected", so a disconnected host scored as connected. | Values are compared exactly. |
| One host was always set aside: a healthy N+0 cluster of 4 hosts showed 75 %, and a healthy single host 0 %. | k hosts are set aside, where k is the HA failover level. N+0 sets none aside. |
| Only one host was set aside, whatever the failover level (N+2 or more). | k hosts are set aside for N+k. |
| No value when the cluster had no HA failover level. | Counted as N+0, and documented. |

The super metric "Worst Cluster Operational Availability" on Custom Datacenter is no longer provided.
