#!/usr/bin/env python3
"""
Author: Onur Yuzseven - onur.yuzseven@broadcom.com

importer.py - Bulk Adapter Instance creator for the VCF Operations vCommunity Management Pack.

For each row in a CSV file (one row = one vCenter), this script creates or reuses a
Credential Instance and creates an Adapter Instance - so you can onboard 20+ vCenters
with a single command instead of configuring each one manually in the UI.

Suite API endpoints used (verified against the documentation at
developer.broadcom.com/xapis/vcf-operations-api):
    POST /suite-api/api/auth/token/acquire
    POST /suite-api/api/auth/token/release
    POST /suite-api/api/credentials
    POST /suite-api/api/adapters

COLLECTOR ASSIGNMENT:
    Use the "collector_name" CSV column to pin an adapter instance to a specific
    Collector (Cloud Proxy) OR a Collector Group - enter either kind of name, the
    script figures out which one it is and resolves it to the correct id automatically
    (via GET /api/collectors, then GET /api/collectorgroups). Leave it blank to let
    the system choose automatically.

    You never need to look up or paste a raw id yourself: a Collector's usable id is a
    short number (e.g. "1", "2"), while a Collector Group's id is a UUID - two different
    shapes that are easy to confuse if entered by hand (the UI's "Proxy ID" field is
    neither of these - it shows the collector's internal nodeIdentifier, which the API
    rejects). Using collector_name avoids all of this.

CREDENTIAL REUSE:
    If a credential with the given "credential_name" already exists in VCF Operations,
    the script logs this and reuses the existing credential's ID instead of failing.
    The existing credential's stored password is NOT overwritten with the CSV's
    password - if they differ, the resulting adapter instance may fail to authenticate.

SECURITY NOTE:
    The CSV file contains vCenter passwords in PLAIN TEXT. After use, delete the CSV
    securely or restrict access to it (e.g. chmod 600), and never commit it to version
    control. For the VCF Operations admin password, an environment variable or an
    interactive prompt is recommended instead of a command-line argument (which would
    be visible in shell history).

Usage:
    python importer.py \\
        --vcf-host vcfops.example.com \\
        --vcf-user admin \\
        --csv vcenters.csv \\
        [--dry-run] [--insecure] [--verbose]

    The VCF Operations password can be provided via --vcf-password, OR via the
    VCFOPS_PASSWORD environment variable, OR if neither is given, via an interactive
    (hidden) prompt.
"""

import argparse
import csv
import getpass
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import requests
import urllib3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("importer")

# Constants taken VERBATIM from get_adapter_definition() in the vCommunity adapter.py.
# If you update this file, keep it in sync with the definition in adapter.py.
ADAPTER_KIND_KEY = "VCFOperationsvCommunity"
CREDENTIAL_KIND_KEY = "vsphere_user"

IDENTIFIER_HOST = "host"
IDENTIFIER_PORT = "port"
IDENTIFIER_ESXI_ADV_SETTINGS = "esxi_adv_settings_config_file"
IDENTIFIER_ESXI_VIB_DRIVER = "esxi_vib_driver_config_file"
IDENTIFIER_VM_ADV_SETTINGS = "vm_adv_settings_config_file"
IDENTIFIER_VM_CONFIGURATION = "vm_configuration_config_file"
IDENTIFIER_WIN_SERVICE_CONFIG = "win_service_config_file"
IDENTIFIER_WIN_EVENT_CONFIG = "win_event_config_file"
IDENTIFIER_SERVICE_MONITORING = "serviceMonitoring"
IDENTIFIER_WIN_EVENT_MONITORING = "winEventMonitoring"

CREDENTIAL_FIELD_USER = "user"
CREDENTIAL_FIELD_PASSWORD = "password"
CREDENTIAL_FIELD_WIN_USER = "winUser"
CREDENTIAL_FIELD_WIN_PASS = "winPass"

# Same as the define_string_parameter(..., default=...) values in adapter.py.
DEFAULTS = {
    "vcenter_port": "443",
    "esxi_adv_settings_config_file": "esxi_advanced_system_settings",
    "esxi_vib_driver_config_file": "esxi_packages",
    "vm_adv_settings_config_file": "vm_advanced_parameters",
    "vm_configuration_config_file": "vm_options",
    "win_service_config_file": "windows_service_list",
    "win_event_config_file": "windows_event_list",
    "service_monitoring": "Disabled",
    "win_event_monitoring": "Disabled",
}


@dataclass
class VCenterRow:
    vcenter_host: str
    vcenter_port: str
    vcenter_user: str
    vcenter_password: str
    display_name: str
    credential_name: str
    esxi_adv_settings_config_file: str
    esxi_vib_driver_config_file: str
    vm_adv_settings_config_file: str
    vm_configuration_config_file: str
    win_service_config_file: str
    win_event_config_file: str
    service_monitoring: str
    win_event_monitoring: str
    win_user: str
    win_pass: str
    collector_name: str


def read_csv(path: str) -> list[VCenterRow]:
    rows: list[VCenterRow] = []
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for lineno, raw in enumerate(reader, start=2):  # 1 = header
            host = (raw.get("vcenter_host") or "").strip()
            user = (raw.get("vcenter_user") or "").strip()
            password = (raw.get("vcenter_password") or "").strip()

            if not host or not user or not password:
                raise ValueError(
                    f"CSV row {lineno}: vcenter_host/vcenter_user/vcenter_password are required, "
                    f"a value is missing/empty."
                )

            rows.append(VCenterRow(
                vcenter_host=host,
                vcenter_port=(raw.get("vcenter_port") or DEFAULTS["vcenter_port"]).strip(),
                vcenter_user=user,
                vcenter_password=password,
                display_name=(raw.get("display_name") or "").strip() or f"vCommunity - {host}",
                credential_name=(raw.get("credential_name") or "").strip() or f"vCommunity Credential - {host}",
                esxi_adv_settings_config_file=(raw.get("esxi_adv_settings_config_file") or "").strip() or DEFAULTS["esxi_adv_settings_config_file"],
                esxi_vib_driver_config_file=(raw.get("esxi_vib_driver_config_file") or "").strip() or DEFAULTS["esxi_vib_driver_config_file"],
                vm_adv_settings_config_file=(raw.get("vm_adv_settings_config_file") or "").strip() or DEFAULTS["vm_adv_settings_config_file"],
                vm_configuration_config_file=(raw.get("vm_configuration_config_file") or "").strip() or DEFAULTS["vm_configuration_config_file"],
                win_service_config_file=(raw.get("win_service_config_file") or "").strip() or DEFAULTS["win_service_config_file"],
                win_event_config_file=(raw.get("win_event_config_file") or "").strip() or DEFAULTS["win_event_config_file"],
                service_monitoring=(raw.get("service_monitoring") or "").strip() or DEFAULTS["service_monitoring"],
                win_event_monitoring=(raw.get("win_event_monitoring") or "").strip() or DEFAULTS["win_event_monitoring"],
                win_user=(raw.get("win_user") or "").strip(),
                win_pass=(raw.get("win_pass") or "").strip(),
                collector_name=(raw.get("collector_name") or "").strip(),
            ))
    return rows


class CredentialConflictError(RuntimeError):
    """Raised when a credential with the requested name already exists (HTTP 422)."""
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"A credential named '{name}' already exists.")


class VcfOpsClient:
    def __init__(self, base_url: str, verify_ssl: bool = True):
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.token: Optional[str] = None
        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _url(self, path: str) -> str:
        return f"{self.base_url}/suite-api{path}"

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"OpsToken {self.token}"
        return headers

    def acquire_token(self, username: str, password: str) -> None:
        resp = self.session.post(
            self._url("/api/auth/token/acquire"),
            headers={"Content-Type": "application/json"},
            data=json.dumps({"username": username, "password": password}),
            verify=self.verify_ssl,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to acquire VCF Operations token (HTTP {resp.status_code}): {resp.text}")
        self.token = resp.json()["token"]
        logger.info("VCF Operations session opened.")

    def release_token(self) -> None:
        if not self.token:
            return
        try:
            self.session.post(self._url("/api/auth/token/release"), headers=self._headers(), verify=self.verify_ssl)
            logger.info("VCF Operations session closed.")
        except requests.RequestException as e:
            logger.warning(f"Error while releasing token (non-fatal, can be ignored): {e!r}")

    def create_credential(self, name: str, fields: list[dict]) -> str:
        payload = {
            "name": name,
            "adapterKindKey": ADAPTER_KIND_KEY,
            "credentialKindKey": CREDENTIAL_KIND_KEY,
            "fields": fields,
        }
        resp = self.session.post(
            self._url("/api/credentials"),
            headers=self._headers(),
            data=json.dumps(payload),
            verify=self.verify_ssl,
        )
        if resp.status_code == 422:
            raise CredentialConflictError(name)
        if resp.status_code != 201:
            raise RuntimeError(f"Failed to create credential (HTTP {resp.status_code}): {resp.text}")
        return resp.json()["id"]

    def find_credential_by_name(self, name: str, adapter_kind_key: str) -> Optional[str]:
        """
        Look up an existing credential by exact name. The Suite API's GET /api/credentials
        endpoint only supports filtering by id or adapterKind (no name filter server-side),
        so we narrow by adapterKind and match the name client-side.
        """
        resp = self.session.get(
            self._url("/api/credentials"),
            params={"adapterKind": adapter_kind_key},
            headers=self._headers(),
            verify=self.verify_ssl,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to look up existing credentials (HTTP {resp.status_code}): {resp.text}")
        for cred in resp.json().get("credentialInstances", []):
            if cred.get("name") == name:
                return cred.get("id")
        return None

    def resolve_collector_by_name(self, name: str) -> tuple[Optional[str], Optional[str]]:
        """
        Resolve a name to either a Collector or a Collector Group, whichever matches.
        Returns (collector_id, collector_group_id) - exactly one will be set, or both
        None if nothing matched. Collectors are checked first, then Collector Groups.

        Field-shape notes (confirmed against a live instance):
        - A Collector's usable id is its short numeric "id" field (e.g. "1", "2") under
          the "collector" key of GET /api/collectors - NOT its "uuId" or "nodeIdentifier"
          field, which are UUID-shaped and look plausible but are rejected by the API.
        - A Collector Group's id IS a UUID, under the "collectorGroups" key of
          GET /api/collectorgroups.
        """
        resp = self.session.get(self._url("/api/collectors"), headers=self._headers(), verify=self.verify_ssl)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to look up collectors (HTTP {resp.status_code}): {resp.text}")
        for collector in resp.json().get("collector", []):
            if collector.get("name") == name:
                return collector.get("id"), None

        resp = self.session.get(self._url("/api/collectorgroups"), headers=self._headers(), verify=self.verify_ssl)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to look up collector groups (HTTP {resp.status_code}): {resp.text}")
        for group in resp.json().get("collectorGroups", []):
            if group.get("name") == name:
                return None, group.get("id")

        return None, None

    def create_adapter_instance(self, name: str, description: str, resource_identifiers: list[dict],
                                 credential_id: str, collector_id: Optional[str] = None,
                                 collector_group_id: Optional[str] = None) -> dict:
        payload = {
            "name": name,
            "description": description,
            "adapterKindKey": ADAPTER_KIND_KEY,
            "resourceIdentifiers": resource_identifiers,
            "credential": {"id": credential_id},
        }
        # The API accepts collectorId or collectorGroupId, but not both - CSV validation in
        # read_csv() already guarantees at most one of these is set.
        if collector_id:
            payload["collectorId"] = collector_id
        elif collector_group_id:
            payload["collectorGroupId"] = collector_group_id

        resp = self.session.post(
            self._url("/api/adapters"),
            params={"force": "true"},
            headers=self._headers(),
            data=json.dumps(payload),
            verify=self.verify_ssl,
        )
        if resp.status_code != 201:
            raise RuntimeError(f"Failed to create adapter instance (HTTP {resp.status_code}): {resp.text}")
        return resp.json()

    def list_collectors(self) -> dict:
        resp = self.session.get(self._url("/api/collectors"), headers=self._headers(), verify=self.verify_ssl)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to list collectors (HTTP {resp.status_code}): {resp.text}")
        return resp.json()

    def list_collector_groups(self) -> dict:
        resp = self.session.get(self._url("/api/collectorgroups"), headers=self._headers(), verify=self.verify_ssl)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to list collector groups (HTTP {resp.status_code}): {resp.text}")
        return resp.json()


def build_resource_identifiers(row: VCenterRow) -> list[dict]:
    return [
        {"name": IDENTIFIER_HOST, "value": row.vcenter_host},
        {"name": IDENTIFIER_PORT, "value": row.vcenter_port},
        {"name": IDENTIFIER_ESXI_ADV_SETTINGS, "value": row.esxi_adv_settings_config_file},
        {"name": IDENTIFIER_ESXI_VIB_DRIVER, "value": row.esxi_vib_driver_config_file},
        {"name": IDENTIFIER_VM_ADV_SETTINGS, "value": row.vm_adv_settings_config_file},
        {"name": IDENTIFIER_VM_CONFIGURATION, "value": row.vm_configuration_config_file},
        {"name": IDENTIFIER_WIN_SERVICE_CONFIG, "value": row.win_service_config_file},
        {"name": IDENTIFIER_WIN_EVENT_CONFIG, "value": row.win_event_config_file},
        {"name": IDENTIFIER_SERVICE_MONITORING, "value": row.service_monitoring},
        {"name": IDENTIFIER_WIN_EVENT_MONITORING, "value": row.win_event_monitoring},
    ]


def build_credential_fields(row: VCenterRow) -> list[dict]:
    fields = [
        {"name": CREDENTIAL_FIELD_USER, "value": row.vcenter_user},
        {"name": CREDENTIAL_FIELD_PASSWORD, "value": row.vcenter_password},
    ]
    if row.win_user:
        fields.append({"name": CREDENTIAL_FIELD_WIN_USER, "value": row.win_user})
    if row.win_pass:
        fields.append({"name": CREDENTIAL_FIELD_WIN_PASS, "value": row.win_pass})
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk Adapter Instance creator for the vCommunity Management Pack.")
    parser.add_argument("--vcf-host", required=True, help="VCF Operations FQDN/IP (e.g. vcfops.example.com)")
    parser.add_argument("--vcf-user", required=True, help="VCF Operations username")
    parser.add_argument("--vcf-password", default=None, help="VCF Operations password (if omitted, the VCFOPS_PASSWORD env var or an interactive prompt is used)")
    parser.add_argument("--csv", default=None, help="Path to the CSV file containing the vCenter list (required unless --list-collectors is given)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without creating anything")
    parser.add_argument("--insecure", action="store_true", help="Skip SSL certificate verification for VCF Operations (for self-signed certificates)")
    parser.add_argument("--verbose", action="store_true", help="Verbose (DEBUG) logging")
    parser.add_argument("--list-collectors", action="store_true",
                         help="Print a simple name/id list of Collectors and Collector Groups, then exit. "
                              "Use this to find the exact 'name' value to put in the collector_name CSV column.")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if not args.list_collectors and not args.csv:
        parser.error("--csv is required unless --list-collectors is given")

    vcf_password = args.vcf_password or os.environ.get("VCFOPS_PASSWORD")
    if not vcf_password:
        vcf_password = getpass.getpass(f"VCF Operations password ({args.vcf_user}): ")

    base_url = args.vcf_host if args.vcf_host.startswith("http") else f"https://{args.vcf_host}"
    client = VcfOpsClient(base_url, verify_ssl=not args.insecure)

    if args.list_collectors:
        try:
            client.acquire_token(args.vcf_user, vcf_password)

            collectors = client.list_collectors().get("collector", [])
            print("\nCollectors:")
            if not collectors:
                print("  (none found)")
            for c in collectors:
                state = c.get("state", "?")
                print(f"  {c.get('name'):<55} id={c.get('id'):<6} state={state}")

            groups = client.list_collector_groups().get("collectorGroups", [])
            print("\nCollector Groups:")
            if not groups:
                print("  (none found)")
            for g in groups:
                print(f"  {g.get('name'):<55} id={g.get('id')}")

            print("\nUse the exact value from the 'name' column above in the collector_name CSV column.\n")
        finally:
            client.release_token()
        return 0

    try:
        rows = read_csv(args.csv)
    except (ValueError, OSError, csv.Error) as e:
        logger.error(f"Could not read CSV: {e}")
        return 1

    logger.info(f"Read {len(rows)} vCenter row(s) from: {args.csv}")

    if args.dry_run:
        logger.info("--dry-run is active: no API calls will be made, showing the plan only.\n")
        for row in rows:
            collector_info = f"'{row.collector_name}' (resolved at run time)" if row.collector_name else "automatic"
            print(f"  -> {row.display_name}  (host={row.vcenter_host}:{row.vcenter_port}, "
                  f"credential='{row.credential_name}', collector={collector_info})")
        return 0

    results: list[tuple[str, bool, str]] = []
    credential_cache: dict[str, str] = {}  # credential_name -> credential_id

    try:
        client.acquire_token(args.vcf_user, vcf_password)

        for row in rows:
            try:
                if row.credential_name in credential_cache:
                    credential_id = credential_cache[row.credential_name]
                    logger.info(f"[{row.display_name}] Reusing credential from earlier in this run: '{row.credential_name}'")
                else:
                    try:
                        credential_id = client.create_credential(row.credential_name, build_credential_fields(row))
                        logger.info(f"[{row.display_name}] Credential created: '{row.credential_name}' ({credential_id})")
                    except CredentialConflictError:
                        credential_id = client.find_credential_by_name(row.credential_name, ADAPTER_KIND_KEY)
                        if credential_id is None:
                            raise RuntimeError(
                                f"Credential '{row.credential_name}' reported a conflict (422) but could not "
                                f"be found via lookup - it may belong to a different adapter kind."
                            )
                        logger.info(
                            f"[{row.display_name}] A credential named '{row.credential_name}' already exists - "
                            f"reusing it (id={credential_id}). NOTE: its stored password was NOT updated from "
                            f"the CSV - if the CSV password differs from what is currently stored, the adapter "
                            f"instance may fail to authenticate to vCenter."
                        )
                    credential_cache[row.credential_name] = credential_id

                resolved_collector_id, resolved_collector_group_id = None, None
                if row.collector_name:
                    resolved_collector_id, resolved_collector_group_id = client.resolve_collector_by_name(row.collector_name)
                    if resolved_collector_id is None and resolved_collector_group_id is None:
                        raise RuntimeError(
                            f"No Collector or Collector Group found with name '{row.collector_name}' "
                            f"(checked GET /api/collectors and GET /api/collectorgroups). Check spelling."
                        )
                    kind = "collector" if resolved_collector_id else "collector group"
                    logger.info(f"[{row.display_name}] Resolved collector_name '{row.collector_name}' -> {kind} id={resolved_collector_id or resolved_collector_group_id}")

                adapter = client.create_adapter_instance(
                    name=row.display_name,
                    description=f"Auto-created for vCommunity - {row.vcenter_host} (importer.py)",
                    resource_identifiers=build_resource_identifiers(row),
                    credential_id=credential_id,
                    collector_id=resolved_collector_id,
                    collector_group_id=resolved_collector_group_id,
                )
                logger.info(f"[{row.display_name}] Adapter instance created: {adapter.get('id')}")
                results.append((row.display_name, True, adapter.get("id", "")))

            except RuntimeError as e:
                logger.error(f"[{row.display_name}] FAILED: {e}")
                results.append((row.display_name, False, str(e)))

    finally:
        client.release_token()

    # --- Summary report ---
    success_count = sum(1 for _, ok, _ in results if ok)
    fail_count = len(results) - success_count

    print("\n" + "=" * 70)
    print(f"RESULT: {success_count} succeeded, {fail_count} failed (total {len(results)})")
    print("=" * 70)
    for name, ok, info in results:
        status = "OK   " if ok else "FAILED"
        print(f"  [{status}] {name}  -  {info}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
