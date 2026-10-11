#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Who runs where, and how big it is: read from vCenter, for the KPIs.

The KPIs that score a host or a cluster need to know which VMs run on each host,
how big those VMs are, and how big each host is. vCenter knows this directly,
so it is read once per collection cycle with the property collector, for all
objects at once.
"""
from typing import Dict, List, NamedTuple, Optional


# vCenter properties to read for every VM, and for every host.
VM_PROPERTIES = ["runtime.host", "runtime.powerState", "config.hardware.numCPU", "config.hardware.memoryMB"]
HOST_PROPERTIES = ["hardware.cpuInfo.numCpuCores", "hardware.memorySize"]
# Read in a request of its own: vCenter before 8.0 Update 3 does not have it, and asking for a property
# vCenter does not know makes the whole request fail. Without it, all memory counts as DIMM.
HOST_MEMORY_TIER_PROPERTIES = ["hardware.memoryTierInfo"]


class VmSize(NamedTuple):
    vcpus: float
    memory_mb: float


class HostHardware(NamedTuple):
    cores: float            # physical cores, all sockets together. Not threads.
    memory_mb: float        # all memory, including a memory tier such as NVMe
    dram_mb: float          # DIMM memory only. The same as memory_mb on a host without memory tiering.


def _props(object_content) -> Dict:
    return {prop.name: prop.val for prop in object_content.propSet}


def powered_on_vms_by_host(vm_props) -> Dict[str, List[str]]:
    """{host MoRef id: [MoRef ids of the powered-on VMs on that host]}.

    vm_props is the vCenter answer for every VM, with at least runtime.host and runtime.powerState.
    A powered-off VM is left out: its last stats in VCF Operations are old and would skew a KPI.
    """
    vms_by_host = {}
    for vm_data in vm_props:
        props = _props(vm_data)
        host = props.get("runtime.host")
        if host is None or props.get("runtime.powerState") != "poweredOn":
            continue
        vms_by_host.setdefault(host._moId, []).append(vm_data.obj._moId)
    return vms_by_host


def vm_sizes(vm_props) -> Dict[str, VmSize]:
    """{VM MoRef id: its configured vCPUs and memory}. VMs without both values are left out."""
    sizes = {}
    for vm_data in vm_props:
        props = _props(vm_data)
        vcpus = props.get("config.hardware.numCPU")
        memory_mb = props.get("config.hardware.memoryMB")
        if vcpus and memory_mb:
            sizes[vm_data.obj._moId] = VmSize(float(vcpus), float(memory_mb))
    return sizes


def dram_bytes(memory_tiers, memory_bytes: float) -> float:
    """DIMM memory of a host. With memory tiering, the DRAM tiers only. Without it, all memory."""
    dram_tiers = [tier.size for tier in (memory_tiers or []) if str(getattr(tier, "type", "")) == "DRAM"]
    return float(sum(dram_tiers)) if dram_tiers else float(memory_bytes)


def host_hardware(host_props, memory_tier_props=()) -> Dict[str, HostHardware]:
    """{host MoRef id: its cores and memory}. Hosts without cores or memory are left out.

    host_props has HOST_PROPERTIES, memory_tier_props has HOST_MEMORY_TIER_PROPERTIES (empty if not available).
    """
    tiers_by_host = {data.obj._moId: _props(data).get("hardware.memoryTierInfo") for data in memory_tier_props}
    hardware = {}
    for host_data in host_props:
        props = _props(host_data)
        cores = props.get("hardware.cpuInfo.numCpuCores")
        memory_bytes = props.get("hardware.memorySize")
        if cores and memory_bytes:
            dram = dram_bytes(tiers_by_host.get(host_data.obj._moId), memory_bytes)
            hardware[host_data.obj._moId] = HostHardware(float(cores), _mb(memory_bytes), _mb(dram))
    return hardware


def _mb(size_bytes: float) -> float:
    return size_bytes / 1024.0 / 1024.0


def resource_ids(moids: List[str], objects_by_moid: Dict) -> List[str]:
    """VCF Operations resource ids of the vCenter objects (VMs or hosts) that VCF Operations knows about."""
    # vCenter names an object by its MoRef id. VCF Operations uses its own id, which the stats API needs.
    return [objects_by_moid[moid].get_id() for moid in moids if moid in objects_by_moid]


def resource_id(moid: str, objects_by_moid: Dict) -> Optional[str]:
    """VCF Operations resource id of one vCenter object, or None when VCF Operations does not know it."""
    obj = objects_by_moid.get(moid)
    return obj.get_id() if obj else None
