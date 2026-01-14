#  Copyright 2026 vCommunity MP
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)

def collect_host_uplink(host_obj, host):
    pnics = host.config.network.pnic
    try:
        if not pnics:
            logger.info(f"No physical NICs found on '{host.name}' with MoID: {host._moId}.")
        else:
            logger.info(f"Collecting physical NIC information for host '{host.name}' with MoID: {host._moId}.")
            for pnic in pnics:
                device = pnic.device if getattr(pnic, 'device') else 'N/A'
                driverVersion = pnic.driverVersion if getattr(pnic, 'driverVersion') else 'N/A'
                firmwareVersion = pnic.firmwareVersion if getattr(pnic, 'firmwareVersion') else 'N/A'
                vmnicStatus = "Connected" if pnic.linkSpeed else "Disconnected"
                host_obj.with_property(f"vCommunity|Network|Device:{device}|Device Name", device)
                host_obj.with_property(f"vCommunity|Network|Device:{device}|Driver Version", driverVersion)
                host_obj.with_property(f"vCommunity|Network|Device:{device}|Firmware Version", firmwareVersion)
                host_obj.with_property(f"vCommunity|Network|Device:{device}|Status", vmnicStatus)
    except Exception as e:
        logger.debug(f"Failed to retrieve physical NIC information on '{host.name}' with MoID: {host._moId}.")