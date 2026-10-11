#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from typing import Any
from typing import List
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from pyVmomi import vim
from properties.host.host_advanced_settings import collect_host_properties
from properties.host.host_software_packages import collect_host_software_properties
from properties.host.host_install_date import collect_host_install_date
from properties.host.host_licensing import collect_host_licensing_data
from properties.host.host_uplink import collect_host_uplink
from properties.host.host_configurations import collect_host_configurations
from utils.vi_property_collector import retrieve_properties
from utils.vcenter_inventory import powered_on_vms_by_host, resource_ids
from metrics.host.esxi_performance_metrics import read_esxi_performance_stats, collect_esxi_performance_metrics

logger = logging.getLogger(__name__)

def collect_host_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any,
    esxiAdvSettings,
    esxiVIBDrivers
) -> None:

    # 🔥 PropertyCollector ile sadece gereken propertyleri çek
    propertyPaths: List[str] = []
    propertyPaths.append("runtime.connectionState")
    propertyPaths.append("configManager.imageConfigManager")
    propertyPaths.append("config.network")
    propertyPaths.append("hardware.pciDevice")
    propertyPaths.append("capability.storageVMotionSupported")
    propertyPaths.append("config.dateTimeInfo.timeZone.description")
    propertyPaths.append("config.dateTimeInfo.timeZone.gmtOffset")
    propertyPaths.append("config.dateTimeInfo.timeZone.name")
    propertyPaths.append("hardware.biosInfo.vendor")
    propertyPaths.append("runtime.bootTime")
    propertyPaths.append("config.storageDevice.hostBusAdapter")
    propertyPaths.append("config.option")
    propertyPaths.append("configStatus")
    propertyPaths.append("summary.maxEVCModeKey")
    
    #TODO delete following condition. We will not need this.
    #if esxiAdvSettings:
    #    propertyPaths.append("config.option")

    if esxiVIBDrivers:
        propertyPaths.append("configManager.imageConfigManager")

    # Retrieve object types from the VCF Operations
    hosts: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["HostSystem"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )

    # Match the VCF Operations objects with the related identifier
    hosts_by_uuid: dict[str, Object] = {
        host.get_identifier_value("VMEntityObjectID"): host for host in hosts
    }

    all_assigned_licenses = []
    try:
        assignment_manager = content.licenseManager.licenseAssignmentManager
        all_assigned_licenses = assignment_manager.QueryAssignedLicenses()
    except Exception as e:
        logger.warning(f"Failed to fetch global license assignment data: {repr(e)}")

    
    licenses_by_host_moid = {}
    for lic in all_assigned_licenses:
        entity_id = getattr(lic, "entityId", None)
        if entity_id:
            if entity_id not in licenses_by_host_moid:
                licenses_by_host_moid[entity_id] = []
            licenses_by_host_moid[entity_id].append(lic)

    host_props = retrieve_properties(content, vim.HostSystem, propertyPaths)

    # ESXi Performance: find the powered-on VMs of each host, then read the stats of all of them
    # and the packet counters of all hosts, in bulk, once for all hosts.
    vms: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["VirtualMachine"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )
    vms_by_uuid: dict[str, Object] = {vm.get_identifier_value("VMEntityObjectID"): vm for vm in vms}
    vms_on_host = powered_on_vms_by_host(
        retrieve_properties(content, vim.VirtualMachine, ["runtime.host", "runtime.powerState"])
    )
    vm_ids_by_host = {host_moid: resource_ids(vm_moids, vms_by_uuid) for host_moid, vm_moids in vms_on_host.items()}
    esxi_performance_stats = read_esxi_performance_stats(
        suite_api_client,
        [vm_id for vm_ids in vm_ids_by_host.values() for vm_id in vm_ids],
        [host.get_id() for host in hosts],
    )

    for host_data in host_props:
        try:
            host_ref = host_data.obj
            prop_dict = {p.name: p.val for p in host_data.propSet}
            host_name = prop_dict.get("name", "Unknown")
            connection_state = prop_dict.get("runtime.connectionState")

            host_obj = hosts_by_uuid.get(host_ref._moId)

            if not host_obj or connection_state != "connected":
                logger.debug(f"Skipping data collection for the host '{host_name}'. Connection state: '{connection_state}'")
                continue

            if esxiAdvSettings:
                collect_host_properties(host_obj, host_name, prop_dict, esxiAdvSettings)
            if esxiVIBDrivers:
                collect_host_software_properties(host_obj, host_name, prop_dict, esxiVIBDrivers)
            collect_host_install_date(host_obj, host_name, prop_dict)
            assigned_licenses = licenses_by_host_moid.get(host_ref._moId)
            if assigned_licenses:
                collect_host_licensing_data(host_obj, host_name, assigned_licenses)
            collect_host_uplink(host_obj, host_name, prop_dict)
            collect_host_configurations(host_obj, host_name, prop_dict)
            collect_esxi_performance_metrics(
                host_obj, host_name, vm_ids_by_host.get(host_ref._moId, []), esxi_performance_stats
            )

            result.add_object(host_obj)
            
        except Exception as e:
            logger.warning(f"Skipping ESX data collection on {host_name} due to error: {repr(e)}")
            continue