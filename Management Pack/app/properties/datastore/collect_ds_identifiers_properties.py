#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
from pyVmomi import vim

logger = logging.getLogger(__name__)

def collect_datastore_identifier_properties(datastore_obj, ds_name, prop_dict):
    try:
        naa_ids = []
        datastoreInfo = prop_dict.get("info")
        ds_type = prop_dict.get("summary.type", "Unknown")

        if datastoreInfo and isinstance(datastoreInfo, vim.VmfsDatastoreInfo):
            vmfs_info = getattr(datastoreInfo, "vmfs", None)
            extents = getattr(vmfs_info, "extent", []) if vmfs_info else []

            for extent in extents:
                disk_name = getattr(extent, "diskName", None)
                if disk_name:
                    naa_ids.append(disk_name)

        if not naa_ids:
            datastore_obj.with_property("vCommunity|Identifiers|Number of Extents", str(0))
            logger.debug(f"Datastore {ds_name} is type [{ds_type}] - No Identifier ID found, skipping datastore.")
        else:
            datastore_obj.with_property("vCommunity|Identifiers|Number of Extents", str(len(naa_ids)))
            for index, identifier_id in enumerate(naa_ids, start=1):
                extent_number = str(index)
                datastore_obj.with_property(f"vCommunity|Identifiers|Extent:{extent_number}|ID", str(identifier_id))
            logger.debug(f"Successfully pushed {len(naa_ids)} extent(s) for datastore {ds_name}.")

    except Exception as e:
        logger.warning(f"Failed to retrieve datastore properties for : {ds_name} - {repr(e)}")