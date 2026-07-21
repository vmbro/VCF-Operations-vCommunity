#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from typing import Any, List
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.suite_api_client import SuiteApiClient
from constants.main import VCENTER_ADAPTER_KIND
from pyVmomi import vim
from utils.vi_property_collector import retrieve_properties
from properties.datastore.collect_ds_identifiers_properties import collect_datastore_identifier_properties
from properties.datastore.collect_ds_summary_properties import collect_datastore_summary_properties

logger = logging.getLogger(__name__)

def collect_datastore_data(
    suite_api_client: SuiteApiClient,
    adapter_instance_id: str,
    result: CollectResult,
    content: Any
) -> None:
    
    propertyPaths: List[str] = []
    propertyPaths.append("summary.type")
    propertyPaths.append("info")
    propertyPaths.append("overallStatus")
    propertyPaths.append("iormConfiguration.enabled")
    propertyPaths.append("iormConfiguration.congestionThreshold")

    ds_props = retrieve_properties(content, vim.Datastore, propertyPaths)
    
    # Retrieve object types from the VCF Operations
    datastores: List[Object] = suite_api_client.query_for_resources(
        {
            "adapterKind": [VCENTER_ADAPTER_KIND],
            "resourceKind": ["Datastore"], 
            "adapterInstanceId": [adapter_instance_id],
        }
    )

    # Match the VCF Operations objects with the related identifier
    datastores_by_moid: dict[str, Object] = {
        ds.get_identifier_value("VMEntityObjectID"): ds for ds in datastores
    }

    for ds_data in ds_props:
        try:
            ds_ref = ds_data.obj
            ds_moid = ds_ref._moId

            datastore_obj = datastores_by_moid.get(ds_moid)
            if not datastore_obj:
                # If datastore object is not available in VCF Operations - skip it.
                continue

            prop_dict = {p.name: p.val for p in ds_data.propSet}
            ds_name = prop_dict.get("name", "Unknown Datastore")

            collect_datastore_identifier_properties(datastore_obj, ds_name, prop_dict)
            collect_datastore_summary_properties(datastore_obj, ds_name, prop_dict, ds_moid)

            result.add_object(datastore_obj)

        except Exception as e:
            logger.warning(f"Skipping Datastore data collection on {ds_name} due to error: {repr(e)}")
            continue