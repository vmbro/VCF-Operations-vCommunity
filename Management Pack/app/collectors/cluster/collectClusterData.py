#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from typing import Any
from typing import List
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from utils.vi_property_collector import retrieve_properties
from constants.main import VCENTER_ADAPTER_KIND
from properties.cluster.ha_properties import collect_ha_properties
from properties.cluster.drs_properties import collect_drs_properties
from metrics.cluster.drs_metrics import collect_drs_metrics
from properties.cluster.evc_properties import collect_evc_properties
from properties.cluster.dpm_properties import collect_dpm_properties
from properties.cluster.cluster_configuration_properties import collect_cluster_configuration_properties
from metrics.cluster.cluster_performance_metrics import collect_cluster_performance_metrics
from metrics.cluster.cluster_risk_metrics import collect_cluster_risk_metrics, HostInventory
from utils.ops_inventory import read_hosts, read_vms, powered_on_vms_by_host, hosts_by_cluster
from metrics.availability.operational_availability import OperationalAvailability, NO_DATA, CLUSTER_METRIC, publish
from pyVmomi import vim

logger = logging.getLogger(__name__)

def collect_cluster_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any,
    availability: OperationalAvailability = NO_DATA,
) -> None:
    
    propertyPaths: List[str] = []
    propertyPaths.append("summary")
    propertyPaths.append("configuration.dasConfig.enabled")
    propertyPaths.append("configuration.dasConfig.hostMonitoring")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.isolationResponse")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.restartPriority")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmStorageProtectionForAPD")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmStorageProtectionForPDL")
    propertyPaths.append("configuration.dasConfig.vmMonitoring")
    propertyPaths.append("configuration.dasConfig.hBDatastoreCandidatePolicy")
    propertyPaths.append("configuration.drsConfig.enabled")
    propertyPaths.append("configuration.drsConfig.enableVmBehaviorOverrides")
    propertyPaths.append("configurationEx")
    propertyPaths.append("configuration.drsConfig.scaleDescendantsShares")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.failureInterval")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailureWindow")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailures")
    propertyPaths.append("configuration.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.minUpTime")
    propertyPaths.append("configurationEx")
    propertyPaths.append("configStatus")
    propertyPaths.append("summary.numEffectiveHosts")
    propertyPaths.append("overallStatus")

    cluster_props = retrieve_properties(content, vim.ClusterComputeResource, propertyPaths)

    # Retrieve object types from the VCF Operations
    clusters: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["ClusterComputeResource"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )

    # Match the VCF Operations objects with the related identifier
    clusters_by_uuid: dict[str, Object] = {
        cluster.get_identifier_value("VMEntityObjectID"): cluster for cluster in clusters
    }

    # KPIs: read from VCF Operations once, for all clusters, which hosts are in each cluster and which
    # powered-on VMs run on each host, with their sizes. See utils/ops_inventory.py.
    hosts_in_cluster = hosts_by_cluster(read_hosts(suite_api_client, adapter_instance_id))
    vms_on_host = powered_on_vms_by_host(read_vms(suite_api_client, adapter_instance_id))

    for cluster_data in cluster_props:
        try:
            cluster_ref = cluster_data.obj
            cluster_moid = cluster_ref._moId

            cluster_obj = clusters_by_uuid.get(cluster_moid)
            if not cluster_obj:
                # If cluster object is not available in VCF Operations - skip it.
                continue

            prop_dict = {p.name: p.val for p in cluster_data.propSet}
            cluster_name = prop_dict.get("name", "Unknown")

            collect_ha_properties(cluster_obj, cluster_name, prop_dict)
            collect_drs_properties(cluster_obj, cluster_name, prop_dict)
            collect_evc_properties(cluster_obj, cluster_name, prop_dict)
            collect_drs_metrics(cluster_obj, cluster_name, prop_dict)
            collect_dpm_properties(cluster_obj, cluster_name, prop_dict)
            collect_cluster_configuration_properties(cluster_obj, cluster_name, prop_dict)

            # KPIs. Hosts are matched to the cluster by name, as VCF Operations shows it (summary|parentCluster).
            cluster_hosts = hosts_in_cluster.get(cluster_obj.get_key().name, [])
            cluster_vms = [vm for host in cluster_hosts for vm in vms_on_host.get(host.name, [])]
            collect_cluster_performance_metrics(
                cluster_obj, cluster_name,
                [vm.id for vm in cluster_vms], [host.id for host in cluster_hosts],
                suite_api_client,
            )

            hosts_inventory = [
                HostInventory(host.id, host.cores, host.threads, vms_on_host.get(host.name, []))
                for host in cluster_hosts
            ]
            collect_cluster_risk_metrics(cluster_obj, cluster_name, hosts_inventory, suite_api_client)

            # Operational Availability, read once per cycle for the whole vCenter by the adapter.
            publish(cluster_obj, CLUSTER_METRIC, availability.by_cluster.get(cluster_obj.get_key().name))

            result.add_object(cluster_obj)

        except Exception as e:
            logger.warning(f"Skipping Cluster data collection on {cluster_name} due to error: {repr(e)}")
            continue