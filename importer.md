# Bulk Adapter Instance Importer

`importer.py` bulk-creates VCF Operations vCommunity Management Pack **Adapter Instances** from a CSV file — one row per vCenter. Instead of configuring each vCenter manually through the VCF Operations UI, you can onboard 20, 50, or 200 vCenters with a single command.

For each row, the script:

1. Creates a **Credential Instance** for the vCenter (or reuses an existing one with the same name).
2. Creates the **Adapter Instance**, wiring up all vCommunity configuration parameters.
3. Optionally pins the instance to a specific **Collector** (Cloud Proxy) or **Collector Group**.

It talks directly to the [VCF Operations Suite API](https://developer.broadcom.com/xapis/vcf-operations-api/latest/) — no other tooling required.

---

## Requirements

- **Python 3.9+**
- The [`requests`](https://pypi.org/project/requests/) library

```bash
pip install requests
```

No other dependencies. The script is a single file (`importer.py`) — no installation step needed beyond that.

---

## Quick Start

```bash
# 1. See what would happen, without creating anything
python importer.py --vcf-host vcfops.example.com --vcf-user admin --csv vcenters.csv --dry-run

# 2. Run it for real
python importer.py --vcf-host vcfops.example.com --vcf-user admin --csv vcenters.csv
```

You'll be prompted for the VCF Operations password interactively (hidden input) unless you provide it another way — see [Authentication](#authentication) below.

---

## Authentication

The **VCF Operations** admin password (for `--vcf-user`) can be supplied in any of these ways, in order of precedence:

| Method | How |
|---|---|
| CLI flag | `--vcf-password 'yourpassword'` (⚠️ visible in shell history — avoid for anything but quick local tests) |
| Environment variable | `export VCFOPS_PASSWORD='yourpassword'` before running |
| Interactive prompt | Leave both of the above out — the script will ask (hidden input, nothing echoed to screen) |

**vCenter** credentials (one per CSV row) are supplied via the `vcenter_password` CSV column — see the [Security Notes](#security-notes) below.

---

## Command-Line Reference

| Flag | Required? | Description |
|---|---|---|
| `--vcf-host` | ✅ Yes | VCF Operations FQDN or IP, e.g. `vcfops.example.com`. `https://` is added automatically if omitted. |
| `--vcf-user` | ✅ Yes | VCF Operations username (e.g. `admin`). |
| `--vcf-password` | No | See [Authentication](#authentication). |
| `--csv` | ✅ Yes* | Path to the CSV file. *Not required if `--list-collectors` is used. |
| `--dry-run` | No | Show what would be created, without making any API calls that create/modify anything. |
| `--insecure` | No | Skip SSL certificate verification against VCF Operations (for self-signed certs). |
| `--verbose` | No | Enable DEBUG-level logging. |
| `--list-collectors` | No | Print all available Collector and Collector Group names + IDs, then exit. Use this to find the exact value to put in the `collector_name` CSV column. Does not require `--csv`. |

---

## CSV File Format

One row = one vCenter / one Adapter Instance. The header row is required; column order does not matter.

**Only three columns are required.** Every other column can be **left empty** — the script falls back to the same defaults defined in the Management Pack's `adapter.py`. You do not need to include columns you don't use, but it's easiest to keep the full header row and just leave the cells blank.

| Column | Required? | Default if blank | Description |
|---|---|---|---|
| `vcenter_host` | ✅ Yes | — | vCenter FQDN or IP address. |
| `vcenter_user` | ✅ Yes | — | vCenter username used by the adapter to collect data. |
| `vcenter_password` | ✅ Yes | — | Password for `vcenter_user`. **Plain text in the CSV** — see [Security Notes](#security-notes). |
| `vcenter_port` | No | `443` | vCenter HTTPS port. |
| `display_name` | No | `vCommunity - <vcenter_host>` | Adapter Instance name as shown in the VCF Operations UI. |
| `credential_name` | No | `vCommunity Credential - <vcenter_host>` | Name of the Credential Instance to create/reuse. Two rows with the same `credential_name` reuse a single credential — see [Credential Reuse](#credential-reuse). |
| `esxi_adv_settings_config_file` | No | `esxi_advanced_system_settings` | Name of the config file listing ESXi Advanced System Settings to collect. |
| `esxi_vib_driver_config_file` | No | `esxi_packages` | Name of the config file listing VIB/driver names to collect. |
| `vm_adv_settings_config_file` | No | `vm_advanced_parameters` | Name of the config file listing VM advanced parameters to collect. |
| `vm_configuration_config_file` | No | `vm_options` | Name of the config file listing VM config paths to collect. |
| `win_service_config_file` | No | `windows_service_list` | Name of the config file listing Windows service names (Guest OS monitoring). |
| `win_event_config_file` | No | `windows_event_list` | Name of the config file listing Windows Event Log IDs (Guest OS monitoring). |
| `service_monitoring` | No | `Disabled` | `Enabled` or `Disabled` — Guest OS service monitoring. |
| `win_event_monitoring` | No | `Disabled` | `Enabled` or `Disabled` — Windows Event Log monitoring. |
| `win_user` | No | *(blank)* | Windows username, only needed if Guest OS monitoring is enabled. |
| `win_pass` | No | *(blank)* | Windows password, only needed if Guest OS monitoring is enabled. |
| `collector_name` | No | *(automatic)* | Name of a **Collector** (Cloud Proxy) or **Collector Group** to pin this instance to. See [Collector Assignment](#collector-assignment). Leave blank to let VCF Operations choose automatically. |

### Example CSV

```csv
vcenter_host,vcenter_port,vcenter_user,vcenter_password,display_name,credential_name,esxi_adv_settings_config_file,esxi_vib_driver_config_file,vm_adv_settings_config_file,vm_configuration_config_file,win_service_config_file,win_event_config_file,service_monitoring,win_event_monitoring,win_user,win_pass,collector_name
vc01.example.com,443,svc-vcfops,SecretPass1!,vCommunity - VC01,vCommunity - Credential,,,,,,,,,,,vcfops-arm-m02-cp01.vcfops.lvn.broadcom.net
vc02.example.com,443,svc-vcfops,SecretPass1!,vCommunity - VC02,vCommunity - Credential,,,,,,,,,,,my-collector-group-name
vc03.example.com,,svc-vcfops-vc03,AnotherPass2!,,,esxi_packages,esxi_packages,,,,,Enabled,Disabled,,,
```

- **Row 1 (VC01):** pinned to a specific Collector by name, shares a credential with VC02.
- **Row 2 (VC02):** pinned to a Collector *Group* by name — same `collector_name` column handles both cases automatically.
- **Row 3 (VC03):** minimal row — uses defaults for almost everything, no collector pinning (VCF Operations chooses automatically), Guest OS service monitoring enabled.

---

## Collector Assignment

Put a **Collector** name or a **Collector Group** name in the `collector_name` column — the script tries both automatically and resolves it to the right ID for you:

```bash
python importer.py --vcf-host vcfops.example.com --vcf-user admin --list-collectors
```

```
Collectors:
  vcfops-arm-m02-cp01.vcfops.lvn.broadcom.net              id=2      state=UP
  VCF Operations Collector-vcfops-arm-m02-ops01            id=1      state=UP

Collector Groups:
  my-collector-group-name                                   id=ca66b8f8-fdc1-477e-8532-bbd6c1c877ed

Use the exact value from the 'name' column above in the collector_name CSV column.
```

Copy the exact `name` value into your CSV. Leave `collector_name` blank to let VCF Operations pick a collector automatically.

> **Why by name, not by ID?** A Collector's internal ID is a short number (`"1"`, `"2"`), while a Collector Group's ID is a UUID — two different formats on the same-looking field. The VCF Operations UI's "Proxy ID" field shows yet another internal identifier that the API does not accept for this purpose. Using `collector_name` avoids all of this — the script looks the name up and uses whichever ID format is correct.

---

## Credential Reuse

If two CSV rows share the same `credential_name`, the Credential Instance is created once and reused for both — useful when multiple vCenters share one service account.

If a credential with that name **already exists in VCF Operations** (e.g. from a previous run), the script does **not** fail. It logs a notice and reuses the existing credential's ID instead:

```
[vCommunity - VC01] A credential named 'vCommunity - Credential' already exists - reusing it
(id=15efe2dd-...). NOTE: its stored password was NOT updated from the CSV - if the CSV
password differs from what is currently stored, the adapter instance may fail to authenticate.
```

The existing credential's **stored password is never overwritten** — this is intentional, since the same credential may already be in use by other adapter instances. If you need to rotate a password, do it through the VCF Operations UI or API directly.

---

## Security Notes

- The CSV file contains **vCenter passwords in plain text**. After you're done:
  - Delete the CSV, or
  - Restrict its permissions (`chmod 600 vcenters.csv`), and
  - **Never commit it to version control.**
- Prefer the environment variable or interactive prompt for `--vcf-password` over the `--vcf-password` CLI flag, which is visible in shell history and process listings.
- `--insecure` disables SSL certificate verification against VCF Operations. Only use it for self-signed certs in trusted/internal environments.

---

## Output

After a run, a summary is printed:

```
======================================================================
RESULT: 3 succeeded, 1 failed (total 4)
======================================================================
  [OK   ] vCommunity - VC01  -  a1b2c3d4-...
  [OK   ] vCommunity - VC02  -  b2c3d4e5-...
  [OK   ] vCommunity - VC03  -  c3d4e5f6-...
  [FAILED] vCommunity - VC04  -  Failed to create adapter instance (HTTP 500): ...
```

The process exits with code `0` if every row succeeded, `1` if any row failed — so it's safe to use in scripts/CI (`&& echo "all good"`).

Each row is independent: if one vCenter fails (bad credentials, unreachable host, etc.), the rest still get processed.

---

## Suite API Endpoints Used

Verified against the [VCF Operations API documentation](https://developer.broadcom.com/xapis/vcf-operations-api/latest/):

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/suite-api/api/auth/token/acquire` | Log in, get a session token |
| `POST` | `/suite-api/api/auth/token/release` | Log out at the end of the run |
| `GET` | `/suite-api/api/credentials` | Look up an existing credential by name (on conflict) |
| `POST` | `/suite-api/api/credentials` | Create a Credential Instance |
| `GET` | `/suite-api/api/collectors` | Resolve `collector_name` to a Collector ID |
| `GET` | `/suite-api/api/collectorgroups` | Resolve `collector_name` to a Collector Group ID |
| `POST` | `/suite-api/api/adapters` | Create an Adapter Instance |
