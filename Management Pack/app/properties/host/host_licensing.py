#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

def collect_host_licensing_data(host_obj, host_name, assigned_licenses):
    try:
        if not assigned_licenses:
            return

        now = datetime.now(timezone.utc)

        for lic in assigned_licenses:
            license_data = getattr(lic, "assignedLicense", None)
            if not license_data:
                continue

            license_name = getattr(license_data, "name", "Unknown")
            license_key = getattr(license_data, "licenseKey", "Unknown")
            edition_key = getattr(license_data, "editionKey", "Unknown")

            expiration_date = None

            for prop in getattr(license_data, "properties", []):
                if prop.key == "expirationDate":
                    expiration_date = prop.value
                    break

            remaining_days = None
            if expiration_date:
                remaining_days = (expiration_date - now).days

            host_obj.with_property(f"vCommunity|Licensing:{license_name}|Name", license_name)
            host_obj.with_property(f"vCommunity|Licensing:{license_name}|License Key", license_key)
            host_obj.with_property(f"vCommunity|Licensing:{license_name}|Edition Key", edition_key)

            if expiration_date:
                host_obj.with_property(f"vCommunity|Licensing:{license_name}|License Expiration Date",str(expiration_date))

            if remaining_days is not None:
                host_obj.with_metric(f"vCommunity|Licensing:{license_name}|Remaining Days", remaining_days)

    except Exception as e:
        logger.warning(f"Failed to retrieve ESX license properties for : {host_name} - {repr(e)}")