[![Blog](https://img.shields.io/badge/vSphere%20vCommunity%20Management%20Pack-157BAD)]([https://github.com/vmbro/VCF-Operations-vCommunity-Content](https://github.com/vmbro/VCF-Operations-vCommunity-Content))
[![MP Version](https://img.shields.io/github/v/release/vmbro/VCF-Operations-vCommunity)](https://badge.fury.io/gh/vmbro%2Fvcf-operations-vcommunity-content)
[![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/vmbro/VCF-Operations-vCommunity/total)]([https://github.com/vmbro/VCF-Operations-vCommunity-Content](https://github.com/vmbro/VCF-Operations-vCommunity-Content))
[![Blog](https://img.shields.io/github/repo-size/vmbro/vcf-operations-vcommunity-content?style=flat)]([https://vmbro.com/](https://github.com/vmbro/VCF-Operations-vCommunity-Content))
[![Blog](https://img.shields.io/github/stars/vmbro/vcf-operations-vcommunity-content?style=flat)]([https://github.com/vmbro/VCF-Operations-vCommunity-Content/stargazers](https://github.com/vmbro/VCF-Operations-vCommunity-Content/stargazers))


# VCF Operations vCommunity Management Pack

This Management Pack was built by Broadcom TAM Onur Yuzseven, using the VCF Operations Integration SDK.  It uses the Python programming language and the VCF Operations API.  It was developed originally for the following use cases:

1.  Capture ESXi Host Advanced System Settings
2.  Capture ESXi Host Software Packages
3.  Capture VM Advanced Paramters
4.  Capture VM Options

The user can customize what is being captured above by editing the assocaited XML files, which are installed with examples by default.

In addition to the four use cases above, this Management Pack also addresses these two use cases:

1.  Captures Windows Services (currently all that are set to Automatic)
2.  Catpures Windows Event Log Events (as configured in windows_event_list.xml)

New Dashboards:
* Critical Business Application 
* vSphere Resource Management 
* VM Storage Configuration 

Enhanced Dashboards:
* VM Configuration
* VM Capacity
* VM Performance
* vSphere Cluster Performance
* vSphere Cluster Capacity
* vSphere Cluster Configuration
* ESXi Configuration
* vSphere Network Configuration

Reports:
Reports were designed to replace all the existing vSphere adapter reports.  There are two types of Reports: PDF and CSV

Super Metrics:
Super Metrics can be found here: https://github.com/vmbro/VCF-Operations-vCommunity/tree/main/Management%20Pack/content/supermetrics.  They must be enabled in Policy's after Management Pack installation.

Additional Properties & Metrics:
- Cluster HA/DRS/EVC
- Virtual Machine Age
- Virtual Machine Snapshot Count
  
