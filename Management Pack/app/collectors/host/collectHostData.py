#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven

import logging
from typing import Any
from typing import List
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from pyVmomi import vim
from properties.host.host_advanced_settings import collect_host_properties
from properties.host.host_profile import collect_host_profile_properties
from properties.host.host_software_packages import collect_host_software_properties
from properties.host.host_install_date import collect_host_install_date

logger = logging.getLogger(__name__)

def collect_host_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any,
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

    # Push your metrics below
    children = container_view.view
    for host in children:
        host_obj = hosts_by_uuid.get(host._moId)
        if host_obj:
            collect_host_properties(host_obj, host)
            collect_host_profile_properties(host_obj, host)
            collect_host_software_properties(host_obj, host)
            collect_host_install_date(host_obj, host)
            result.add_object(host_obj)
        else:
            logger.warning(
                f"Could not find host '{host.name}' with MoID: {host._moId}."
            )
