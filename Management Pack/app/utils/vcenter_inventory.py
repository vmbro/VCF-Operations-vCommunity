#  Copyright 2026 VCF Operations vCommunity Management Pack
"""DIMM memory of each ESXi host, read from vCenter. The ONE KPI input that still comes from vCenter.

Every other KPI input is read from VCF Operations, see utils/ops_inventory.py. DIMM memory stays here until
the VCF Operations key for host memory without the memory tier (such as NVMe) is decided.
Used by Cluster Risk, for the Memory Monster VM ratio.
"""
from typing import Dict


HOST_MEMORY_PROPERTIES = ["hardware.memorySize"]
# Read in a request of its own: vCenter before 8.0 Update 3 does not have it, and asking for a property
# vCenter does not know makes the whole request fail. Without it, all memory counts as DIMM.
HOST_MEMORY_TIER_PROPERTIES = ["hardware.memoryTierInfo"]


def _props(object_content) -> Dict:
    return {prop.name: prop.val for prop in object_content.propSet}


def dram_bytes(memory_tiers, memory_bytes: float) -> float:
    """DIMM memory of a host. With memory tiering, the DRAM tiers only. Without it, all memory."""
    dram_tiers = [tier.size for tier in (memory_tiers or []) if str(getattr(tier, "type", "")) == "DRAM"]
    return float(sum(dram_tiers)) if dram_tiers else float(memory_bytes)


def host_dram_mb(host_props, memory_tier_props=()) -> Dict[str, float]:
    """{host MoRef id: DIMM memory in MB}.

    host_props has HOST_MEMORY_PROPERTIES, memory_tier_props has HOST_MEMORY_TIER_PROPERTIES (empty if not available).
    """
    tiers_by_host = {data.obj._moId: _props(data).get("hardware.memoryTierInfo") for data in memory_tier_props}
    dram_by_host = {}
    for host_data in host_props:
        memory_bytes = _props(host_data).get("hardware.memorySize")
        if memory_bytes:
            dram = dram_bytes(tiers_by_host.get(host_data.obj._moId), memory_bytes)
            dram_by_host[host_data.obj._moId] = dram / 1024.0 / 1024.0
    return dram_by_host
