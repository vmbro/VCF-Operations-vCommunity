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
from properties.vm.vmConfig import collect_vm_config_properties
from properties.vm.vm_extra_config import collect_vm_extraconfig_properties
from properties.vm.vmService import collect_vm_service_properties
from properties.vm.vm_disk import collect_vm_disk
from properties.vm.vm_configurations import collect_vm_configurations
from properties.vm.vmOSInformation import collect_vm_os_information_properties
from events.vm.collect_windows_event_logs import collect_windows_events
from utils.vi_property_collector import retrieve_properties
from pyVmomi import vim

logger = logging.getLogger(__name__)

def collect_vm_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any,
    ServiceMonitoringStatus,
    WindowsEventLogMonitoringStatus,
    winUser,
    winPassword,
    winEventLogConfigFile,
    vmConfigs,
    vmAdvParameters,
    windowsServices
) -> None:
    
    propertyPaths: List[str] = []

    if vmConfigs:
        propertyPaths.extend(vmConfigs)

    if vmAdvParameters:
        propertyPaths.append("config.extraConfig")

    propertyPaths.append("config.hardware.device")

    ### VM Default Configurations
    propertyPaths.append("config.bootOptions.bootDelay")
    propertyPaths.append("config.bootOptions.bootRetryDelay")
    propertyPaths.append("config.bootOptions.bootRetryEnabled")
    propertyPaths.append("config.bootOptions.enterBIOSSetup")
    propertyPaths.append("config.changeVersion")
    propertyPaths.append("config.firmware")
    propertyPaths.append("config.flags.diskUuidEnabled")
    propertyPaths.append("config.latencySensitivity.level")
    propertyPaths.append("config.rebootPowerOff")
    propertyPaths.append("config.scheduledHardwareUpgradeInfo.scheduledHardwareUpgradeStatus")
    propertyPaths.append("config.scheduledHardwareUpgradeInfo.upgradePolicy")
    propertyPaths.append("config.scheduledHardwareUpgradeInfo.versionKey")
    propertyPaths.append("config.vmOpNotificationTimeout")
    propertyPaths.append("guest.guestState")
    propertyPaths.append("runtime.consolidationNeeded")
    propertyPaths.append("runtime.dasVmProtection.dasProtected")
    propertyPaths.append("runtime.minRequiredEVCModeKey")
    propertyPaths.append("config.tools.syncTimeWithHost")
    propertyPaths.append("config.tools.toolsUpgradePolicy")
    propertyPaths.append("guest.appState")
    propertyPaths.append("guest.guestKernelCrashed")
    propertyPaths.append("guest.guestOperationsReady")
    propertyPaths.append("guest.guestStateChangeSupported")
    propertyPaths.append("guest.interactiveGuestOperationsReady")
    propertyPaths.append("config.numaInfo.vnumaOnCpuHotaddExposed")
    propertyPaths.append("config.cpuAllocation.shares.level")
    propertyPaths.append("configStatus")
    propertyPaths.append("guest.customizationInfo.customizationStatus")
    propertyPaths.append("summary.quickStats.guestHeartbeatStatus")
    propertyPaths.append("summary.config.vmPathName")
    propertyPaths.append("config.memoryAllocation.shares.level")
    propertyPaths.append("guest")

    vm_props = retrieve_properties(content, vim.VirtualMachine, propertyPaths)

    # Retrieve object types from the VCF Operations
    vms: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["VirtualMachine"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )

    # Match the VCF Operations objects with the related identifier
    vms_by_uuid: dict[str, Object] = {
        vm.get_identifier_value("VMEntityObjectID"): vm for vm in vms
    }

    for vm_data in vm_props:
        try:
            vm_ref = vm_data.obj
            vm_moid = vm_ref._moId

            vm_obj = vms_by_uuid.get(vm_moid)
            if not vm_obj:
                continue

            prop_dict = {p.name: p.val for p in vm_data.propSet}
            vm_name = prop_dict.get("name", "Unknown")

            if vmConfigs:
                collect_vm_config_properties(vm_obj, vm_name, prop_dict, vmConfigs)
                
            if vmAdvParameters:
                collect_vm_extraconfig_properties(vm_obj, vm_name, prop_dict, vmAdvParameters)
                
            collect_vm_disk(vm_obj, prop_dict, vm_name)
            collect_vm_configurations(vm_obj, prop_dict, vm_name)


            # TODO need to improve data collection 
            # a logic need that we can only collect data for vms from the config file

            # --- Guest OS Monitoring ---
            if ServiceMonitoringStatus == "Enabled":
                collect_vm_service_properties(vm_obj, vm_ref, content, winUser, winPassword, windowsServices)
                collect_vm_os_information_properties(vm_obj, vm_ref, content, winUser, winPassword)

            # --- Windows Event Log Monitoring ---
            if WindowsEventLogMonitoringStatus == "Enabled":
                collect_windows_events(vm_obj, vm_ref, content, winUser, winPassword, winEventLogConfigFile)

            result.add_object(vm_obj)

        except Exception as e:
            logger.warning(f"Skipping VM data collection on {vm_name} due to error: {repr(e)}")
            continue