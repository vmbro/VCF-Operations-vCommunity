#  Copyright 2026 VCF Operations vCommunity Management Pack
"""VM Guest OS KPI.

One 0-100 % score per powered-on VM: the average of its VM Performance and Guest OS Performance.
It replaces the old "vSphere VM Performance" super metric, which mixed both in one formula.

A VM without VMware Tools has no Guest OS Performance. Its VM Guest OS KPI is then its VM Performance alone.
The fallback is done in code, where it is simple and tested, so this is a metric, not a super metric.

Published on the VM as vCommunity|VM Guest OS KPI.
"""
import logging
from typing import Optional
from aria.ops.object import Object

logger = logging.getLogger(__name__)

# The key of the metric, directly in the "vCommunity" group of the VM.
KPI_KEY = "VM Guest OS KPI"


def vm_guest_os_kpi(vm_performance: Optional[float], guest_os_performance: Optional[float]) -> Optional[float]:
    """The average of the two KPIs. VM Performance alone when there is no Guest OS Performance."""
    if vm_performance is None:
        return None
    if guest_os_performance is None:
        return vm_performance
    return round((vm_performance + guest_os_performance) / 2, 2)


def collect_vm_guest_os_kpi(
    vm_obj: Object, vm_name: str, vm_performance: Optional[float], guest_os_performance: Optional[float]
) -> None:
    """Publishes the VM Guest OS KPI, from the two KPIs just published on this VM."""
    try:
        score = vm_guest_os_kpi(vm_performance, guest_os_performance)
        if score is not None:
            vm_obj.with_metric(f"vCommunity|{KPI_KEY}", score)
    except Exception as e:
        # A failure here must not stop the collection of the other VM data.
        logger.warning(f"Failed to publish the VM Guest OS KPI for : {vm_name} - {repr(e)}")
