#  Copyright 2025 vCommunity MP
#  Author: Scott Bowe scott.bowe@broadcom.com

import logging
from pyVmomi import vim

NULL_STATUS = "null"
logger = logging.getLogger(__name__)

def collect_vm_scsi_controller_properties(vm_obj, vm):
    """
    Emits properties like:
      Config|SCSI Controllers|Count = <int>
      Config|SCSI Controllers|<busNumber>|Type = <friendly type>

    Where <busNumber> is the controller's SCSI bus index (typically 0–3).
    """
    try:
        cfg = getattr(vm, "config", None)
        hw  = getattr(cfg, "hardware", None)
        devices = getattr(hw, "device", []) if hw else []

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

        # TODO: we should remove following block since we are working with instanced metrics.
              # If there is no scsi controller, we don't need to push metric manually.
        # Emit a sentinel when there are no controllers (keeps dashboards happy)
        #if not ctrls:
        #    vm_obj.with_property("vCommunity|Config|SCSI Controllers|0|Type", NULL_STATUS)

    except Exception as e:
        logger.exception(
            f"Failed to collect SCSI controllers for VM '{getattr(vm, 'name', 'unknown')}' "
            f"(MoID: {getattr(vm, '_moId', 'unknown')}): {e}"
        )