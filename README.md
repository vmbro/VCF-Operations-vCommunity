[![Blog](https://img.shields.io/badge/vSphere%20vCommunity%20Management%20Pack-157BAD)]([https://github.com/vmbro/VCF-Operations-vCommunity-Content](https://github.com/vmbro/VCF-Operations-vCommunity-Content))
[![MP Version](https://img.shields.io/github/v/release/vmbro/VCF-Operations-vCommunity)](https://badge.fury.io/gh/vmbro%2Fvcf-operations-vcommunity-content)
[![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/vmbro/VCF-Operations-vCommunity/total)]([https://github.com/vmbro/VCF-Operations-vCommunity-Content](https://github.com/vmbro/VCF-Operations-vCommunity-Content))
[![Blog](https://img.shields.io/github/repo-size/vmbro/vcf-operations-vcommunity-content?style=flat)]([https://vmbro.com/](https://github.com/vmbro/VCF-Operations-vCommunity-Content))
[![Blog](https://img.shields.io/github/stars/vmbro/vcf-operations-vcommunity-content?style=flat)]([https://github.com/vmbro/VCF-Operations-vCommunity-Content/stargazers](https://github.com/vmbro/VCF-Operations-vCommunity-Content/stargazers))


# VCF Operations vCommunity Management Pack

This Management Pack was built by Broadcom TAM [Onur Yuzseven](https://www.linkedin.com/in/oyuzseven/), using the [VCF Operations Integration SDK](https://github.com/vmware/vmware-aria-operations-integration-sdk).  It uses the Python programming language and the VCF Operations API.  It was developed originally for the following use cases:

1.  Capture ESXi Host Advanced System Settings (esxi_advanced_system_settings.xml)
2.  Capture ESXi Host Software Packages (esxi_packages.xml)
3.  Capture VM Advanced Paramters (vm_advanced_parameters.xml)
4.  Capture VM Options (vm_options.xml)

The user can customize what is being captured above by editing the associated XML files, which are installed with examples by default. For details, see this [blog](https://www.brockpeterson.com/post/vcommunity-management-pack-for-vcf-operations) by [Brock Peterson](https://www.linkedin.com/in/brockpetersonbdcvmw/). 

In addition to the four use cases above, this Management Pack also addresses these two use cases:

1.  Captures Microsoft Windows Services (windows_service_list.xml))
2.  Captures Microsoft Windows Event Log Events (windows_event_list.xml)

The above implementation is _agentless_. It uses GuestAPI with the provided Guest OS credentials. For details, see this [blog](https://www.brockpeterson.com/post/vcommunity-management-pack-for-vcf-operations-part-2). 
As it does not come with a dashboard, [Dale Hassinger](https://www.linkedin.com/in/dalehassinger/) has created a cool dashboard [here](https://www.vcrocs.info/vcommunity-mp-windows-servers-services/). 
Before monitoring hundreds of Windows machine, check the additional load in both VCF Operations and the Windows machine.

New Dashboards:
* Critical Business Application 
* vSphere Resource Management 
* VM Storage Configuration 

Enhanced Dashboards (replacing existing ones):
* VM Configuration
* VM Capacity
* VM Performance
* vSphere Cluster Performance
* vSphere Cluster Capacity
* vSphere Cluster Configuration
* ESXi Configuration
* vSphere Network Configuration

Reports:
Reports were designed to replace all the existing vSphere adapter reports. They were designed top down, as a set.
They are also purpose-built. The PDF format and the CSV format is targetted for their specific use cases.

Super Metrics:
They are used in the dashboards. Super Metrics can be found [here](https://github.com/vmbro/VCF-Operations-vCommunity/tree/main/Management%20Pack/content/supermetrics). You can bulk enable them in Policy, after Management Pack installation.

The above was provided by [Iwan Rahabok](https://www.linkedin.com/in/e1ang/). They are documented in his books, available for download [here](https://broadcom.box.com/v/OpsYourWorld). 

Additional Properties & Metrics:
- Cluster HA/DRS/EVC
- Virtual Machine Snapshot Count
  
