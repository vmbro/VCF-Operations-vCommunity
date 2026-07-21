#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Scott Bowe scott.bowe@broadcom.com

import logging

logger = logging.getLogger(__name__)

NULL_STATUS = "null"

def collect_host_configurations(host_obj, host_name, prop_dict):
    try:
        timeZoneName = prop_dict.get("config.dateTimeInfo.timeZone.name")
        timeZoneDescription = prop_dict.get("config.dateTimeInfo.timeZone.description")
        timeZoneGmtOffset = prop_dict.get("config.dateTimeInfo.timeZone.gmtOffset")
        bootTime = prop_dict.get("runtime.bootTime")
        biosVendor = prop_dict.get("hardware.biosInfo.vendor") 
        storageVMotionSupported = prop_dict.get("capability.storageVMotionSupported")
        configStatus = prop_dict.get("configStatus")
        maxEVCModeKey = prop_dict.get("summary.maxEVCModeKey", [])
        network = prop_dict.get("config.network", None)
        dnsConfig = getattr(network, "dnsConfig", None) if network else None
        dhcp = getattr(dnsConfig, "dhcp", NULL_STATUS)
        searchDomain_raw = getattr(dnsConfig, "searchDomain", [])

        if searchDomain_raw and isinstance(searchDomain_raw, (list, tuple)):
            searchDomain = ", ".join([str(d).strip() for d in searchDomain_raw if str(d).strip()])
        else:
            searchDomain = NULL_STATUS
            
        if not searchDomain:
            searchDomain = NULL_STATUS

        advanced_options = prop_dict.get("config.option", [])
        options_map = {opt.key: opt.value for opt in advanced_options if hasattr(opt, "key")}

        atsHeartbeat = str(options_map.get("VMFS3.UseATSForHBOnVMFS5", NULL_STATUS))
        atsLocking   = str(options_map.get("VMFS3.HardwareAcceleratedLocking", NULL_STATUS))

        hbaList = prop_dict.get("config.storageDevice.hostBusAdapter", [])
        hbaCount = 0
        hbaCount = str(len(hbaList)) if hbaList else "0"

        if hbaList is not None and isinstance(hbaList, list) and len(hbaList) > 0:
            for hba in hbaList:
                hba_device = getattr(hba, "device", "unknown_hba")
                
                if not hba_device or hba_device == "null":
                    hba_device = getattr(hba, "key", "unknown_hba").split("-")[-1]

                hba_bus_raw = getattr(hba, "bus", NULL_STATUS)
                hba_bus = str(hba_bus_raw) if hba_bus_raw is not None else NULL_STATUS

                hba_model_raw = getattr(hba, "model", NULL_STATUS)
                hba_model = str(hba_model_raw).strip() if hba_model_raw else NULL_STATUS

                hba_pci_raw = getattr(hba, "pci", NULL_STATUS)
                hba_pci = str(hba_pci_raw).strip() if hba_pci_raw else NULL_STATUS

                hba_status_raw = getattr(hba, "status", NULL_STATUS)
                hba_status = str(hba_status_raw).strip() if hba_status_raw else NULL_STATUS

                hba_protocol_raw = getattr(hba, "storageProtocol", NULL_STATUS)
                hba_protocol = str(hba_protocol_raw).strip() if hba_protocol_raw else NULL_STATUS

                host_obj.with_property(f"vCommunity|Storage Adapter:{hba_device}|Device", hba_device)
                host_obj.with_property(f"vCommunity|Storage Adapter:{hba_device}|Bus", hba_bus)
                host_obj.with_property(f"vCommunity|Storage Adapter:{hba_device}|Model", hba_model)
                host_obj.with_property(f"vCommunity|Storage Adapter:{hba_device}|PCI", hba_pci)
                host_obj.with_property(f"vCommunity|Storage Adapter:{hba_device}|Status", hba_status)
                host_obj.with_property(f"vCommunity|Storage Adapter:{hba_device}|Type", hba_protocol)

        host_obj.with_property("vCommunity|Storage Adapter|Number of HBA", str(hbaCount))
        host_obj.with_property("vCommunity|Configuration|VAAI|ATS Heartbeat", str(atsHeartbeat))
        host_obj.with_property("vCommunity|Configuration|VAAI|ATS Locking", str(atsLocking))
        host_obj.with_property("vCommunity|Configuration|Config Status", str(configStatus))
        host_obj.with_property("vCommunity|Configuration|Max EVC", str(maxEVCModeKey))
        host_obj.with_property("vCommunity|Network|DHCP", str(dhcp))
        host_obj.with_property("vCommunity|Network|Search Domain", str(searchDomain))
        host_obj.with_property("vCommunity|Configuration|Time Zone|Name", str(timeZoneName))
        host_obj.with_property("vCommunity|Configuration|Time Zone|Description", str(timeZoneDescription))
        host_obj.with_property("vCommunity|Configuration|Time Zone|GMT Offset", str(timeZoneGmtOffset))
        host_obj.with_property("vCommunity|Runtime|Boot Time", str(bootTime))
        host_obj.with_property("vCommunity|Hardware|BIOS Vendor", str(biosVendor))
        host_obj.with_property("vCommunity|Capability|Storage vMotion Supported", str(storageVMotionSupported))

        logger.debug(f"Successfully collected all configuration properties for Host {host_name}")

    except Exception as e:
        logger.warning(f"Failed to retrieve ESX configuration properties for : {host_name} - {repr(e)}")