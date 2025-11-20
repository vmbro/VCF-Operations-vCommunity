#  Copyright 2024 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)


def collect_host_properties(host_obj, host, esxiAdvSettings):

    advancedSettingsDict = {
        advKey.key: advKey.value
        for advKey in host.configManager.advancedOption.setting
    }

    commonKeys = [key for key in esxiAdvSettings if key in advancedSettingsDict]

    for advSettingsKey in commonKeys:
        advSettingsValue = advancedSettingsDict[advSettingsKey]
        host_obj.with_property(f"vCommunity|Configuration|Advanced System Settings|{advSettingsKey}", advSettingsValue)