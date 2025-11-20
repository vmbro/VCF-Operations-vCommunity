#  Copyright 2024 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)

def collect_host_software_properties(host_obj, host, esxiVIBDrivers):
    imageConfigManager = host.configManager.imageConfigManager
    if imageConfigManager:
        softwarePackages = imageConfigManager.fetchSoftwarePackages()
        logger.info(f"Image Config Manager found on host '{host.name}' with MoID: {host._moId}. Collecting software packages...")
        for vibName in esxiVIBDrivers:
            for package in softwarePackages:
                if vibName == package.name:
                    host_obj.with_property(f"vCommunity|Configuration|Packages:{package.name}|Package Name", package.name)
                    host_obj.with_property(f"vCommunity|Configuration|Packages:{package.name}|Package Version", package.version)
                    host_obj.with_property(f"vCommunity|Configuration|Packages:{package.name}|Acceptance Level", package.acceptanceLevel)
                    host_obj.with_property(f"vCommunity|Configuration|Packages:{package.name}|Maintenance Mode Required", package.maintenanceModeRequired)
                    host_obj.with_property(f"vCommunity|Configuration|Packages:{package.name}|Package Summary", package.summary)
                    host_obj.with_property(f"vCommunity|Configuration|Packages:{package.name}|Package Type", package.type)
                    host_obj.with_property(f"vCommunity|Configuration|Packages:{package.name}|Package Vendor", package.vendor)
    else:
        logger.debug(f"Could not find Image Config Manager on host '{host.name}' with MoID: {host._moId}.")