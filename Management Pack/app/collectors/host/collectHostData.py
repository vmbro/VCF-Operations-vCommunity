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
from properties.host.host_advanced_settings import collect_host_properties
from properties.host.host_software_packages import collect_host_software_properties
from properties.host.host_install_date import collect_host_install_date
from properties.host.host_licensing import collect_host_licensing_data
from properties.host.host_uplink import collect_host_uplink

logger = logging.getLogger("collect_host_data")

def collect_host_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any,
    esxiAdvSettings,
    esxiVIBDrivers
) -> None:
    container = content.rootFolder
    view_type = [vim.HostSystem]
    recursive = True
    container_view = content.viewManager.CreateContainerView(
        container, view_type, recursive
    )

    # Retrieve object types from the Aria Operations
    hosts: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["HostSystem"],
            "adapterInstanceId": [adapter_instance_id],
        }
    )

    # Match the Aria Operations objects with the related identifier
    hosts_by_uuid: dict[str, Object] = {
        host.get_identifier_value("VMEntityObjectID"): host for host in hosts
    }

    licenseManager = content.licenseManager
    assignmentManager = licenseManager.licenseAssignmentManager
    
    # Push your metrics below
    children = container_view.view
    for host in children:
            hostConnectionState = host.runtime.connectionState
            host_obj = hosts_by_uuid.get(host._moId)

            if hostConnectionState != "connected":
                 logger.debug(f"Host: '{host.name}' (MoID: {host._moId}) is not processed because connection state is '{hostConnectionState}'. Expected: 'connected'.")
            elif hostConnectionState == "connected" and host_obj:
                logger.info(f"Started data collection on host: '{host.name}' (MoID: {host._moId})")
                assignedLicenses = assignmentManager.QueryAssignedLicenses(host._moId)
                if esxiAdvSettings:
                    collect_host_properties(host_obj, host, esxiAdvSettings)
                if esxiVIBDrivers:
                    collect_host_software_properties(host_obj, host, esxiVIBDrivers)
                collect_host_install_date(host_obj, host)
                collect_host_uplink(host_obj, host)
                if assignedLicenses:
                    collect_host_licensing_data(host_obj, host, assignedLicenses)
                result.add_object(host_obj)
            else:
                logger.warning(f"Could not find host '{host.name}' with MoID: {host._moId} or host is in an unexpected state.")