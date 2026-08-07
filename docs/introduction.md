# Introduction

## What is the vCommunity Management Pack?

This Management Pack gives VCF Operations admins the ability to add their own content to VCF Operations. While the Management Pack Builder is the best tool for rapid and easy extension, the vCommunity Management Pack was built using the [VCF Operations Integration SDK](https://github.com/vmware/vmware-aria-operations-integration-sdk) and offers more advanced features — parallel, high-performance data collection at scale, custom object properties and metrics, and configuration-driven flexibility over exactly what gets monitored.

## Why You Need It

VMware/Broadcom security hardening guides, Knowledge Base articles, and vSphere best-practice documentation consistently call out **specific ESXi Advanced System Settings and VM Advanced Parameters** that should be configured a certain way — timeout values, security-related flags, storage behavior settings, and more. These recommendations exist because getting them wrong has real consequences: instability, performance degradation, or security exposure.

The problem is that standard vCenter and VCF Operations monitoring doesn't track these deep configuration values by default. A setting can drift — changed manually during troubleshooting, missed during a host rebuild, inconsistent across a cluster — and nothing will tell you. Often, the first sign of a problem is the incident itself.

**This Management Pack closes that visibility gap.** It continuously collects exactly the ESXi and VM advanced settings that matter to you — the ones referenced in your hardening guides, your internal best practices, or your own operational experience — across every host and VM in your environment. Configuration drift becomes something you can see and alert on, not something you discover during a postmortem.

In short: **stable environments start with consistent configuration, and you can't keep configuration consistent if you can't see it.**

## What It Collects

Out of the box, and fully customizable via simple configuration files, the Management Pack captures:

- **ESXi Host Advanced System Settings** — the specific settings *you* choose to track
- **ESXi Host Software Packages (VIBs)** — installed driver/package names, versions, and vendors
- **VM Advanced Parameters** — the specific `.vmx`-level settings *you* choose to track
- **VM Options** — configuration fields such as boot options, firmware type, hardware version, and more
- **Cluster HA / DRS / EVC configuration** — settings that affect availability and resource management
- **Microsoft Windows Services and Event Logs** *(optional, agentless via GuestAPI)*
- **Virtual Machine Snapshot Count** and other properties commonly missing from default inventory

Every one of these is documented, with its exact object path and description, in the [Metrics & Properties Reference](metrics-reference.md).

## Built for Scale

Configuration drift monitoring is only useful if it actually finishes collecting before the next cycle starts. The vCommunity Management Pack's data collection architecture was built and performance-tuned specifically for large environments — parallel collectors, careful concurrency control around expensive host-level API calls, and a full collection cycle that stays comfortably under 5 minutes even at 1,500+ hosts and 15,000+ VMs.

## Community-Driven

This is a free Management Pack developed by [Onur Yuzseven](https://www.linkedin.com/in/oyuzseven/) as a contribution to the vCommunity (VMUG, vExpert, VCP). It's not an official VMware/Broadcom project and comes with no VMware GSS support — see [Support](../SUPPORT.md) and [License](../LICENSE) for details. Contributions, dashboards, and reports from the wider community (see the main [README](../README.md)) extend it well beyond the core data collection described here.

## Where to Go Next

- [System Requirements](system-requirements.md)
- [Installation](installation.md)
- [Configuration](configuration.md) — how to choose exactly which settings get monitored
- [How It Works](how-it-works.md)
