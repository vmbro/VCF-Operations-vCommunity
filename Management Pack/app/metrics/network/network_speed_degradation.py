#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Network Speed Degradation of ESXi hosts, and the count of degraded hosts.

What it is
----------
Network Speed Degradation (%, per host)
    The speed the physical NICs run at, as a share of the speed they are configured for:
    sum of the actual speeds / sum of the configured speeds x 100, over the NICs that can be compared.
    100 % means no degradation. Below 100 %, a NIC negotiated a lower speed than configured.

Total Network Speed Degradation (count, per Datacenter and on vSphere World)
    The number of hosts below 100 %.

Both replace super metrics. The host super metric was avg(net|speed) / avg(net|configuredSpeed): a NIC that
is down (speed 0) pulled the average down as if it were degraded, and a host with no configured speed divided
by zero. Here each NIC is checked:
    - A NIC with no speed or speed 0 is down or unused. It is not degraded, so it is left out.
    - A NIC with no configured speed or 0 cannot be compared, so it is left out.
    - A host with no NIC left to compare has no value.

Datacenter: the hosts of this account's vCenter, matched to the Datacenter by name (summary|parentDatacenter).
A Datacenter is in one vCenter, so the count is from the same collection cycle.
vSphere World: the stored values of all hosts of all vCenters, so it has the known limitations of the other
vSphere World metrics.

All inputs come from VCF Operations. See docs/network-speed-degradation.md, including its known limitations.
"""
import logging
from typing import Dict, List, NamedTuple, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from utils.ops_stats import query_resources, read_latest_instance_stats, read_latest_properties, read_latest_stats

logger = logging.getLogger(__name__)

# Where the metrics are published, under vCommunity.
GROUP = "Network"
HOST_METRIC = "Network Speed Degradation"
COUNT_METRIC = "Total Network Speed Degradation"

# Per physical NIC, in Mbps. VCF Operations returns one value per NIC, such as net:vmnic0|speed.
NIC_SPEED = "net|speed"
NIC_CONFIGURED_SPEED = "net|configuredSpeed"
HOST_DATACENTER = "summary|parentDatacenter"        # name of the Datacenter the host is in

# The host value, as stored in VCF Operations. Read for vSphere World.
STORED_HOST_VALUE = f"vCommunity|{GROUP}|{HOST_METRIC}"


# ---------------------------------------------------------------------------
# Formulas. They make no API calls.
# ---------------------------------------------------------------------------

def speed_degradation(speeds: Dict[str, float], configured_speeds: Dict[str, float]) -> Optional[float]:
    """Sum of actual speeds / sum of configured speeds x 100, over the NICs that can be compared.

    A NIC that is down (no speed or 0) or has no configured speed (none or 0) is left out.
    None when no NIC is left. Capped at 100 %: a NIC faster than configured is not "less degraded".
    """
    nics = [nic for nic in speeds if speeds[nic] > 0 and configured_speeds.get(nic, 0) > 0]
    if not nics:
        return None
    actual = sum(speeds[nic] for nic in nics)
    configured = sum(configured_speeds[nic] for nic in nics)
    return min(100.0, actual / configured * 100)


def degraded_count(values: List[Optional[float]]) -> int:
    """The number of hosts below 100 %. A host without a value is not counted."""
    return sum(1 for value in values if value is not None and value < 100)


# ---------------------------------------------------------------------------
# Reading from VCF Operations, once per collection cycle for the whole vCenter.
# ---------------------------------------------------------------------------

class NetworkSpeed(NamedTuple):
    """The values of one vCenter. Empty when they could not be read."""
    by_host: Dict[str, Optional[float]]         # host resource id -> %
    count_by_datacenter: Dict[str, int]         # Datacenter name, as in summary|parentDatacenter -> hosts below 100 %


NO_DATA = NetworkSpeed({}, {})


def read_network_speed(suite_api_client: SuiteApiClient, adapter_instance_id: str) -> NetworkSpeed:
    """Reads the NIC speeds of the hosts of one vCenter, and calculates the degradation."""
    try:
        hosts = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "HostSystem", adapter_instance_id)
        host_ids = [host.id for host in hosts]
        nics = read_latest_instance_stats(suite_api_client, host_ids, [NIC_SPEED, NIC_CONFIGURED_SPEED])
        datacenters = read_latest_properties(suite_api_client, host_ids, [HOST_DATACENTER])
        if host_ids and not nics:
            # No NIC speed for any host: the request failed. A count of 0 would be false assurance.
            logger.warning("No NIC speeds for any host, so no Network Speed Degradation this cycle")
            return NO_DATA

        by_host = {
            host_id: speed_degradation(nics.get(host_id, {}).get(NIC_SPEED, {}),
                                       nics.get(host_id, {}).get(NIC_CONFIGURED_SPEED, {}))
            for host_id in host_ids
        }
        count_by_datacenter = {}
        for host_id in host_ids:
            datacenter = datacenters.get(host_id, {}).get(HOST_DATACENTER)
            if datacenter is not None:
                count_by_datacenter.setdefault(datacenter, 0)
                count_by_datacenter[datacenter] += degraded_count([by_host[host_id]])
        return NetworkSpeed(by_host, count_by_datacenter)
    except Exception as e:
        logger.warning(f"Failed to read the network speeds, so no Network Speed Degradation this cycle - {repr(e)}")
        return NO_DATA


def collect_world_network_speed(world_obj: Object, suite_api_client: SuiteApiClient) -> None:
    """Publishes Total Network Speed Degradation on vSphere World, from the stored values of all hosts."""
    try:
        hosts = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "HostSystem", None)
        stats = read_latest_stats(suite_api_client, [host.id for host in hosts], [STORED_HOST_VALUE])
        if not stats:
            return      # nothing stored yet, or the request failed: no count rather than a false 0
        values = [host_stats.get(STORED_HOST_VALUE) for host_stats in stats.values()]
        publish(world_obj, COUNT_METRIC, degraded_count(values))
    except Exception as e:
        logger.warning(f"Failed to publish Total Network Speed Degradation on vSphere World - {repr(e)}")


def publish(obj, metric: str, value: Optional[float]) -> None:
    """Publishes one value under vCommunity|Network."""
    if value is not None:
        obj.with_metric(f"vCommunity|{GROUP}|{metric}", round(value, 2))
