#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Reading who runs where, and how big it is, from vCenter answers.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from utils import vcenter_inventory as inv
from fakes import FakeObject, FakeMoRef


def answer(moid, **props):
    """One object of a vCenter property-collector answer."""
    return SimpleNamespace(obj=FakeMoRef(moid), propSet=[SimpleNamespace(name=k, val=v) for k, v in props.items()])


def vm(moid, host_moid, power_state, vcpus=None, memory_mb=None):
    return answer(moid, **{
        "runtime.host": FakeMoRef(host_moid) if host_moid else None,
        "runtime.powerState": power_state,
        "config.hardware.numCPU": vcpus,
        "config.hardware.memoryMB": memory_mb,
    })


def test_only_powered_on_vms_are_counted_per_host():
    vm_props = [
        vm("vm-1", "host-1", "poweredOn"),
        vm("vm-2", "host-1", "poweredOff"),
        vm("vm-3", "host-2", "poweredOn"),
        vm("vm-4", None, "poweredOn"),        # not on a host
    ]
    assert inv.powered_on_vms_by_host(vm_props) == {"host-1": ["vm-1"], "host-2": ["vm-3"]}


def test_vm_sizes():
    vm_props = [vm("vm-1", "host-1", "poweredOn", 4, 8192), vm("vm-2", "host-1", "poweredOn")]
    assert inv.vm_sizes(vm_props) == {"vm-1": inv.VmSize(4.0, 8192.0)}     # vm-2 has no size


GB = 1024 * 1024 * 1024


def test_host_hardware_converts_memory_to_mb():
    host = answer("host-1", **{"hardware.cpuInfo.numCpuCores": 32, "hardware.memorySize": 512 * GB})
    # No memory tiering: all memory is DIMM.
    assert inv.host_hardware([host]) == {"host-1": inv.HostHardware(32.0, 524288.0, 524288.0)}


def test_with_memory_tiering_only_dram_is_dimm():
    # 768 GB of DIMM plus a 768 GB NVMe tier.
    host = answer("host-1", **{"hardware.cpuInfo.numCpuCores": 64, "hardware.memorySize": 1536 * GB})
    tiers = answer("host-1", **{"hardware.memoryTierInfo": [
        SimpleNamespace(type="DRAM", size=768 * GB), SimpleNamespace(type="NVMe", size=768 * GB),
    ]})
    assert inv.host_hardware([host], [tiers]) == {"host-1": inv.HostHardware(64.0, 1572864.0, 786432.0)}


def test_resource_ids_skip_objects_unknown_to_vcf_operations():
    known = {"vm-1": FakeObject("ops-vm-1")}
    assert inv.resource_ids(["vm-1", "vm-9"], known) == ["ops-vm-1"]
    assert inv.resource_id("vm-1", known) == "ops-vm-1"
    assert inv.resource_id("vm-9", known) is None
