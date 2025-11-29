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


Automated default-credential detection and password hardening for Schneider Electric APC UPS devices (NMC3) using [Playwright](https://playwright.dev/python/).

This tool automates end-to-end browser interaction with APC Network Management Card (NMC3) web interfaces in order to:

- Detect UPS devices still using **default credentials** (`apc/apc`)
- Prompt the operator to harden security by changing the password
- Perform a **full UI-driven password update**, including:
  - Login
  - Menu navigation
  - Editing the `apc` Super User password
  - Applying confirmation screens
- Provide clear reporting per device (valid, invalid, unknown)

Developed for large-scale UPS deployments where vendors/suppliers often leave insecure defaults across multiple branch sites.

Published on PyPI for easy installation.

---

## Installation

### Install from PyPI (recommended)

```
pip install apc-ups-security-auditor
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

```
Downloading Chromium 141.0.7390.37 (playwright build v1194) from https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1194/chromium-mac.zip
136.3 MiB [====================] 100% 0.0s
Chromium 141.0.7390.37 (playwright build v1194) downloaded to /Users/me/Library/Caches/ms-playwright/chromium-1194
Downloading Chromium Headless Shell 141.0.7390.37 (playwright build v1194) from https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1194/chromium-headless-shell-mac.zip
85.1 MiB [====================] 100% 0.0s
Chromium Headless Shell 141.0.7390.37 (playwright build v1194) downloaded to /Users/me/Library/Caches/ms-playwright/chromium_headless_shell-1194
Downloading Firefox 142.0.1 (playwright build v1495) from https://cdn.playwright.dev/dbazure/download/playwright/builds/firefox/1495/firefox-mac.zip
96.9 MiB [====================] 100% 0.0s
Firefox 142.0.1 (playwright build v1495) downloaded to /Users/me/Library/Caches/ms-playwright/firefox-1495
You are using a frozen webkit browser which does not receive updates anymore on mac13. Please update to the latest version of your operating system to test up-to-date browsers.
Downloading Webkit playwright build v2140 from https://cdn.playwright.dev/dbazure/download/playwright/builds/webkit/2140/webkit-mac-13.zip
77 MiB [====================] 100% 0.0s
Webkit playwright build v2140 downloaded to /Users/me/Library/Caches/ms-playwright/webkit_mac13_special-2140
Downloading FFMPEG playwright build v1011 from https://cdn.playwright.dev/dbazure/download/playwright/builds/ffmpeg/1011/ffmpeg-mac.zip
1.3 MiB [====================] 100% 0.0s
FFMPEG playwright build v1011 downloaded to /Users/me/Library/Caches/ms-playwright/ffmpeg-1011
```

#### 4. Run the tool
See Usage below

### Install directly from GitHub (bleeding-edge)

```
pip install "git+https://github.com/hacktivism-github/netauto@development#subdirectory=apc-nmc3-ui-scraper"
```
This will pull only the package from the subfolder, not the whole repo.

## Features

- ✔ Headful Playwright browser automation (podes ver cada passo no browser)
- ✔ Login automático com credenciais por defeito (`apc/apc`)
- ✔ Deteção de dispositivos que ainda usam credenciais por defeito
- ✔ Modo interativo (pergunta por host se deve mudar a password)
- ✔ **Modo no-prompt (`--auto-change`)** para hardening em massa sem interações
- ✔ Fluxo completo de mudança de password:
  - Selecção de idioma (English)
  - Logon com `apc/apc`
  - `Configuration → Security → Local Users → Management → apc`
  - Preenchimento de Current / New / Confirm Password
  - Clique em `Next` e `Apply` na página de confirmação
- ✔ Suporte para HTTP e HTTPS (ignora certificados inválidos)
- ✔ **Relatórios em CSV e JSON** (`--report-csv`, `--report-json`) com:
  - host
  - timestamp
  - se usava credenciais por defeito
  - se a password foi alterada
  - estado (ok/timeout/error)
  - mensagem de erro (quando aplicável)

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

## Usage

### 1. Interactive mode (ideal for watching the process)

```
apc-ups-audit --hosts ups_hosts.txt --headful --https --timeout 30
```

Flow:

1. Script asks for a new password (this will replace apc).
2. For each UPS:
    . Opens browser
    . Selects English language
    . Logs in with apc/apc
    . If defaults still work, asks:
   ```
   -> Attempt password change via web UI now? [y/N]:
    ```
3. If you type ```y```, it performs the full password-hardening workflow.

### 2. Automatic mode (no prompts)

To harden all UPS devices without asking anything, use:

```
apc-ups-audit \
  --hosts ups_hosts.txt \
  --https \
  --auto-change
```

If the login using ```apc/apc``` succeeds:
   - The tool __does not ask__
   - It __immediately__ runs the full UI-driven password change
   - Moves to the next UPS automatically

Combine auto-change with headful mode if you want to visually monitor:

```
apc-ups-audit \
  --hosts ups_hosts.txt \
  --https \
  --headful \
  --auto-change
```

### 3. Generate CSV/JSON Reports

```
apc-ups-audit \
  --hosts ups_hosts.txt \
  --https \
  --auto-change \
  --report-csv ups_report.csv \
  --report-json ups_report.json
```

The report includes:

```
| Field                 | Meaning                                |
| --------------------- | -------------------------------------- |
| `host`                | UPS IP/hostname                        |
| `timestamp`           | UTC timestamp                          |
| `default_credentials` | `True` = still using `apc/apc`         |
| `password_changed`    | `True` = password successfully updated |
| `status`              | ok / timeout / error / unknown         |
| `error`               | error message if applicable            |
```

__Example CSV line:__
```
10.111.9.219,2025-11-27T10:15:00Z,True,True,ok,
```

### 4. All available arguments

```
| Parameter        | Description                                   |
|------------------|-----------------------------------------------|
| `--hosts`        | Path to file with UPS list                    |
| `--https`        | Use HTTPS                                     |
| `--headful`      | Show the browser window                       |
| `--timeout`      | Timeout (seconds) for page loads              |
| `--username`     | Username (default: `apc`)                     |
| `--default-pass` | Default password (default: `apc`)             |
| `--new-pass`     | New password (if omitted, asks interactively) |
| `--auto-change`  | Do not prompt; automatically harden devices   |
| `--report-csv`   | Write CSV report                              |
| `--report-json`  | Write JSON report                             |

```

---

## Password Hardening Workflow

When a device still accepts ```apc/apc```, the tool:

1. Logs in

2. Navigates using clicks, not hovers

3. Opens the apc Super User config

4. Fills:

   - Current Password
   - New Password
   - Confirm Password
5. Clicks Next
6. Clicks Apply on confirmation page
7. Confirms success
8. Moves to next host

The entire process is visible in headful mode.

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

## Author

Bruno Teixeira
Network & Security Automation — Angola
