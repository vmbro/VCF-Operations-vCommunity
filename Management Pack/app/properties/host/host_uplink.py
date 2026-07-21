#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import logging

logger = logging.getLogger(__name__)


def collect_host_uplink(host_obj, host_name, prop_dict):
    try:
        network = prop_dict.get("config.network", None)
        pnics = getattr(network, "pnic", None) if network else None
        pciDevices = prop_dict.get("hardware.pciDevice", None)

        if not pnics:
            logger.debug(f"No physical NICs found on {host_name}.")
            return

        logger.debug(f"Collecting physical NIC information for host {host_name}.")

        pciMap = {}
        if pciDevices:
            pciMap = {
                getattr(dev, "id", None): dev
                for dev in pciDevices
                if getattr(dev, "id", None)
            }

        for pnic in pnics:
            device = getattr(pnic, "device", "N/A")
            driverVersion = getattr(pnic, "driverVersion", "N/A")
            firmwareVersion = getattr(pnic, "firmwareVersion", "N/A")
            vmnicStatus = ("Connected" if getattr(pnic, "linkSpeed", None) else "Disconnected")

            pci_id = getattr(pnic, "pci", None)
            pci_dev = pciMap.get(pci_id) if pci_id else None
            vendorName = getattr(pci_dev, "vendorName", "N/A") if pci_dev else "N/A"
            deviceName = getattr(pci_dev, "deviceName", "N/A") if pci_dev else "N/A"

            vid = (
                f"{pci_dev.vendorId:04x}"
                if pci_dev and getattr(pci_dev, "vendorId", None) is not None
                else "N/A"
            )

            did = (
                f"{pci_dev.deviceId:04x}"
                if pci_dev and getattr(pci_dev, "deviceId", None) is not None
                else "N/A"
            )

            svid = (
                f"{pci_dev.subVendorId:04x}"
                if pci_dev and getattr(pci_dev, "subVendorId", None) is not None
                else "N/A"
            )

            macAddress = getattr(pnic, "mac", "N/A")
            wakeOnLanSupported = getattr(pnic, "wakeOnLanSupported", "N/A")
            pci = getattr(pnic, "pci", "N/A")
            linkSpeed = getattr(pnic, "linkSpeed", None)
            duplex = "full-duplex" if linkSpeed and getattr(linkSpeed, "duplex", None) else "half-duplex"
        
            # --- vmhba properties ---
            host_obj.with_property(f"vCommunity|Network|Device:{device}|Device Name", device)
            host_obj.with_property(f"vCommunity|Network|Device:{device}|Driver Version", driverVersion)
            host_obj.with_property(f"vCommunity|Network|Device:{device}|Firmware Version", firmwareVersion)
            host_obj.with_property(f"vCommunity|Network|Device:{device}|Status", vmnicStatus)

            # --- PCI Device Properties ---
            host_obj.with_property(f"vCommunity|Network|Device:{device}|PCI Vendor Name", vendorName)
            host_obj.with_property(f"vCommunity|Network|Device:{device}|PCI Device Name", deviceName)
            host_obj.with_property(f"vCommunity|Network|Device:{device}|PCI Vendor ID (VID)", vid)
            host_obj.with_property(f"vCommunity|Network|Device:{device}|PCI Device ID (DID)", did)
            host_obj.with_property(f"vCommunity|Network|Device:{device}|PCI SubVendor ID (SVID)", svid)

            host_obj.with_property(f"vCommunity|Network|Device:{device}|MAC", str(macAddress))
            host_obj.with_property(f"vCommunity|Network|Device:{device}|Wake On Lan Supported", str(wakeOnLanSupported))
            host_obj.with_property(f"vCommunity|Network|Device:{device}|PCI", str(pci))
            host_obj.with_property(f"vCommunity|Network|Device:{device}|Duplex", str(duplex))


            logger.debug(
                f"host {host_name} [{device}] Driver={driverVersion}, Firmware={firmwareVersion}, "
                f"Status={vmnicStatus}, Vendor={vendorName}, Device={deviceName}, "
                f"VID={vid}, DID={did}, SVID={svid}"
            )

    except Exception as e:
        logger.warning(f"Failed to retrieve ESX NIC configuration properties for : {host_name} - {repr(e)}")