[![Blog](https://img.shields.io/badge/vSphere%20vCommunity%20Management%20Pack-157BAD)]([https://github.com/vmbro/VCF-Operations-vCommunity-Content](https://github.com/vmbro/VCF-Operations-vCommunity-Content))
[![MP Version](https://img.shields.io/github/v/release/vmbro/VCF-Operations-vCommunity)](https://badge.fury.io/gh/vmbro%2Fvcf-operations-vcommunity-content)
[![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/vmbro/VCF-Operations-vCommunity/total)]([https://github.com/vmbro/VCF-Operations-vCommunity-Content](https://github.com/vmbro/VCF-Operations-vCommunity-Content))
[![Blog](https://img.shields.io/github/repo-size/vmbro/vcf-operations-vcommunity-content?style=flat)]([https://vmbro.com/](https://github.com/vmbro/VCF-Operations-vCommunity-Content))
[![Blog](https://img.shields.io/github/stars/vmbro/vcf-operations-vcommunity-content?style=flat)]([https://github.com/vmbro/VCF-Operations-vCommunity-Content/stargazers](https://github.com/vmbro/VCF-Operations-vCommunity-Content/stargazers))




# VCF Operations vCommunity

This Management Pack gives the user the ability to add your own content to VCF Operations. While the Management Pack Builder is an option for targets with REST APIs, the vCommunity Management Pack was built using the Integration SDK and offers more advanced features. 

With Phyton programming and VCF Operations API knowledge, you can:

* Add your own Metrics and Properties for existing VCF Objects. 
* Create your own Object Types.
* Add your own Alerts, Dashboards, and Reports. To override existing ones, simply use the same ID.
* Add your own Super Metrics. Note you need to enable them manually in the Policy UI.

![Adapter](Documentation-Images/screenshots/VCF_Operations_vCommunity-Adapter.png)

### Dashboards
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

### Reports
Reports were designed to replace all the existing Reports that came out-of-the-box.
There are 2 types of reports: PDF and CSV.

### Additional Properties & Metrics
- Cluster HA/DRS/EVC
- ESXi Host System Advanced System Settings
- ESXi Host Software Packages
- Virtual Machine Advanced Parameters
- Virtual Machine Options
- Virtual Machine Age
- Virtual Machine Snapshot Count

### Windows Service Monitoring:
* Windows Service Monitoring to track the status of critical services (currently we monitor all Windows Services set to Automatic

### Windows Event Log Monitoring:
* Windows Event Log Monitoring 
