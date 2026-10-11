#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Operational Availability of ESXi hosts and clusters.

What it is
----------
ESXi Host Operational Availability (%, per host)
    25 points for each condition met: powered on, connected, not in maintenance, not in quarantine.
    So a host is 0, 25, 50, 75 or 100 %. Hardware redundancy is not part of it: workloads can run fine
    on a host that has lost a redundant component.

Cluster Operational Availability (%, per cluster)
    min(100, (sum of the host values - the k lowest host values) / (N - k))
    N is the number of hosts in the cluster, k the number of host failures vSphere HA tolerates
    (N+k). The k spare hosts are assumed to be the k worst hosts, so any other degraded host counts
    against the cluster. Capped at 100 %, so a cluster with more spare capacity does not look better.
    No value when N - k is 0 or less.

Worst Cluster Operational Availability (%, per vCenter)
    The lowest Cluster Operational Availability of the clusters of this account's vCenter.

Both replace super metrics. They fix three problems of those formulas:
    1. "disconnected" contains "connected", so a disconnected host scored as connected. Values are now
       compared exactly.
    2. A cluster without HA host failover (N+0) lost one host in the formula: a healthy 4-host cluster
       showed 75 %. Now any k works, including 0.
    3. Only one host was set aside, whatever the failover level. Now k hosts are set aside for N+k.

Design choices (strict: a problem must never be hidden)
    - A host with no data counts as 0 %, not left out. Leaving it out would make its cluster look better.
    - N is summary|total_number_hosts. When VCF Operations has no value, the hosts found in the cluster.
    - No host failover level (HA off, percentage-based or dedicated-host admission control, or the value
      was not collected) counts as k = 0. That makes the value lower than real, never higher.
    - When no host has any data at all, the request to VCF Operations failed: nothing is published,
      instead of every host and cluster at 0 %.

All inputs come from VCF Operations. See docs/operational-availability.md, including its known limitations.
"""
import logging
from typing import Dict, List, NamedTuple, Optional
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from utils.ops_inventory import HostInfo, read_hosts
from utils.ops_stats import as_number, query_resources, read_latest_properties, read_latest_stats

logger = logging.getLogger(__name__)

# Where the metrics are published, under vCommunity.
GROUP = "Availability"
HOST_METRIC = "ESXi Host Operational Availability"
CLUSTER_METRIC = "Cluster Operational Availability"
WORST_CLUSTER_METRIC = "Worst Cluster Operational Availability"

# Host inputs. The three properties are compared with these exact values.
HOST_POWERED_ON = "sys|poweredOn"                       # stat: 1 when powered on
HOST_CONDITIONS = {
    "runtime|connectionState": "connected",
    "runtime|maintenanceState": "notInMaintenance",
    "runtime|quarantineState": "notInQuarantine",
}
POINTS_PER_CONDITION = 25.0

# Cluster inputs.
CLUSTER_HOST_COUNT = "summary|total_number_hosts"
CLUSTER_FAILOVER_LEVEL = "configuration|dasConfig|hostFailoverLevel"


# ---------------------------------------------------------------------------
# Formulas. They make no API calls.
# ---------------------------------------------------------------------------

def host_availability(powered_on: Optional[float], properties: Dict[str, str]) -> float:
    """0, 25, 50, 75 or 100. A condition with no data is not met."""
    conditions_met = [powered_on == 1]
    conditions_met += [properties.get(key) == value for key, value in HOST_CONDITIONS.items()]
    return POINTS_PER_CONDITION * sum(conditions_met)


def cluster_availability(host_values: List[float], host_count: Optional[float],
                         failover_level: Optional[float]) -> Optional[float]:
    """min(100, (sum - the k lowest) / (N - k)). None when N - k is 0 or less.

    host_values has one value per host found in the cluster. Hosts counted in host_count but not found
    count as 0 %. No failover level counts as k = 0.
    """
    n = max(int(host_count or 0), len(host_values))
    k = int(failover_level or 0)
    if n - k <= 0:
        return None
    # A host that VCF Operations counts but that has no data is unavailable: 0 %.
    values = sorted(host_values + [0.0] * (n - len(host_values)))
    return min(100.0, (sum(values) - sum(values[:k])) / (n - k))


def worst(values: List[Optional[float]]) -> Optional[float]:
    """The lowest value. A cluster without a value is left out. None when there is none."""
    known = [value for value in values if value is not None]
    return min(known) if known else None


# ---------------------------------------------------------------------------
# Reading from VCF Operations, once per collection cycle for the whole vCenter.
# ---------------------------------------------------------------------------

class OperationalAvailability(NamedTuple):
    """The values of one vCenter. Empty when they could not be read."""
    by_host: Dict[str, float]                   # host resource id -> %
    by_cluster: Dict[str, Optional[float]]      # cluster name, as in summary|parentCluster -> %

    def worst_cluster(self) -> Optional[float]:
        return worst(list(self.by_cluster.values()))


NO_DATA = OperationalAvailability({}, {})


def read_operational_availability(suite_api_client: SuiteApiClient, adapter_instance_id: str) -> OperationalAvailability:
    """Reads the hosts and clusters of one vCenter, and calculates their Operational Availability."""
    try:
        hosts = read_hosts(suite_api_client, adapter_instance_id)
        by_host = read_host_availability(suite_api_client, hosts)
        if by_host is None:
            return NO_DATA
        clusters = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, "ClusterComputeResource", adapter_instance_id)
        by_cluster = read_cluster_availability(suite_api_client, clusters, hosts, by_host)
        return OperationalAvailability(by_host, by_cluster)
    except Exception as e:
        logger.warning(f"Failed to read Operational Availability, so none this cycle - {repr(e)}")
        return NO_DATA


def read_host_availability(suite_api_client: SuiteApiClient, hosts: List[HostInfo]) -> Optional[Dict[str, float]]:
    """{host id: %}. None when no host has any data: the requests failed, so there is nothing to score."""
    host_ids = [host.id for host in hosts]
    stats = read_latest_stats(suite_api_client, host_ids, [HOST_POWERED_ON])
    properties = read_latest_properties(suite_api_client, host_ids, list(HOST_CONDITIONS))
    if host_ids and not stats and not properties:
        logger.warning("No Operational Availability data for any host, so none is published this cycle")
        return None
    return {
        host_id: host_availability(stats.get(host_id, {}).get(HOST_POWERED_ON), properties.get(host_id, {}))
        for host_id in host_ids
    }


def read_cluster_availability(suite_api_client: SuiteApiClient, clusters, hosts: List[HostInfo],
                              by_host: Dict[str, float]) -> Dict[str, Optional[float]]:
    """{cluster name: %}. The failover level is read as a stat, or as a property when it is stored as one."""
    cluster_ids = [cluster.id for cluster in clusters]
    stats = read_latest_stats(suite_api_client, cluster_ids, [CLUSTER_HOST_COUNT, CLUSTER_FAILOVER_LEVEL])
    properties = read_latest_properties(suite_api_client, cluster_ids, [CLUSTER_FAILOVER_LEVEL])

    by_cluster = {}
    for cluster in clusters:
        cluster_stats = stats.get(cluster.id, {})
        failover_level = cluster_stats.get(CLUSTER_FAILOVER_LEVEL)
        if failover_level is None:
            failover_level = as_number(properties.get(cluster.id, {}).get(CLUSTER_FAILOVER_LEVEL))
        host_values = [by_host[host.id] for host in hosts if host.cluster_name == cluster.name]
        by_cluster[cluster.name] = cluster_availability(host_values, cluster_stats.get(CLUSTER_HOST_COUNT), failover_level)
    return by_cluster


def publish(obj, metric: str, value: Optional[float]) -> None:
    """Publishes one value under vCommunity|Availability, rounded to two decimals."""
    if value is not None:
        obj.with_metric(f"vCommunity|{GROUP}|{metric}", round(value, 2))
