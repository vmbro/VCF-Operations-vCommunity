#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)

NULL_STATUS = "null"

def collect_drs_properties(cluster_obj, cluster_name, prop_dict):
    try:
        proactiveDrsEnabled = "vCommunity|Cluster Configuration|DRS|Proactive DRS"
        scaleDescendantsShares = "vCommunity|Cluster Configuration|DRS|Scale Descendants Shares"
        cpuOverCommitment = "vCommunity|Cluster Configuration|DRS|CPU Over-Commitment"
        enableVmBehaviorOverrides = "vCommunity|Cluster Configuration|DRS|Virtual Machine Automation Enabled"
        cpuOverCommitmentValue = None
        drsEnabled = prop_dict.get("configuration.drsConfig.enabled")
        clusterConfigurationEx = prop_dict.get("configurationEx")
        proactiveDrsConfig = getattr(clusterConfigurationEx, "proactiveDrsConfig")
        proactiveDrsEnabledValue = getattr(proactiveDrsConfig, "enabled")
        enableVmBehaviorOverridesValue = prop_dict.get("configuration.drsConfig.enableVmBehaviorOverrides")
        scaleDescendantsSharesValue = prop_dict.get("configuration.drsConfig.scaleDescendantsShares")
        drsConfig = getattr(clusterConfigurationEx, "drsConfig")
        options = getattr(drsConfig, "option", None)

        if options:
            for opt in options:
                if opt.key == "MaxVcpusPerCore":
                    cpuOverCommitmentValue = int(opt.value)
                    break

        proactive_final = str(proactiveDrsEnabledValue) if (drsEnabled and proactiveDrsEnabledValue is not None) else NULL_STATUS
        scale_shares_final = str(scaleDescendantsSharesValue) if (drsEnabled and scaleDescendantsSharesValue is not None) else NULL_STATUS
        cpuOverCommitment_final = str(cpuOverCommitmentValue) if (drsEnabled and cpuOverCommitmentValue is not None) else NULL_STATUS
        enableVmBehaviorOverridesValue_final = str(enableVmBehaviorOverridesValue) if (drsEnabled and enableVmBehaviorOverridesValue is not None) else NULL_STATUS

        cluster_obj.with_property(proactiveDrsEnabled, str(proactive_final))
        cluster_obj.with_property(scaleDescendantsShares, str(scale_shares_final))
        cluster_obj.with_property(cpuOverCommitment, str(cpuOverCommitment_final))
        cluster_obj.with_property(enableVmBehaviorOverrides, str(enableVmBehaviorOverridesValue_final))

        logger.debug(f"Successfully collected vSphere Cluster DRS properties for : {cluster_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve vSphere Cluster DRS properties for : {cluster_name} - {repr(e)}")