#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Operational Availability summary on the vSphere World object, over all vCenters.

    Worst Cluster Operational Availability   the lowest Cluster Operational Availability of any cluster
    ESXi Hosts Operational Availability      the average ESXi Host Operational Availability of all hosts

Built from the values already stored in VCF Operations, like the cluster summary metrics, so they have the
same known limitations: a value can be up to one collection cycle old, and every account publishes the same
values. A host or cluster without a stored value is left out: it may belong to a vCenter that has no account
of this pack. See docs/operational-availability.md.

The average is not rolled up to the cluster: a cluster has to consider vSphere HA. See operational_availability.py.
"""
import logging
from typing import Dict, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from metrics.availability.operational_availability import (
    GROUP, HOST_METRIC, CLUSTER_METRIC, WORST_CLUSTER_METRIC, publish, worst,
)
from utils.ops_stats import query_resources, read_latest_stats

logger = logging.getLogger(__name__)

HOSTS_METRIC = "ESXi Hosts Operational Availability"

# The values stored in VCF Operations.
STORED_HOST_VALUE = f"vCommunity|{GROUP}|{HOST_METRIC}"
STORED_CLUSTER_VALUE = f"vCommunity|{GROUP}|{CLUSTER_METRIC}"


def average(values) -> Optional[float]:
    values = list(values)
    return sum(values) / len(values) if values else None


def read_stored_values(suite_api_client: SuiteApiClient, resource_kind: str, stat_key: str) -> Dict[str, float]:
    """{resource id: stored value} for every object of one kind, of all vCenters. Objects without one are absent."""
    resources = query_resources(suite_api_client, VCENTER_ADAPTER_KIND, resource_kind, None)
    stats = read_latest_stats(suite_api_client, [resource.id for resource in resources], [stat_key])
    return {resource_id: values[stat_key] for resource_id, values in stats.items() if stat_key in values}


def collect_availability_summary_metrics(world_obj: Object, suite_api_client: SuiteApiClient) -> None:
    """Publishes the two metrics on the vSphere World object."""
    try:
        clusters = read_stored_values(suite_api_client, "ClusterComputeResource", STORED_CLUSTER_VALUE)
        hosts = read_stored_values(suite_api_client, "HostSystem", STORED_HOST_VALUE)
        publish(world_obj, WORST_CLUSTER_METRIC, worst(list(clusters.values())))
        publish(world_obj, HOSTS_METRIC, average(hosts.values()))
    except Exception as e:
        # A failure here must not stop the rest of the collection.
        logger.warning(f"Failed to publish the Operational Availability summary on vSphere World - {repr(e)}")
