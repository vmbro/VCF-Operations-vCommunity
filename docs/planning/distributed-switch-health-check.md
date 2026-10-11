# Distributed Switch Health Check — Planning

> **Status: planned, not built.** This page describes future work, so that collaborators know what is intended and what was already decided. Nothing on this page exists in the pack yet.

## Goal

An always-on health check of vSphere Distributed Switches and distributed port groups that:

- checks the configuration continuously against one baseline the customer defines,
- checks that each host's uplinks are redundant on the physical side,
- has no impact on the network, and
- does not rely on the vSphere Distributed Switch health check feature, whose results are unreliable as an always-on signal (see [Limitations of the current VCF Operations properties](#limitations-of-the-current-vcf-operations-properties)).

It replaces the "Total Network Configuration Issues" and "Total Non-default Settings" super metrics. Both were removed from the pack because the properties they use are unreliable (see the limitations below). Their dashboard widgets and report columns were removed with them, and are to be added back with the new metrics; see [Content to add back](#content-to-add-back).

## Decisions already made

| Topic | Decision |
| :--- | :--- |
| Data source | VCF Operations properties where they exist. Settings that VCF Operations does not collect are read from vCenter, which the pack already connects to for its configuration features. |
| Baseline | One XML baseline file for the whole pack, in the style of the existing `esxi_advanced_system_settings.xml`. |
| First scope | Port group security, teaming and VLAN, plus the uplink redundancy check. |
| vSphere health check feature | Not used as a continuous signal. It stays a troubleshooting tool for change windows. |

## Scope

### Phase 1 (agreed)

**Port group, against the baseline**

| Area | Settings |
| :--- | :--- |
| Security | Promiscuous mode, MAC address changes, Forged transmits. Expected: Reject, unless the baseline lists an exception (for example a nested ESXi port group). |
| Teaming and failover | Load balancing policy, Notify switches, Failback, active and standby uplinks. At least 2 uplinks in total; never 1 active with no standby. |
| VLAN | VLAN type and ID are set. VLAN 0 or None only where the baseline allows it. |

**Host uplink redundancy**

- With LLDP or CDP enabled on the switch, each uplink reports the physical switch and port it is connected to.
- Check that the uplinks of a host connect to at least 2 different physical switches.
- This finds a missed redundancy that no other check sees.

### Phase 2 (later, not agreed yet)

- Port group: override allowed policies (what "Total Non-default Settings" tries to count, but against the baseline instead of the vSphere default), port binding, traffic shaping, NetFlow/IPFIX.
- Distributed switch: version, MTU (the same on every switch that carries vMotion, vSAN or NSX traffic), Network I/O Control, LACP/LAG, discovery protocol on, number of uplinks.
- Host: all uplinks connected and link up, vmkernel MTU equal to the switch MTU, and distributed switch out of sync for several collection cycles in a row (see `host|config_outofsync` below).

## Outputs

| Object | Output |
| :--- | :--- |
| Distributed port group | Compliant or not, and the list of settings that differ from the baseline. |
| Distributed switch | Number of non-compliant port groups. Number of hosts whose uplinks are not on 2 physical switches. |
| vSphere World | Totals, like the other vSphere World summary metrics, with the same known limitations. |

## Design notes

- **Baseline file.** One XML file for the pack, in `content/files/solutionconfig`, with comments that explain each setting. Like the existing files: a reference copy that is overwritten on upgrade, and a working copy that the customer edits.
- **Exceptions.** The baseline lists port groups that may differ, by name, with the setting and the reason.
- **Read once per cycle per vCenter.** All port groups and switches in bulk, as the KPIs do.
- **Properties stay forever.** Once a property is collected, it stays with the object until the object is deleted. This is an existing limitation of the pack's configuration features and applies here too.
- **Tests and documentation.** As for the KPIs: a table of the checks, unit tests with worked examples, and a page with design considerations and known limitations.

## Limitations of the current VCF Operations properties

These distributed switch properties are listed by VCF Operations and used by the "Total Network Configuration Issues" super metric. In practice they do not return the values expected. The reasons below come from Broadcom knowledge base articles and other public sources (listed at the end).

### The four that come from the vSphere health check feature

`host|mtu_mismatch`, `host|vlans_unsupported`, `host|mtu_unsupported`, `host|teaming_mismatch`

| Limitation | Effect on the property |
| :--- | :--- |
| **Health check is off by default.** | Without it, these properties carry no information. A "0" does not mean the network is correct. |
| **Health check should not stay on.** It generates one test MAC address per uplink, per VLAN, per host (Broadcom's example: 2 uplinks × 35 VLANs × 60 hosts = 4,200 entries), which can fill the physical switch MAC table. Broadcom advises against leaving it on continuously, and hardening guides limit it to troubleshooting. | Not suitable as an always-on signal. |
| **Results are not cleared when health check is disabled.** | Old findings stay in vCenter and VCF Operations, so the properties can show problems that no longer exist. |
| **VLAN type None counts as VLAN 0, and VLAN 0 is reported as unsupported.** | False positive on every port group without a VLAN. |
| **Every VLAN is tested on every uplink.** A VLAN that is deliberately not carried on one uplink is reported as unsupported. | False positive with designs that split VLANs across uplinks. It also skews the MTU and teaming results for that uplink. |
| **The MTU test is a round trip that can cross several devices.** | An MTU problem on an upstream device is reported even when the switch directly connected to the host is correct. |
| **Route based on IP hash with EtherChannel:** a reply can arrive on another uplink than the one the probe was sent from. | False "Not Supported" on healthy uplinks. |
| **Hardware virtual NICs**, for example Broadcom Flex10 and Cisco UCS. | The check may not work at all. |
| **Minimums:** the VLAN and MTU checks need at least 2 uplinks; the teaming check needs at least 2 hosts. | No result on small switches. |
| **The teaming check does not cover LAG (LACP) ports.** | No teaming result for LACP uplinks. |
| **Reported after upgrade:** MTU errors on some clusters after vCenter 7.0.3 → 8.0.3. | Possible false positives after an upgrade. |

### `host|config_outofsync`

This one is not part of the health check feature. Each host keeps a local copy of the distributed switch configuration that is synchronised with vCenter; the property flags when that copy is out of sync.

| Limitation | Effect on the property |
| :--- | :--- |
| **Often temporary.** A missed synchronisation after a host or vCenter reboot, a network interruption or a vCenter service restart triggers it, and it usually clears within minutes. | Short spikes that are not real problems. |
| **A real problem when it persists:** a host moved to another vCenter while still attached to the switch, a failed distributed switch upgrade (which can cut VM connectivity), or dvPort conflicts between the host and vCenter. | Meaningful only when it lasts several collection cycles. The fix is "Rectify vSphere Distributed Switch Host" in the vSphere Client. |

**Planned use:** only `host|config_outofsync`, and only when it lasts several collection cycles in a row. That needs code, because a super metric cannot remember earlier cycles. The four health-check properties are not used.

## Limitations of the port group override properties

These distributed port group properties are used by the "Total Non-default Settings" super metric, which counts how many of them are `false`:

`config|policies|override|block_override_allowed`, `…|ipfix_override_allowed`, `…|live_port_moving_allowed`, `…|network_resourcepool_moving_override_allowed`, `…|port_config_reset_at_disconnect`, `…|security_policy_override_allowed`, `…|shaping_override_allowed`, `…|traffic_filter_override_allowed`, `…|uplink_teaming_override_allowed`, `…|vendor_config_override_allowed`, `…|vlan_override_allowed`

They map to the vSphere API port group policy (`DVPortgroupPolicy` and its VMware extension), shown in the vSphere Client under the port group's *Advanced* settings.

### General limitations

| Limitation | Effect |
| :--- | :--- |
| **They say whether a port *may* override the port group, not whether any port *does*.** An "…override_allowed" flag allows an individual distributed port to use its own policy instead of the port group's. | A port group can show every flag `false` and still be fine, or a flag `true` with no port actually overriding anything. The real deviations are on the individual ports, which VCF Operations does not show through these properties. |
| **Counting `false` as "non-default" is inverted.** Per-port overrides are disabled by default, and hardening guidance (DISA STIG) requires them to stay disabled. | The super metric counts the secure, default state as an issue. A fully hardened port group scores the highest count. |
| **Not all keys are override flags.** `port_config_reset_at_disconnect` and `live_port_moving_allowed` control port behaviour, not policy overrides (see below). | Adding them to an override count mixes different meanings. |
| **No per-setting expected value.** The defaults differ per setting, and some customers allow an override on purpose. | A count without a baseline cannot tell an intended setting from a mistake. The plan is to compare each flag with the value in the baseline file. |

### Per property

| Property | What it controls | Limitation or issue |
| :--- | :--- | :--- |
| `block_override_allowed` | A port may be blocked individually, overriding the port group. | Allowing it is commonly left on so single ports can be blocked during troubleshooting. *To verify:* its default value in the vSphere version in use. |
| `ipfix_override_allowed` | A port may use its own NetFlow (IPFIX) setting. | Only meaningful when NetFlow is configured on the distributed switch. |
| `live_port_moving_allowed` | A port that is in use may be moved into or out of the port group. | Not a policy override. It belongs in the baseline, not in an override count. |
| `network_resourcepool_moving_override_allowed` | A port may use another Network I/O Control network resource pool than the port group. | Relates to network resource pools of Network I/O Control. User-defined pools of NIOC version 2 are not available in NIOC version 3 (distributed switch 6.0 and later). *To verify:* whether the flag still has an effect with NIOC version 3. |
| `port_config_reset_at_disconnect` | A port's own settings are reset to the port group's when the VM disconnects. | Not an override flag, and `true` is the protective value: per-port changes do not persist. Counting `false` mixes it with the override flags, where `false` is the protective value. |
| `security_policy_override_allowed` | A port may use its own security policy (promiscuous mode, MAC address changes, forged transmits). | Deprecated in the vSphere API since 6.7, replaced by `macManagementOverrideAllowed`. On current switches it may not reflect the setting that is in force. The replacement is not in this list. *To verify* on a live system. |
| `shaping_override_allowed` | A port may use its own traffic shaping. | Only meaningful when traffic shaping is used. |
| `traffic_filter_override_allowed` | A port may use its own traffic filtering and marking rules. | Only meaningful when traffic filtering and marking is used. |
| `uplink_teaming_override_allowed` | A port may use its own teaming and failover policy. | A port with its own teaming can bypass the redundancy checked at port group level. |
| `vendor_config_override_allowed` | A port may use its own vendor-specific configuration. | Relevant mainly with third-party switch integrations; rarely used. |
| `vlan_override_allowed` | A port may use its own VLAN. | A port with its own VLAN can bypass the port group's VLAN. The VLAN check at port group level does not see it. |

**Planned use:**

- Each flag is compared with its expected value in the baseline file, instead of being counted.
- The deprecated security flag is replaced by `macManagementOverrideAllowed`, read from vCenter if VCF Operations does not collect it.
- `port_config_reset_at_disconnect` and `live_port_moving_allowed` are checked as behaviour settings, not as overrides.
- Detecting the ports that actually override the port group is phase 2. It needs per-port data from vCenter, which can be large on big switches.

## Content to add back

When "Total Network Configuration Issues" (super metric `0c648c9c-cede-4403-b8fe-500067629bf0`) and "Total Non-default Settings" (`f30f298c-385f-4ef8-b511-4092a348a346`) were removed, the content that used them was removed too. Add it back, using the new metrics, when the health check is built.

| Content | What was removed | Super metric it used |
| :--- | :--- | :--- |
| Dashboard *vSphere Network Configuration 2.0* | Widget "Configuration Issues" (Health Chart, for the selected Datacenter or vSphere World), and its interaction from the selector widget | Total Network Configuration Issues |
| Dashboard *vSphere Network Configuration 2.0* | The two columns' saved layout in the "Distributed Switches" view widget | Both |
| Dashboard *VCF Optimization Assessment/Report: vSphere Network Configuration* (in *Input dashboards*) | Widget "Configuration Issues" (Health Chart) | Total Network Configuration Issues |
| Report view *View - Set 3* | Columns "Total Network Configuration Issues" and "Non-default Setting" | Both |
| Report view *View - Set 4* | Columns "Network Configuration Issues" and "Non-default Settings" | Both |
| Report *Report - VOA - Distributed Switch for CSV export* | Columns "Network Configuration Issues" and "Non-default Settings" | Both |

## Open questions

1. Which of the phase 1 settings VCF Operations already collects as properties, and their exact keys and values. To verify on a live system, as was done for the KPI inputs.
2. The default values of the override flags in the vSphere version in use, especially `block_override_allowed`, and whether `security_policy_override_allowed` and `network_resourcepool_moving_override_allowed` still have an effect.
3. Whether VCF Operations collects the LLDP/CDP neighbour of each uplink. If not, it is read from vCenter (decided above).
4. How many cycles in a row `host|config_outofsync` must last before it counts (phase 2).
5. The format of exceptions in the baseline file.

## Sources

- [Network health check feature limitations in vSphere (KB 315308)](https://knowledge.broadcom.com/external/article/315308/network-health-check-feature-limitations.html)
- [vDS Health Check reports unsupported VLANs for MTU and VLAN trunk (KB 318971)](https://knowledge.broadcom.com/external/article/318971/vds-health-check-reports-unsupported-vla.html)
- [vDS Health Check reports unsupported VLANs (legacy KB 2140503)](https://knowledge.broadcom.com/external/article?legacyId=2140503)
- [vDS Health Check reports unsupported VLANs when using IP hash teaming (KB 315270)](https://knowledge.broadcom.com/external/article/315270/vsphere-distributed-switch-health-check.html)
- [Aria Operations alerts for unsupported MTU/VLANs cannot be canceled without re-appearing (KB 423935)](https://knowledge.broadcom.com/external/article/423935/aria-operations-alerts-for-unsupported-m.html)
- [Connectivity issues and MTU/Teaming errors on a non-LACP distributed switch (KB 409275)](https://knowledge.broadcom.com/external/article/409275/connectivity-issues-and-mtuteaming-error.html)
- [vDS MTU errors after vCenter 7.0.3 → 8.0.3 upgrade (KB 408869)](https://knowledge.broadcom.com/external/article/408869/during-upgrade-of-vcenter-server-from-70.html)
- [Enabling vSphere Distributed Switch health check (KB 321305)](https://knowledge.broadcom.com/external/article/321305/enabling-vsphere-distributed-switch-heal.html)
- [vSphere Distributed Switch Health Check — vSphere 8 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere/8-0/vsphere-networking-8-0/monitoring-network-packets/health-check.html)
- [VMware Distributed Virtual Switch Metrics — Aria Operations 8.18 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/aria/aria-operations/8-18/vmware-aria-operations-user-guide-8-18/metric-property-and-alert-definitions/metrics-definitions-in-vrealize-operations-manager/metrics-for-vcenter-server-components/vmware-distributed-virtual-switch-metrics.html)
- [vSphere Distributed Switch Alert Definitions — Aria Operations 8.18 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/aria/aria-operations/8-18/vmware-aria-operations-user-guide-8-18/metric-property-and-alert-definitions/alert-definitions-in-vrealize-operations-manager/vsphere-distributed-switch-alert-definitions.html)
- [vDS configuration on some hosts differed from vCenter — "Out of Sync" (KB 317901 / 2042692)](https://knowledge.broadcom.com/external/article/317901)
- [ESXi hosts showing out of sync with distributed switch (KB 317923)](https://knowledge.broadcom.com/external/article/317923/esxi-hosts-showing-out-of-sync-with-dist.html)
- [VMs unable to ping on vDS after upgrade (KB 396559)](https://knowledge.broadcom.com/external/article/396559)
- [Dell: vSphere Distributed Switch Health Check Reports Unsupported VLANs and MTU](https://www.dell.com/support/kbdoc/en-us/000402855/vsphere-distributed-switch-health-check-reports-unsupported-vlans-and-mtu)
- [DVPortgroupPolicy — vSphere API reference](https://vdc-download.vmware.com/vmwb-repository/dcr-public/a5f4000f-1ea8-48a9-9221-586adff3c557/7ff50256-2cf2-45ea-aacd-87d231ab1ac7/vim.dvs.DistributedVirtualPortgroup.PortgroupPolicy.html)
- [community.vmware issue #1998: securityPolicyOverrideAllowed deprecated since vSphere API 6.7](https://github.com/ansible-collections/community.vmware/issues/1998)
- [Configure Overriding Networking Policies on Port Level — vSphere 8 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere/8-0/vsphere-networking-8-0/networking-policies/configure-overriding-networking-policies-on-port-level.html)
- [DISA STIG VCWN-06-000017: the system must not override port group settings at the port level](https://www.tenable.com/audits/items/DISA_STIG_VMware_vSphere_vCenter_6_v1r4.audit:87aea9919637818c03d97ce700a791e2)
- [vCenter Server Security Controls Reference — vSphere 8 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere/8-0/vsphere-security/understanding-vsphere-hardening-and-compliance/understanding-vsphere-security-configuration-guide/vcenter-server-security-controls-reference.html)
- [About vSphere Network I/O Control Version 3 — vSphere 6.0 docs](https://docs.vmware.com/en/VMware-vSphere/6.0/com.vmware.vsphere.networking.doc/GUID-98E0B3C2-52A7-4CAB-A839-4DA82A9F6D3A.html)
- [vsphere.DistributedPortGroup — Pulumi provider docs](https://www.pulumi.com/registry/packages/vsphere/api-docs/distributedportgroup/)
- [vSphere Distributed Switch health check fails on HPE Comware switches](https://vcloudnine.de/vsphere-distributed-switch-health-check-fails-on-hpe-comware-switches/)

The knowledge base pages could not be opened from the environment where this page was written; the limitations are taken from the published excerpts of these articles. Confirm against the articles before relying on a specific detail.
