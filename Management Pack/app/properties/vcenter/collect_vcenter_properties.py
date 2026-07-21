#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)

NULL_STATUS = "null"
def collect_vcenter_properties(vcenter_obj, vc_name, settings_dict):
    try:
        userDirectoryTimeout = "vCommunity|Configuration|User Directory Timeout"
        enableMOB = "vCommunity|Configuration|Enable MOB"
        eventMaxAge = "vCommunity|Configuration|Database|Event retention (days)"
        eventMaxAgeEnabled = "vCommunity|Configuration|Database|Event Cleanup Enabled"
        taskMaxAge = "vCommunity|Configuration|Database|Task retention (days)"
        taskMaxAgeEnabled = "vCommunity|Configuration|Database|Task Cleanup Enabled"
        vcInstanceId = "vCommunity|Configuration|Runtime|vCenter Unique ID"
        vcManagedIP = "vCommunity|Configuration|Runtime|vCenter managed address"
        vcMaxDBConnection = "vCommunity|Configuration|Database|Maximum Connections"
        logLevel = "vCommunity|Configuration|Log Level"
        
        userDirectoryTimeoutValue = str(settings_dict.get("ads.timeout", NULL_STATUS))
        enableMOBValue = str(settings_dict.get("config.vpxd.enableDebugBrowse", NULL_STATUS))
        eventMaxAgeValue = str(settings_dict.get("event.maxAge", NULL_STATUS))
        eventMaxAgeEnabledValue  = str(settings_dict.get("event.maxAgeEnabled", NULL_STATUS))
        taskMaxAgeValue = str(settings_dict.get("task.maxAge", NULL_STATUS))
        taskMaxAgeEnabledValue = str(settings_dict.get("task.maxAgeEnabled", NULL_STATUS))
        vcInstanceIdValue = str(settings_dict.get("instance.id", NULL_STATUS))
        vcManagedIPValue = str(settings_dict.get("VirtualCenter.ManagedIP", NULL_STATUS))
        vcMaxDBConnectionValue = str(settings_dict.get("VirtualCenter.MaxDBConnection", NULL_STATUS))
        logLevelValue = str(settings_dict.get("log.level", NULL_STATUS))

        vcenter_obj.with_property(userDirectoryTimeout, userDirectoryTimeoutValue)
        vcenter_obj.with_property(enableMOB, enableMOBValue)
        vcenter_obj.with_property(eventMaxAge, eventMaxAgeValue)
        vcenter_obj.with_property(eventMaxAgeEnabled, eventMaxAgeEnabledValue)
        vcenter_obj.with_property(taskMaxAge, taskMaxAgeValue)
        vcenter_obj.with_property(taskMaxAgeEnabled, taskMaxAgeEnabledValue)
        vcenter_obj.with_property(vcInstanceId, vcInstanceIdValue)
        vcenter_obj.with_property(vcManagedIP, vcManagedIPValue)
        vcenter_obj.with_property(vcMaxDBConnection, vcMaxDBConnectionValue)
        vcenter_obj.with_property(logLevel, logLevelValue)

        logger.debug(f"Successfully pushed vCenter settings for vCenter: {vc_name}")

    except Exception as e:
        logger.debug(f"Failed to retrieve vCenter settings for {vc_name}: {repr(e)}")