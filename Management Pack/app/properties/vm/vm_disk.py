#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Scott Bowe scott.bowe@broadcom.com

import logging
from pyVmomi import vim

logger = logging.getLogger(__name__)

def collect_vm_disk(vm_obj, prop_dict, vm_name):
    try:
        devices = prop_dict.get("config.hardware.device")
        if not devices:
            vm_obj.with_metric("vCommunity|Configuration|SCSI Controllers|Count", 0)
            return

        ctrls = [d for d in devices if isinstance(d, vim.vm.device.VirtualSCSIController)]
        
        vm_obj.with_metric("vCommunity|Configuration|SCSI Controllers|Count", len(ctrls))

        def pretty_type(ctrl):
            if isinstance(ctrl, vim.vm.device.ParaVirtualSCSIController):
                return "VMware Paravirtual (PVSCSI)"
            if isinstance(ctrl, vim.vm.device.VirtualLsiLogicSASController):
                return "LSI Logic SAS"
            if isinstance(ctrl, vim.vm.device.VirtualLsiLogicController):
                return "LSI Logic Parallel"
            if isinstance(ctrl, vim.vm.device.VirtualBusLogicController):
                return "BusLogic"
            return type(ctrl).__name__

        for c in ctrls:
            bus = getattr(c, "busNumber", None)
            bus_str = str(bus) if bus is not None else "unknown"
            vm_obj.with_property(f"vCommunity|Configuration|SCSI Controllers:{bus_str}|Type", pretty_type(c))
            
        if ctrls:
            logger.debug(f"VM SCSI controller properties for VM '{vm_name}': {len(ctrls)} controllers found.")
            
        ## new code-block for network card props
        vnics = [d for d in devices if isinstance(d, vim.vm.device.VirtualEthernetCard)]
        if not vnics:
            logger.debug(f"No network adapters found on VM '{vm_name}'.")
            return
        
        for vnic in vnics:
            deviceInfo = getattr(vnic, "deviceInfo", None)
            vnicLabel = getattr(deviceInfo, "label", "Unknown Adapter").strip() if deviceInfo else "Unknown Adapter"
            addressType = getattr(vnic, "addressType", "null")

            connectable = getattr(vnic, "connectable", None)
            startConnected = getattr(connectable, "startConnected", None) if connectable else "null"

            vm_obj.with_property(f"vCommunity|Network|Network Adapters:{vnicLabel}|Type", str(addressType))
            vm_obj.with_property(f"vCommunity|Network|Network Adapters:{vnicLabel}|Starts Connected", str(startConnected))


        vdisks = [d for d in devices if isinstance(d, vim.vm.device.VirtualDisk)]

        if not vdisks:
            logger.debug(f"No virtual disk found on VM '{vm_name}'.")
            return
        
        for vdisk in vdisks:
            vdiskDeviceInfo = getattr(vdisk, "deviceInfo", "unknownDisk")
            vdiskLabel = getattr(vdiskDeviceInfo, "label", "unknown") if vdiskDeviceInfo else "Unknown"
            vdiskkey = getattr(vdisk, "key", "UnknownKey")
            vdiskcontrollerKey = getattr(vdisk, "controllerKey", "UnknownKey")
            vdiskbacking = getattr(vdisk, "backing", None)
            backingEagerlyScrub = getattr(vdiskbacking, "eagerlyScrub", None) if vdiskbacking else "Unknown"
            backingSplit = getattr(vdiskbacking, "split", None) if vdiskbacking else "Unknown"
            backingWriteThrough = getattr(vdiskbacking, "writeThrough", None) if vdiskbacking else "Unknown"
            vdiskShares = getattr(vdisk, "shares", None)
            vdiskShareLevel = getattr(vdiskShares, "level", None) if vdiskShares else "Unknown"

            vm_obj.with_property(f"vCommunity|Virtual Disk:{vdiskLabel}|Label", str(vdiskLabel))
            vm_obj.with_property(f"vCommunity|Virtual Disk:{vdiskLabel}|Key", str(vdiskkey))
            vm_obj.with_property(f"vCommunity|Virtual Disk:{vdiskLabel}|Controller Key", str(vdiskcontrollerKey))
            vm_obj.with_property(f"vCommunity|Virtual Disk:{vdiskLabel}|Eagerly Scrub", str(backingEagerlyScrub))
            vm_obj.with_property(f"vCommunity|Virtual Disk:{vdiskLabel}|Split", str(backingSplit))
            vm_obj.with_property(f"vCommunity|Virtual Disk:{vdiskLabel}|Write Through", str(backingWriteThrough))
            vm_obj.with_property(f"vCommunity|Virtual Disk:{vdiskLabel}|Storage Allocation Share Level", str(vdiskShareLevel))
    
    except Exception as e:
        logger.warning(f"Failed to retrieve VM virtual disk properties for : {vm_name} - {repr(e)}")