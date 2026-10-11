#  Copyright 2026 VCF Operations vCommunity Management Pack
"""DIMM memory of each host, the one KPI input still read from vCenter.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from utils import vcenter_inventory as inv
from fakes import FakeMoRef

GB = 1024 * 1024 * 1024


def answer(moid, **props):
    """One object of a vCenter property-collector answer."""
    return SimpleNamespace(obj=FakeMoRef(moid), propSet=[SimpleNamespace(name=k, val=v) for k, v in props.items()])


def test_without_memory_tiering_all_memory_is_dimm():
    host = answer("host-1", **{"hardware.memorySize": 512 * GB})
    assert inv.host_dram_mb([host]) == {"host-1": 524288.0}


def test_with_memory_tiering_only_dram_is_dimm():
    # 768 GB of DIMM plus a 768 GB NVMe tier.
    host = answer("host-1", **{"hardware.memorySize": 1536 * GB})
    tiers = answer("host-1", **{"hardware.memoryTierInfo": [
        SimpleNamespace(type="DRAM", size=768 * GB), SimpleNamespace(type="NVMe", size=768 * GB),
    ]})
    assert inv.host_dram_mb([host], [tiers]) == {"host-1": 786432.0}
