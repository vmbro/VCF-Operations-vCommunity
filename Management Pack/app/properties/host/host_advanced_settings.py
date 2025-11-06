#  Copyright 2024 vCommunity Content MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
import os
import yaml

logger = logging.getLogger(__name__)

#current_directory = os.path.dirname(os.path.abspath(__file__))
#esxHostAdvSettings = os.path.join(current_directory, "../../constants/host/hostAdvancedSettings.yaml")

def collect_host_properties(host_obj, host, esxiAdvSettings):

    advancedSettingsDict = {
        advKey.key: advKey.value
        for advKey in host.configManager.advancedOption.setting
    }

    commonKeys = [key for key in esxiAdvSettings if key in advancedSettingsDict]

    for advSettingsKey in commonKeys:
        advSettingsValue = advancedSettingsDict[advSettingsKey]
        #host_obj.with_property(f"vCommunity|Configuration|Advanced System Settings|{'|'.join(advSettingsKey.split('.'))}", advSettingsValue)
        host_obj.with_property(f"vCommunity|Configuration|Advanced System Settings|{advSettingsKey}", advSettingsValue)

    #with open(esxHostAdvSettings, "r") as file:
    #    data = yaml.safe_load(file)
    #advancedKeys = data.get("advancedSettings", [])
    #advancedSettingsDict = {advKey.key: advKey.value for advKey in host.configManager.advancedOption.setting}
    #commonKeys = [key for key in advancedKeys if key in advancedSettingsDict]
    #for advSettingsKey in commonKeys:
    #    advSettingsValue = advancedSettingsDict[advSettingsKey]
    #    host_obj.with_property(f"Config|Host Agent|{'|'.join(advSettingsKey.split('.'))}", advSettingsValue)