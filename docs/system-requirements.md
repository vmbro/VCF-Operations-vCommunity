# System Requirements

**On this page:**

- [Platform Requirements](#platform-requirements)
- [User Account Requirements](#user-account-requirements)

---

## Platform Requirements

- VCF Operations 8.18.x or higher
- vCenter Server 8 and higher, including VCF 9.x
- A VCF Operations Cloud Proxy
- Container Registry access, to allow the Cloud Proxy to install adapter requirements. If this isn't available in your environment, see [Dark Site Installation](dark-site.md) for a workaround.

The Cloud Proxy will try to pull the container image from the following example registry to set up the adapter. This is by design of the VCF Operations Integration SDK:

```
ghcr.io/vmbro/vcf-operations-vcommunity:x.x.x_x.x
```

HTTPS access to **ghcr.io** is required for every Cloud Proxy that runs the VCF Operations vCommunity Management Pack.

After installing the `.PAK` file for the first time, the Cloud Proxy will pull the related container image from the registry. The Cloud Proxy will also pull a new container image after every `.PAK` file upgrade. Since the vCommunity MP is continuously updated, it's recommended to keep container registry access available — this way, administrators can always easily upgrade the package.

> If your Cloud Proxy does not have internet access, see [Dark Site Installation](dark-site.md) to work with a private registry instead.

FYI, an internet proxy setting is available during OVF deployment of the Cloud Proxy.

---

## User Account Requirements

### vCenter Server

- An account with **read-only** permission.
- The **"Propagate to children"** option must be selected.
- `Host.Configuration.ImageConfiguration` — needed for collecting ESXi VIB packages and ESXi install date.

### Guest OS (Windows) — optional

Only required if **Windows Service Monitoring** and/or **Windows Event Log Monitoring** are enabled (see [Configuration](configuration.md#2-advanced-settings-optional)). Collected agentlessly via GuestAPI, running under this account's security context.

- **Baseline:** any standard, non-admin domain or local Windows account. Service status (`Get-Service`) and OS info (WMI `Win32_OperatingSystem` + `HKLM` registry read) are both readable by a standard authenticated user by default — no extra permission needed for these.
- **If Windows Event Log Monitoring is enabled:** the account must also be a member of the local **`Event Log Readers`** group. The `Application`, `Setup`, and `System` logs are readable by any standard user, but `Security` is not — `Event Log Readers` is the built-in group that grants read access to all of them, including `Security`, without full admin rights.
- **Do not use a local Administrator account** for this credential.

---

**Next:** [Installation](installation.md) · [Configuration](configuration.md)
