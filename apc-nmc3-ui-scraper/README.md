# APC UPS Security Auditor

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

This tool automates browser interaction with the APC Network Management Card web interface to:

- Detect UPS devices still using **default credentials** (`apc/apc`)
- Change the Super User default password through the UI
- Create and enable a new administrator account
- Navigate menu structures exactly as a human operator
- Provide clear CSV/JSON reporting per device

Developed for large-scale UPS deployments where vendors/suppliers often leave insecure defaults across multiple branch sites.

Published on PyPI for easy installation.

---

## Installation

### Install from PyPI (recommended)

```
pip install apc-ups-security-auditor==0.1.4
```
Then install Playwright browsers:
```
playwright install
```

### Install from Source

If you want to run the latest development version directly from GitHub, you can install the package from the `apc-nmc3-ui-scraper` subdirectory of the repository.

#### 1. Clone the repository

```
git clone https://github.com/hacktivism-github/netauto.git
cd netauto/apc-nmc3-ui-scraper
```

#### 2. Create and activate a virtual environment (recommended)

```
python3 -m venv .venv
source .venv/bin/activate     # Linux/macOS
```
#### or
```
.\.venv\Scripts\activate      # Windows PowerShell
```
#### 3. Install the project in editable mode

```
pip install -e .
```
This installs the CLI entry point:
```
apc-ups-audit --help
```
```
playwright install
```

#### 4. Run the tool
See Usage below

### Install directly from GitHub (bleeding-edge)

```
pip install "git+https://github.com/hacktivism-github/netauto@development#subdirectory=apc-nmc3-ui-scraper"
```
This will pull only the package from the subfolder, not the whole repo.

---

## Features

### Default Credential Audit

- Attempts login with `apc/apc`
- Detects whether default credentials are still accepted

### Automated Password Hardening

- UI-driven navigation:
  - Configuration → Security → Local Users → Management → apc
  - Fill Current / New / Confirm password fields
  - “Next” → “Apply” confirmation page
- Works reliably across multiple firmware versions

### Create a New Administrator Account (Phase 1)

Use:

```
--create-admin
--new-admin-user "<your admin user>"
--new-admin-pass "<password>"
```

The script will:

- Navigate to *Configuration → Security → Local Users → Management*
- Click **Add User**
- **Tick the “Enable” checkbox automatically**
- Fill username & password
- Select **Super User**
- Click **Next → Apply** until fully submitted

### Auto Mode (`--auto`)

Run fully non-interactive:
```
--auto
```
Good for large deployments.

### CSV / JSON Reporting

Use:

```
--report-csv results.csv
--report-json results.json
```
Each row includes:

- Host
- Timestamp
- Login success
- Admin creation success
- New admin username
- Error state

---

## CLI Usage

```
apc-ups-audit --hosts <file> [options]
```

### Most useful flags:

```
| Flag                 | Description                           |
| -------------------- | ------------------------------------- |
| `--hosts FILE`       | List of UPS IPs (one per line)        |
| `--create-admin`     | Create a new admin account            |
| `--new-admin-user`   | Username for the new account          |
| `--new-admin-pass`   | Password for the new account          |
| `--current-user`     | User to authenticate as (e.g., `apc`) |
| `--current-pass`     | Password for existing admin           |
| `--auto`             | Non-interactive mode                  |
| `--headful`          | Show the browser window               |
| `--https`            | Use HTTPS instead of HTTP             |
| `--report-csv FILE`  | Output results as CSV                 |
| `--report-json FILE` | Output results as JSON                |
```

Full help:

```
apc-ups-audit --help
```

Example: Create new admin user on all hosts

macOS, Linux:
```
apc-ups-audit \
  --hosts ups_hosts.txt \
  --https \
  --headful \
  --current-user apc \
  --current-pass "<hardened_apc_password>" \
  --create-admin \
  --new-admin-user <your admin user> \
  --new-admin-pass "<StrongPasswordHere>" \
  --auto \
  --report-csv phase1_create_admin.csv
```

Powershell:
```
(.venv) PS> apc-ups-audit `
  --hosts ups_hosts.txt `
  --https `
  --headful `
  --current-user apc `
  --current-pass "<hardened_apc_password>" `
  --create-admin `
  --new-admin-user "<your admin user>" `
  --new-admin-pass "<StrongPass>" `
  --auto `
  --report-csv phase1_create_admin.csv
```

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

## Hosts File Format

```
10.x.x.x
172.16.x.x
192.168.x.x
```
You may include comments:
```
# Benguela Branch UPS
10.x.x.x
```

---

## Demo

```
I'll be adding the demo soon!
```
---

## Disclaimer

This tool modifies administrator credentials on APC UPS devices.
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

PRs, issues, and feature requests are welcome!

---

## Author

Bruno Teixeira
Network & Security Automation — Angola
