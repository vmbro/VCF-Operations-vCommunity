#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Share per vCPU and Share per MB of Memory.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.vm import vm_shares as vs
from utils.ops_inventory import VmInfo
from fakes import FakeObject, FakeSuiteApi

# A 4 vCPU, 16 GB VM at Normal: 1000 CPU shares per vCPU, 10 memory shares per MB.
VM = VmInfo(id="vm-1", name="vm-1", moid="vm-1", host_name="esx-01", powered_on=False, vcpus=4.0, memory_mb=16384.0)
NORMAL = {vs.CPU_SHARES: 4000.0, vs.MEMORY_SHARES: 163840.0}


def test_normal_shares():
    vm = FakeObject("vm-1")
    vs.collect_vm_shares(vm, "vm-1", VM, NORMAL)
    assert vm.metrics == {
        "vCommunity|Configuration|Share per vCPU": 1000.0,
        "vCommunity|Configuration|Share per MB of Memory": 10.0,
    }


def test_same_values_as_the_super_metric():
    # The "Share per GB of Memory" super metric: shares / memoryKB x 1024. It was per MB.
    memory_kb = VM.memory_mb * 1024
    assert vs.per_unit(NORMAL[vs.MEMORY_SHARES], VM.memory_mb) == NORMAL[vs.MEMORY_SHARES] / memory_kb * 1024


def test_no_value_instead_of_a_division_by_zero():
    assert vs.per_unit(4000.0, 0) is None
    assert vs.per_unit(4000.0, None) is None
    assert vs.per_unit(None, 4.0) is None


def test_a_powered_off_vm_gets_its_shares_too():
    vm = FakeObject("vm-1")
    vs.collect_vm_shares(vm, "vm-1", VM._replace(powered_on=False), NORMAL)
    assert len(vm.metrics) == 2


def test_shares_are_read_as_properties_or_as_stats():
    api = FakeSuiteApi(
        properties={"vm-1": {vs.CPU_SHARES: "4000", vs.MEMORY_SHARES: "163840"}},
        samples={"vm-2": {vs.CPU_SHARES: [2000.0], vs.MEMORY_SHARES: [81920.0]}},
    )
    assert vs.read_vm_shares(api, ["vm-1", "vm-2"]) == {
        "vm-1": {vs.CPU_SHARES: 4000.0, vs.MEMORY_SHARES: 163840.0},
        "vm-2": {vs.CPU_SHARES: 2000.0, vs.MEMORY_SHARES: 81920.0},
    }
