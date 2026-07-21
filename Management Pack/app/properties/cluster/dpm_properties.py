#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)

def collect_dpm_properties(cluster_obj, cluster_name, prop_dict):
    try:
        hostPowerActionRate = "vCommunity|Cluster Configuration|DPM|Host Power Action Rate"
        configurationEx = prop_dict.get("configurationEx")

        dpmConfig = getattr(configurationEx, "dpmConfigInfo", None)

        if dpmConfig is not None:
            hostPowerActionRateValue = getattr(dpmConfig, "hostPowerActionRate")
            cluster_obj.with_property(hostPowerActionRate, str(hostPowerActionRateValue))
            logger.debug(f"Successfully collected vSphere Cluster DPM properties for : {cluster_name}")
        else:
            logger.debug(f"Can not find vSphere Cluster DPM properties for : {cluster_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve vSphere Cluster DPM properties for : {cluster_name} - {repr(e)}")