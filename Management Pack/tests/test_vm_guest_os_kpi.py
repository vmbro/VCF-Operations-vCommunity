#  Copyright 2026 VCF Operations vCommunity Management Pack
"""VM Guest OS KPI: the average of VM Performance and Guest OS Performance.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from metrics.vm import vm_guest_os_kpi as vg
from fakes import FakeObject


def test_the_kpi_is_the_average_of_both():
    assert vg.vm_guest_os_kpi(80.0, 61.0) == 70.5


def test_without_guest_os_performance_it_is_vm_performance_alone():
    # A VM without VMware Tools has no Guest OS Performance.
    assert vg.vm_guest_os_kpi(19.94, None) == 19.94


def test_without_vm_performance_there_is_no_kpi():
    assert vg.vm_guest_os_kpi(None, 61.19) is None
    assert vg.vm_guest_os_kpi(None, None) is None


def test_it_is_published_in_the_vcommunity_group():
    vm = FakeObject("vm-1")
    vg.collect_vm_guest_os_kpi(vm, "vm-1", 80.0, 60.0)
    assert vm.metrics == {"vCommunity|VM Guest OS KPI": 70.0}


def test_nothing_is_published_without_vm_performance():
    vm = FakeObject("vm-1")
    vg.collect_vm_guest_os_kpi(vm, "vm-1", None, 60.0)
    assert vm.metrics == {}
