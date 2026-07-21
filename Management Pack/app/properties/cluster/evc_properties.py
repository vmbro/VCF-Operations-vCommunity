#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

NULL_STATUS = "null"
logger = logging.getLogger(__name__)

def collect_evc_properties(cluster_obj, cluster_name, prop_dict):
    try:
        evcEnabledKey = "vCommunity|Cluster Configuration|EVC|Enabled"
        evcModeKey = "vCommunity|Cluster Configuration|EVC|Mode"

        summary_obj = prop_dict.get("summary")

        currentEVCModeValue = None
        if summary_obj:
            currentEVCModeValue = getattr(summary_obj, "currentEVCModeKey", None)

        if currentEVCModeValue:
            cluster_obj.with_property(evcEnabledKey, "True")
            cluster_obj.with_property(evcModeKey, str(currentEVCModeValue))
        else:
            cluster_obj.with_property(evcEnabledKey, "False")
            cluster_obj.with_property(evcModeKey, NULL_STATUS)

        logger.debug(f"Successfully collected vSphere Cluster EVC properties for : {cluster_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve vSphere Cluster EVC properties for : {cluster_name} - {repr(e)}")