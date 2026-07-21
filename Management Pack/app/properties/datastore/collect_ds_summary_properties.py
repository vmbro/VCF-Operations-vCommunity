#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging
#from pyVmomi import vim

logger = logging.getLogger(__name__)

def collect_datastore_summary_properties(datastore_obj, ds_name, prop_dict, ds_moid):
    try:
        dsStatus = prop_dict.get("overallStatus")
        dsSIOCEnabled = prop_dict.get("iormConfiguration.enabled")
        dsSIOCThreshold = prop_dict.get("iormConfiguration.congestionThreshold")

        dsInfo = prop_dict.get("info")
        vmfsData = getattr(dsInfo, "vmfs", None) if dsInfo else None

        datastore_obj.with_property(f"vCommunity|Summary|MOID", str(ds_moid))

        if vmfsData:
            block_size_mb = getattr(vmfsData, "blockSizeMb", None)
            if block_size_mb is not None:
                datastore_obj.with_property("vCommunity|Summary|Block Size", str(block_size_mb))

            max_blocks = getattr(vmfsData, "maxBlocks", None)
            if max_blocks is not None:
                datastore_obj.with_property("vCommunity|Summary|Max Blocks", str(max_blocks))

            upgradable = getattr(vmfsData, "vmfsUpgradable", None)
            if upgradable is not None:
                datastore_obj.with_property("vCommunity|Summary|VMFS Upgradable", str(upgradable))
            logger.debug(f"Successfully processed VMFS properties for datastore '{ds_name}'")
        else:
            logger.debug(f"Datastore '{ds_name}' is not VMFS (or info.vmfs is empty). Skipping VMFS properties.")

        datastore_obj.with_property("vCommunity|Summary|Status", str(dsStatus))
        datastore_obj.with_property("vCommunity|Summary|SIOC Enabled", str(dsSIOCEnabled))
        datastore_obj.with_property("vCommunity|Summary|SIOC Threshold", str(dsSIOCThreshold))

    except Exception as e:
        logger.warning(f"Failed to retrieve datastore properties for : {ds_name} - {repr(e)}")