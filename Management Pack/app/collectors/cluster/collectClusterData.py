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
from utils.vcenter_inventory import (
    VM_PROPERTIES, HOST_PROPERTIES, HOST_MEMORY_TIER_PROPERTIES, powered_on_vms_by_host, vm_sizes, host_hardware, resource_ids, resource_id,
)
from pyVmomi import vim

logger = logging.getLogger(__name__)

def collect_cluster_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any,
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
    propertyPaths.append("host")

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

    # Retrieve HostSystem and VirtualMachine resources for bulk metric lookup
    hosts: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["HostSystem"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )
    hosts_by_uuid: dict[str, Object] = {
        host.get_identifier_value("VMEntityObjectID"): host for host in hosts
    }

    vms: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["VirtualMachine"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )
    vms_by_uuid: dict[str, Object] = {
        vm.get_identifier_value("VMEntityObjectID"): vm for vm in vms
    }

    # Read from vCenter once, for all clusters: the powered-on VMs of each host (a cluster has no list
    # of its VMs), the size of each VM, and the hardware of each host.
    vm_props = retrieve_properties(content, vim.VirtualMachine, VM_PROPERTIES)
    vms_on_host = powered_on_vms_by_host(vm_props)
    sizes_by_vm = vm_sizes(vm_props)
    hardware_by_host = host_hardware(
        retrieve_properties(content, vim.HostSystem, HOST_PROPERTIES),
        retrieve_properties(content, vim.HostSystem, HOST_MEMORY_TIER_PROPERTIES),
    )

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

            host_moids = [host._moId for host in prop_dict.get("host", [])]
            vm_moids = [vm_moid for host_moid in host_moids for vm_moid in vms_on_host.get(host_moid, [])]
            collect_cluster_performance_metrics(
                cluster_obj, cluster_name,
                resource_ids(vm_moids, vms_by_uuid), resource_ids(host_moids, hosts_by_uuid),
                suite_api_client,
            )

            # Cluster Risk: one entry per host that VCF Operations knows about.
            hosts_inventory = [
                HostInventory(
                    resource_id(host_moid, hosts_by_uuid),
                    hardware_by_host.get(host_moid),
                    [sizes_by_vm[vm] for vm in vms_on_host.get(host_moid, []) if vm in sizes_by_vm],
                )
                for host_moid in host_moids if host_moid in hosts_by_uuid
            ]
            collect_cluster_risk_metrics(cluster_obj, cluster_name, hosts_inventory, suite_api_client)

            result.add_object(cluster_obj)

        except Exception as e:
            logger.warning(f"Skipping Cluster data collection on {cluster_name} due to error: {repr(e)}")
            continue