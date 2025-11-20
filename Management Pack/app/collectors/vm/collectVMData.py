#  Copyright 2024 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from typing import Any
from typing import List
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from pyVmomi import vim
from metrics.vm.vm_snapshot_metrics import collect_vm_metrics
from properties.vm.vmConfig import collect_vm_config_properties
from properties.vm.vm_extra_config import collect_vm_extraconfig_properties
from properties.vm.vmService import collect_vm_service_properties
from properties.vm.vm_scsi_controller_type import collect_vm_scsi_controller_properties
from properties.vm.vmOSInformation import collect_vm_os_information_properties
from events.vm.collect_windows_event_logs import collect_windows_events

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
    container = content.rootFolder
    view_type = [vim.VirtualMachine]
    recursive = True
    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )

    # Retrieve object types from the Aria Operations
    vms: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["VirtualMachine"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )

    # Match the Aria Operations objects with the related identifier
    vms_by_uuid: dict[str, Object] = {
        vm.get_identifier_value("VMEntityObjectID"): vm for vm in vms
    }

    # Push your metrics below
    children = container_view.view

    for vm in children:
        vm_obj = vms_by_uuid.get(vm._moId)
        if vm_obj:
            collect_vm_metrics(vm_obj, vm)
            if vmConfigs:
                collect_vm_config_properties(vm_obj, vm, vmConfigs)
            if vmAdvParameters:
                collect_vm_extraconfig_properties(vm_obj, vm, vmAdvParameters)
            collect_vm_scsi_controller_properties(vm_obj,vm)
            if str(ServiceMonitoringStatus) == "Enabled":
                collect_vm_service_properties(vm_obj, vm, content, winUser, winPassword, windowsServices)
                logger.info(f"Service Monitoring is enabled. VCF Operations vCommunity will start service monitoring. Service Monitoring Status: {ServiceMonitoringStatus}")
                collect_vm_os_information_properties(vm_obj, vm, content, winUser, winPassword)
            else:
                logger.debug(f"Service Monitoring is disabled. Service collection will not started. Service Monitoring Status: {ServiceMonitoringStatus}")
            if str(WindowsEventLogMonitoringStatus) == "Enabled":
                collect_windows_events(vm_obj, vm, content, winUser, winPassword, winEventLogConfigFile)
                logger.info(f"Windows Event Log Monitoring is enabled. VCF Operations vCommunity will start Windows event log monitoring. Windows Event Log Monitoring Status: {WindowsEventLogMonitoringStatus}")
            else:
                logger.debug(f"Windows Event Log Monitoring is disabled. Event log collection will not started. Windows Event Log Monitoring Status: {WindowsEventLogMonitoringStatus}")
            result.add_object(vm_obj)
        else:
            logger.warning(f"Could not find vm '{vm.name}' with MoID: {vm._moId}.")