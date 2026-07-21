#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from typing import Any, List
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from pyVmomi import vim
from properties.vcenter.collect_vcenter_properties import collect_vcenter_properties

logger = logging.getLogger(__name__)

def collect_vcenter_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any
) -> None:
    try:
        about_info = getattr(content, "about", None)
        
        if about_info is None:
            logger.debug("vCenter about info is None. Skipping data collection for vCenter object.")
            return

        vcenter_uuid = getattr(about_info, "instanceUuid", None)
        if not vcenter_uuid:
            logger.debug("vCenter instanceUuid not found in the vSphere API. Skipping data collection.")
            return

        # Retrieve object types from the VCF Operations
        vcenters: List[Object] = suite_api_client.query_for_resources(
            {
                "adapterKind": [VCENTER_ADAPTER_KIND],
                "resourceKind": ["VMwareAdapter Instance"],
                "adapterInstanceId": [adapter_instance_id],
            }
        )

        vcenter_obj = None
        for vc in vcenters:
            vc_vcid = vc.get_identifier_value("VMEntityVCID")
            if vc_vcid == vcenter_uuid:
                vcenter_obj = vc
                patchLevelValue = getattr(about_info, "patchLevel", "Unknown")
                vcenter_obj.with_property("vCommunity|Configuration|Patch Level", str(patchLevelValue))
                break

        if not vcenter_obj:
            logger.debug("Can not find the vCenter object in the VCF Operations. Skipping vCenter data collection.")
            return

        vc_name = "vCenter Server"
        try:
            vc_json = vcenter_obj.get_json()
            vc_name = vc_json.get("key").get("name")
        except Exception as json_err:
            logger.debug(f"Failed to parse name from JSON: {repr(json_err)}")

        option_manager = getattr(content, "setting", None)
        
        settings_dict = {}
        if option_manager is not None:
            target_keys = [
                "ads.timeout",
                "config.vpxd.enableDebugBrowse",
                "event.maxAge",
                "event.maxAgeEnabled",
                "instance.id",
                "log.level",
                "task.maxAge",
                "task.maxAgeEnabled",
                "VirtualCenter.ManagedIP",
                "VirtualCenter.MaxDBConnection",
            ]

            for key in target_keys:
                try:
                    retrieved_option = option_manager.QueryOptions(name=key)
                    if retrieved_option and len(retrieved_option) > 0:
                        val = retrieved_option[0].value
                        if val is None or (isinstance(val, str) and not val.strip()) or val == "":
                            settings_dict[key] = "null"
                        else:
                            settings_dict[key] = val
                    else:
                        settings_dict[key] = "null"
                        
                except Exception as single_key_err:
                    settings_dict[key] = "null"
                    logger.debug(f"Can not found the vCenter property '{key}' on the {vc_name}. Error: {repr(single_key_err)}")

        if settings_dict:
            collect_vcenter_properties(vcenter_obj, vc_name, settings_dict)

        result.add_object(vcenter_obj)

    except Exception as e:
        logger.warning(f"Skipping vCenter data collection on due to error: {repr(e)}")