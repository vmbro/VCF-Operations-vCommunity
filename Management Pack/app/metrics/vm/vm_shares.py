#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Normalized CPU and memory shares of a VM.

    Share per vCPU            CPU shares / vCPUs.             Normal = 1000, Low = 500, High = 2000.
    Share per MB of Memory    memory shares / configured MB.  Normal = 10, Low = 5, High = 20.

Shares grow with the size of the VM, so raw shares cannot be compared between VMs. Per vCPU and per MB
they can: a VM above Normal gets more than its fair part when there is contention, one below gets less.

They replace the "Share per vCPU" and "Share per GB of Memory" super metrics, which had to be enabled by hand.
The memory super metric was in fact per MB (shares / KB x 1024), so it is now named per MB, with the same values.

Published on every VM, powered on or off: shares apply either way. No value when the VM has no vCPU or memory
size, or no shares, instead of a division by zero. All inputs come from VCF Operations.
See docs/vm-shares.md.
"""
import logging
from typing import Dict, List, Optional
from aria.ops.object import Object
from aria.ops.suite_api_client import SuiteApiClient
from utils.ops_inventory import VmInfo
from utils.ops_stats import as_number, read_latest_properties, read_latest_stats

logger = logging.getLogger(__name__)

# Where the metrics are published: the existing "Configuration" group of the VM, next to the share levels.
GROUP = "Configuration"
CPU_METRIC = "Share per vCPU"
MEMORY_METRIC = "Share per MB of Memory"

CPU_SHARES = "config|cpuAllocation|shares|shares"
MEMORY_SHARES = "config|memoryAllocation|shares|shares"
SHARE_KEYS = [CPU_SHARES, MEMORY_SHARES]


def per_unit(shares: Optional[float], units: Optional[float]) -> Optional[float]:
    """shares / units. None when either is missing, or units is 0."""
    if shares is None or not units:
        return None
    return shares / units


def read_vm_shares(suite_api_client: SuiteApiClient, vm_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """{VM id: {share key: shares}}, read in bulk. Read as properties, or as stats when stored as stats."""
    try:
        properties = read_latest_properties(suite_api_client, vm_ids, SHARE_KEYS)
        shares = {
            vm_id: {key: as_number(value) for key, value in values.items() if as_number(value) is not None}
            for vm_id, values in properties.items()
        }
        missing = [vm_id for vm_id in vm_ids if len(shares.get(vm_id, {})) < len(SHARE_KEYS)]
        if missing:
            for vm_id, values in read_latest_stats(suite_api_client, missing, SHARE_KEYS).items():
                shares.setdefault(vm_id, {}).update({key: value for key, value in values.items()
                                                     if key not in shares.get(vm_id, {})})
        return shares
    except Exception as e:
        # Without shares there is no value, but the rest of the VM collection must still run.
        logger.warning(f"Failed to read VM shares, so no Share per vCPU or per MB this cycle - {repr(e)}")
        return {}


def collect_vm_shares(vm_obj: Object, vm_name: str, vm: VmInfo, shares: Dict[str, float]) -> None:
    """Publishes Share per vCPU and Share per MB of Memory. shares is the entry of this VM in read_vm_shares()."""
    try:
        values = {
            CPU_METRIC: per_unit(shares.get(CPU_SHARES), vm.vcpus),
            MEMORY_METRIC: per_unit(shares.get(MEMORY_SHARES), vm.memory_mb),
        }
        for metric, value in values.items():
            if value is not None:
                vm_obj.with_metric(f"vCommunity|{GROUP}|{metric}", round(value, 2))
    except Exception as e:
        logger.warning(f"Failed to publish the VM shares for : {vm_name} - {repr(e)}")
