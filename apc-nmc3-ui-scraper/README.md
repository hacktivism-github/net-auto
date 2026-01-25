# APC UPS Security Auditor (NMC3)

<p align="center">
  <a href="https://pypi.org/project/apc-ups-security-auditor/">
    <img src="https://img.shields.io/pypi/v/apc-ups-security-auditor.svg" alt="PyPI Version">
  </a>
  <a href="https://pypi.org/project/apc-ups-security-auditor/">
    <img src="https://img.shields.io/pypi/pyversions/apc-ups-security-auditor.svg" alt="Python Versions">
  </a>
  <a href="https://github.com/hacktivism-github/netauto/blob/development/LICENSE">
    <img src="https://img.shields.io/github/license/hacktivism-github/netauto.svg" alt="MIT License">
  </a>
</p>



Automated security auditing and UI-driven hardening for Schneider Electric APC UPS devices (NMC3) using [Playwright](https://playwright.dev/python/).

<!-- This tool automates browser interaction with the Schneider/APC NMC3 web interface to:

- Detect if default credentials (`apc`/`apc`) still work

- Automatically harden the default password

- Create a new Super User / Administrator account

- Failover to non-default login when needed

- Generate CSV/JSON reports

- Run in headless (fast) or headful (visual) modes

Developed for large-scale UPS deployments where vendors/suppliers often leave insecure defaults across multiple branch sites.

Published on PyPI for easy installation. -->

This tool automates browser interaction with the Schneider/APC NMC3 Web UI to enforce security baselines at scale — without relying on undocumented APIs.

Designed for large UPS deployments where insecure defaults are commonly left unchanged across branch sites, data centers, and industrial environments.

---

## Architecture & Design

This project follows a **UI-first, workflow-driven automation architecture** designed specifically for APC NMC3 devices, where no stable public API exists.

The architecture document explains:

- Why UI automation was chosen over APIs
- How login, hardening, and SNMPv3 enforcement are orchestrated
- How safety, idempotency, and auditability are guaranteed
- How the SNMPv3 hardening workflow is structured internally

 **Full architecture documentation:** 
 I'm working on it!
 <!-- [`docs/architecture.md`](docs/architecture.md) -->

---

## Features
<!-- ✔ Detect if default credentials still work

If the UPS still accepts `apc`/`apc`, the tool can automatically:

- change the password of the `apc` account

- create a new admin user

- record results in a report

✔ Harden the apc account password

Provide a strong new password once; the tool applies it to all hosts.

✔ Create new admin accounts

Custom username + password:

```--create-admin --new-admin-user <your admin username> --new-admin-pass "your hardened password"```

✔ Automatic mode (```--auto```)

Runs fully unattended, skipping all user prompts.

✔ Works headless or headful

- Headless (default) → fastest

- Headful → watch every step in a real browser

✔ CSV/JSON reporting

Ideal for audits, change-control logs, and compliance evidence.

✔ Check-only mode

Verify a single UPS without making any changes. -->

✔ __Credential & Account Security__

- Detect if default credentials (```apc``` / ```apc```) still work

- Automatically harden the default ```apc``` password

- Create a new __Super User__ / __Administrator__ account

- Failover to a non-default login when required

✔ __SNMPv3 Security Hardening (v0.2.0)__

- Fully automated __SNMPv3 user profile configuration__

- Supports:

    - Authentication protocols: ```SHA```, ```MD5```

    - Privacy protocols: ```AES```, ```DES```

- Automates __SNMPv3 Access Control__:

    - Enables SNMPv3 access

    - Binds SNMPv3 users to a specific __NMS IP__ / __Host__

- Optional __SNMPv1 disablement__ (only after SNMPv3 is confirmed working)

✔ __Automation & Reporting__

- Headless (fast) or Headful (visual) execution

- Fully unattended mode (```--auto```)

- CSV and JSON reporting for audits and compliance

- Check-only mode (read-only validation)

---
## What’s New in v0.2.0
__Major Enhancements__

- End-to-end SNMPv3 hardening via NMC3 Web UI

- Unified SNMP hardening workflow

- SNMPv3 Access Control automation with NMS binding

- Optional SNMPv1 decommissioning

- Improved Playwright selector stability and timing

- Extended CSV/JSON reports with SNMPv3 fields

This release transforms the tool from __credential hygiene__ into a __full monitoring-security enforcement utility__.

---

## Installation
__Option 1__ — Install from PyPI (preferred)
```
pip install apc-ups-security-auditor==0.2.0
```

This installs the CLI tool:
```
apc-ups-audit --help
```

__Option 2__ — Install from Source (development version)

If you want to run the latest development version directly from GitHub, you can install the package from the `apc-nmc3-ui-scraper` subdirectory of the repository.

#### 1. Clone the repository
```
git clone https://github.com/hacktivism-github/netauto.git
cd netauto/apc-nmc3-ui-scraper
```
#### 2. Create and activate a virtual environment (recommended)
```
python3 -m venv .venv
```
```
source .venv/bin/activate    # Linux/macOS
```
#### or
```
.\.venv\Scripts\activate      # Windows PowerShell
```
#### 3. Install the project in editable mode

```
python -m pip install --upgrade pip
pip install -e .
```
Install Playwright browsers:
```
playwright install
```
#### 4. Run the tool
See Usage below

__Option 3__ — Install directly from GitHub (bleeding-edge)

```
pip install "git+https://github.com/hacktivism-github/netauto@development#subdirectory=apc-nmc3-ui-scraper"
```
This will pull only the package from the subfolder, not the whole repo.

---

## Usage
- Prepare a list of UPS hosts (ups_hosts.txt):
```
10.x.x.x
172.16.x.x
192.168.x.x
...
```
__Note:__ use **`** (grave accent) to change the line (if using Windows PowerShell).

- Basic command (recommended)

Try default `apc`/`apc` → harden → create new admin → next host.
```
apc-ups-audit \
  --hosts ups_hosts.txt \
  --https \
  --create-admin \
  --new-admin-user <your admin user> \
  --auto \
  --report-csv results.csv
```

**This performs:**

1. Try login with `apc`/`apc`

2. If default credentials work →

   - harden `apc` password

   - create admin user

3. If default creds fail → automatically try fallback (`--current-user`, `--current-pass`)

4. Move to next host automatically

5. Save results to CSV

---

- Headful mode (watch the automation)
```
apc-ups-audit \
  --hosts ups_hosts.txt \
  --https \
  --create-admin \
  --new-admin-user <your admin user> \
  --auto \
  --headful
  ```

  ---

- Fully non-interactive (no prompts)
```
apc-ups-audit \
  --hosts ups_hosts.txt \
  --https \
  --auto \
  --create-admin \
  --new-admin-user <your admin user> \
  --new-admin-pass "your admin secure password" \
  --apc-new-pass "your apc hardened password" \
  --current-user <your current user> \
  --current-pass "your current password"
  ```

PowerShell:
```
apc-ups-audit.exe `
  --hosts ups_hosts.txt `
  --https `
  --headful `
  --apc-new-pass "Enter your hardened password" `
  --create-admin `
  --new-admin-user <Enter you desired admin user> `
  --new-admin-pass "Enter your hardened password" `
  --current-user <your current user> `
  --current-pass "your current password" `
  --auto `
  --report-csv report.csv

```

  ---

- Fallback login example

If `apc`/`apc` fails, try another known user:
```
apc-ups-audit \
  --hosts ups_hosts.txt \
  --https \
  --current-user <your current user> \
  --current-pass "your current password" \
  --create-admin \
  --new-admin-user <your admin user> \
  --auto
  ```

  ---
  
  - Check-only mode (no changes)

Verify a single UPS without modifying anything:

```
apc-ups-audit \
  --check-only <IP Address> \
  --https \
  --headful
```

__Output example:__
```
[RESULT] <IP Address>: default credentials NOT valid
```

This mode is ideal for:

- Spot checks
- Post-remediation validation
- Audit sampling

  ## Example Output (Headful + Auto)

```
(.venv) PS C:\Users\<user>\netauto\apc-nmc3-ui-scraper> apc-ups-audit.exe `
>>   --hosts ups_hosts.txt `
>>   --https `
>>   --headful `
>>   --apc-new-pass "Your hardened password" `
>>   --create-admin `
>>   --new-admin-user <your admin user> `
>>   --new-admin-pass "Your hardened password" `
>>   --auto `
>>   --report-csv report.csv
Loaded 2 host(s) from ups_hosts.txt
Using scheme: HTTPS
Browser will be HEADFUL (visible).


==============================================================
[*] Processing host: <IP Address>
==============================================================
    -> Opening https://<IP Address>/ ...
    -> Trying default credentials apc/apc …
    [*] Login page ready.
    [*] Set language to English.
    [*] Filled username and password.
    [*] Clicked Log On, waiting for home page...
    [✓] Login successful.
    [✓] Default login succeeded as apc. Hardening password and creating admin if requested…
    -> Hardening password for 'apc' on <IP Address>…
    [*] Navigating to User Management (click-only navigation)...
      -> Clicking 'Configuration'
      -> Clicking 'Security'
      -> Clicking 'Local Users'
      -> Clicking 'Management' (Local Users / userman.htm)
      -> Clicking user 'apc' under Super User Management
      -> Filling Current / New / Confirm Password fields...
      -> Clicking 'Next' (or fallback 'Apply')...
      -> Waiting for final confirmation page...
      -> Clicking FINAL 'Apply'
    [✓] Password change fully confirmed.
    [✓] Default user password hardened successfully.
    -> Creating new admin user 'your admin user' …
    [*] Navigating to Local Users to create admin user...
      -> Clicking 'Configuration'
      -> Clicking 'Security'
      -> Clicking 'Local Users'
      -> Opening 'Management' (user list)
      -> Clicking 'Add User'…
      -> Now on page: https://<IP Address>/NMC/uXfKb-aEKZloM5mXKqZlBg/usercfg.htm?user=
      -> Enabling new user (ticking 'Enable' checkbox)…
      -> Filling new admin user: your admin user
      -> Filling password fields…
      -> Setting user role (Super User / Administrator) if possible…
      -> Clicking 'Next'…
      -> On confirmation page, clicking 'Apply'…
    [✓] New admin user creation flow completed (Next + Apply).
    [✓] Admin user created successfully.
```
It automatically moves on to the next host as listed on the ups_hosts.txt file
```
[✓] CSV report written to report.csv

[*] All hosts processed.
```
If the default username/password are no longer accepted, it will attempt the fallback if provided (`--current-user`, `--current-pass`) otherwise it will skip to the next host or eventually exit. 

```
==============================================================
[*] Processing host: <IP Address>
==============================================================
    -> Opening https://<IP Address>/ ...
    -> Trying default credentials apc/apc …
    [*] Login page ready.
    [*] Set language to English.
    [*] Filled username and password.
    [*] Clicked Log On, waiting for home page...
    [-] Login did not reach home.htm – default credentials probably NOT valid.
    [-] Default login failed or undetermined. Trying fallback credentials (if configured)…
    [-] No fallback credentials provided; skipping host.

[✓] CSV report written to report.csv

[*] All hosts processed.
```
--- 

## SNMPv3 Hardening (v0.2.0)
```
apc-ups-audit \
  --hosts ups_hosts.txt \
  --https \
  --snmpv3-enable \
  --snmpv3-user <Your SNMPv3 username> \
  --snmpv3-auth-proto SHA \
  --snmpv3-priv-proto AES \
  --snmpv3-auth-pass "<Your Auth Passphrase>" \
  --snmpv3-priv-pass "<Your Priv Passphrase>" \
  --snmpv3-nms <Your NMS IP Address> \
  --disable-snmpv1 \
  --auto \
  --report-csv snmpv3_hardened.csv
  ```
---

## SNMPv3 Hardening Workflow

__Logical Flow__

Login to UPS 
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;</br>
Navigate: Configuration → Network → SNMPv3 → User Profiles
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;</br>
Open SNMPv3 Profile (e.g. apc snmp profile1)
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;</br>
Set User Name, Auth Protocol, Privacy Protocol, Passphrases
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;</br>
Apply & Return to User Profiles
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;</br>
Navigate: Configuration → Network → SNMPv3 → Access Control
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;</br>
Select SNMPv3 User
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;</br>
Enable Access + Set NMS IP/Host
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;</br>
Apply Changes
<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&darr;</br>
(Optional) Disable SNMPv1

---


  ## Command Line Options

 | __Flag__                              | __Purpose__                                                                   |
 | ------------------------------------- | ----------------------------------------------------------------------------- |
 | `-h`, `--help`                        | show this help message and exit                                               |
 | `--version`                           | show program's version number and exit                                        |
 | `--hosts` HOSTS                       | Path to file containing UPS IPs/hostnames (one per line).                     |
 | `--check-only`                        | Verify a single host, no changes                                              |
 | `--https`                             | Use HTTPS instead of HTTP to open the web UI.                                 |
 | `--timeout` TIMEOUT                   | Timeout (seconds) for page loads and login (default: 30).                     |
 | `--headful`                           | Run the browser in headful mode (visible window). Default is headless.        |
 | `--default-user` DEFAULT_USER         | Default username to test first (default: apc).                                |
 | `--default-pass` DEFAULT_PASS         | Default password to test first (default: apc).                                |
 | `--apc-new-pass` APC_NEW_PASS         | New hardened password to set for the default user (e.g. 'apc') when default   |
 |                                       | credentials are still valid. If omitted and not in --auto, you will be        |
 |                                       | prompted once.                                                                |
 | `--current-user` CURRENT_USER         | Fallback username to use when default login fails (default: apc).             |
 | `--current-pass` CURRENT_PASS         | Fallback password to use when default login fails. If omitted and             |
 |                                       | current-user != default-user, you may be prompted (except when using --auto). |
 | `--create-admin`                      | Create a new Super User admin account on hosts where login succeeds.          |
 | `--new-admin-user` NEW_ADMIN_USER     | New admin username to create (used with --create-admin).                      |
 | `--new-admin-pass` NEW_ADMIN_PASS     | New admin password to set (used with --create-admin). If omitted and not in   |
 |                                       | --auto, you will be prompted.                                                 |
 | `--auto`                              | Run without interactive prompts for admin creation (non-interactive mode).    |
 | `--report-csv` REPORT_CSV             | Path to CSV report file to write scan results (optional).                     |
 | `--report-json` REPORT_JSON           | Path to JSON report file to write scan results (optional).                    |
 | __Version: 0.2.0__                                                                                                    |
 | `--snmpv3-enable`                     | Configure and enable SNMPv3 on hosts where login succeeds.                    |
 | `--snmpv3-profile` SNMPV3_PROFILE     | SNMPv3 profile entry name to click in the UI table                            |
 |                                       | (default: 'apc snmp profile1').                                               |
 | `--snmpv3-user` SNMPV3_USER           | SNMPv3 User Name to set inside the profile AND to click in Access Control     |
 | `--snmpv3-auth-proto` {SHA,MD5,None}  | SNMPv3 authentication protocol (default: SHA).                                |
 | `--snmpv3-priv-proto` {AES,DES,None}  | SNMPv3 privacy protocol (default: AES).                                       |
 | `--snmpv3-auth-pass` SNMPV3_AUTH_PASS | SNMPv3 authentication passphrase                                              |
 |                                       | (prompted if omitted and not --auto, required if auth-proto != None).         |
 | `--snmpv3-priv-pass` SNMPV3_PRIV_PASS | SNMPv3 privacy passphrase                                                     |
 |                                       | (prompted if omitted and not --auto, required if priv-proto != None).         |
 | `--snmpv3-nms` SNMPV3_NMS             | NMS IP/Host Name to allow in SNMPv3 access control                            |
 | `--disable-snmpv1`                    | Disable SNMPv1 after SNMPv3 access control was successfully enabled.          |
     

---

## Supported Devices

This tool is designed for:

- Schneider Electric **APC UPS Network Management Card 3 (NMC3)**
- Web UI using pages like:
  - `logon.htm`
  - `home.htm`
  - `userman.htm`
  - `usercfg.htm`
  - `usrcnfrm.htm`

Devices tested include:

- APC Easy UPS 3S
- APC Smart-UPS with NMC3 firmware 2022–2025

---

## Requirements

- Python 3.9 or later
- Playwright

Install dependencies:

```
pip install playwright
playwright install
```

---

 ## Demo

```
I'll be adding the demo soon!
```
---

## Disclaimer

<!-- This tool modifies administrator credentials on APC UPS devices. -->
This tool performs live security configuration changes on UPS devices.
Use responsibly and ensure:
   - You have explicit authorization
   - You follow organizational security policies
   - New passwords are stored securely
   - Changes are properly documented

The author is not responsible for misuse or misconfiguration.

---

## License

This project is licensed under the **MIT License**.  
See [`LICENSE`](https://github.com/hacktivism-github/netauto/blob/development/LICENSE) for details.

---

## Contributions

Pull requests, issues, and feature requests are welcome!

---

## Author

Bruno Teixeira
Network & Security Automation — Angola
















