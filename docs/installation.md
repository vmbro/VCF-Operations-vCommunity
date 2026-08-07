# Installation

**On this page:**

- [Enable Unsigned PAK Installation](#enable-unsigned-pak-installation)
- [Install the Management Pack](#install-the-management-pack)

---

## Enable Unsigned PAK Installation

Since the PAK file is not signed by VMware/Broadcom (this is a community-built, unofficial Management Pack — see the main [README](../README.md)), you need to enable unsigned PAK installation once per VCF Operations instance:

1. Go to `https://<VCF_Ops>/admin` → **Administrator Settings** → **Security Settings** → **Activate Unsigned PAK Installation**.

After enabling this, the **"Ignore the PAK file signature checking"** checkbox will appear during the PAK installation wizard.

---

## Install the Management Pack

1. Navigate to **Administration** → **Integrations** → **Repository** tab, and click **Add**.
2. Browse to the `VCFOperationsvCommunity_x.x.x.pak` file. Select:
   - **"Install the PAK file even if it is already installed"** — to override an existing installation.
   - **"Ignore the PAK file signature checking"** — required, since this Management Pack is unsigned.

   Upload the file and click **Next**.
3. Accept the End User License Agreement, then click **Next**.
4. Once installation completes, click **Finish**.

You can review the VCF Operations vCommunity Management Pack under the **Repository** tab.

---

**Next:** [Configuration](configuration.md) — create your first Adapter Instance.
