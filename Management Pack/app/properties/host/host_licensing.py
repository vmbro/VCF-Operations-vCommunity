#  Copyright 2025 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

def collect_host_licensing_data(host_obj, host, assignedLicenses):
    try:
        for license in assignedLicenses:
            licenseData = license.assignedLicense
            expirationDate = None
            remainingDays = None

            if hasattr(licenseData, "properties") and licenseData.properties:
                for prop in licenseData.properties:
                    if prop.key == "expirationDate":
                        expirationDate = prop.value
                        break

            licenseName = getattr(licenseData, "name", "Unknown")
            licenseKey = getattr(licenseData, "licenseKey", "Unknown")
            licenseEditionKey = getattr(licenseData, "editionKey", "Unknown")

            now = datetime.now(timezone.utc)
            remainingDays = (expirationDate - now).days

            host_obj.with_property(f"vCommunity|Licensing:{licenseName}|Name", licenseName)
            host_obj.with_property(f"vCommunity|Licensing:{licenseName}|License Key", licenseKey)
            host_obj.with_property(f"vCommunity|Licensing:{licenseName}|License Expiration Date", str(expirationDate))
            host_obj.with_metric(f"vCommunity|Licensing:{licenseName}|Remaining Days", remainingDays)
            host_obj.with_property(f"vCommunity|Licensing:{licenseName}|Edition Key", licenseEditionKey)
    except Exception as e:
        message = f"Failed to retrieve licensing info for host '{host.name}' (MoID: {host._moId}): {e}"
        logger.exception(message)