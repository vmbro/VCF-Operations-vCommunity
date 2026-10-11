# Network Speed Degradation

**Network Speed Degradation** shows whether the physical NICs of an ESXi host run at the speed they are configured for. A NIC that negotiates a lower speed, for example 1 Gbps on a 10 Gbps link after a cable or switch port problem, still works, so it is easy to miss.

It replaces the "Network Speed Degradation" and "Total Network Speed Degradation" super metrics, and fixes two problems in their formula. See [Changes from the super metrics](#changes-from-the-super-metrics).

Code: [`Management Pack/app/metrics/network/network_speed_degradation.py`](../Management%20Pack/app/metrics/network/network_speed_degradation.py)

## Known limitations

> **Read this before using the metrics.**

- **A NIC set to auto-negotiate may have no configured speed.** A NIC without a configured speed (none or 0) cannot be compared, so it is left out. A host whose NICs all auto-negotiate then has no value, and is not counted. *To verify on a live system:* the value of `net|configuredSpeed` for an auto-negotiating NIC.
- **A NIC that is down is not counted as degraded.** A speed of 0 means the NIC is down or unused, which is a different problem from running slower. It is left out.
- **A host without a value is not counted in Total Network Speed Degradation.** The count is a lower bound: there may be more degraded hosts among those that could not be checked.
- **The Datacenter of a host is matched by name**, from the host property `summary|parentDatacenter`. Names are unique inside one vCenter. *To verify on a live system:* that VCF Operations has this property on hosts.
- **The vSphere World count can be up to one collection cycle old (5 minutes).** It is built from the host values already stored in VCF Operations, like the other [vSphere World metrics](vsphere-world-metrics.md#known-limitations). Every account publishes the same count.
- **When VCF Operations returns no NIC speed for any host, nothing is published for that cycle.** The request has failed. Publishing a count of 0 would be false assurance.

## The metrics

| Object | Metric | Calculation |
| :--- | :--- | :--- |
| ESXi host | `vCommunity\|Network\|Network Speed Degradation` (%) | Sum of the actual NIC speeds ÷ sum of the configured NIC speeds × 100, over the NICs that can be compared. 100 % means no degradation. Capped at 100 %. |
| Datacenter | `vCommunity\|Network\|Total Network Speed Degradation` (count) | The number of hosts of the Datacenter below 100 %. From the same collection cycle. |
| vSphere World | `vCommunity\|Network\|Total Network Speed Degradation` (count) | The number of hosts below 100 %, of all vCenters. |

**Inputs.** Per physical NIC, in Mbps, from VCF Operations: `net|speed` (the speed the NIC runs at) and `net|configuredSpeed`. VCF Operations returns one value per NIC, such as `net:vmnic0|speed`, and the code compares each NIC with its own configured speed.

## Design considerations

- **Each NIC is checked on its own.** The super metric averaged all speeds and all configured speeds, so a NIC that was down looked like degradation, and one without a configured speed made the result wrong.
- **A host with no NIC left to compare has no value**, instead of a division by zero.
- **Read once per cycle per vCenter**, before the collection starts, for the host and Datacenter values.
- All inputs come from VCF Operations. Nothing is read from vCenter.

## Examples

| NICs (actual / configured, Mbps) | Value |
| :--- | :--- |
| 10000 / 10000, 10000 / 10000 | 100 % |
| 1000 / 10000, 10000 / 10000 | (1000 + 10000) ÷ (10000 + 10000) = 55 % |
| 0 / 10000 (down), 10000 / 10000 | 100 %: the NIC that is down is left out |
| 10000 / 0 (no configured speed) | no value |

The same examples are checked by the tests in [`Management Pack/tests/test_network_speed_degradation.py`](../Management%20Pack/tests/test_network_speed_degradation.py).

## Changes from the super metrics

| Problem in the super metric | Fix |
| :--- | :--- |
| `avg(net\|speed) / avg(net\|configuredSpeed)`: a NIC that was down (speed 0) pulled the average down, as if it were degraded. | Each NIC is compared with its own configured speed. A NIC that is down is left out. |
| A host without a configured speed divided by zero. | NICs without a configured speed are left out. A host with none left has no value. |
| The count on Datacenter and vSphere World was a super metric over the host super metric. | Calculated in code: per Datacenter from the same cycle, on vSphere World from the stored host values. |
