# Lexmark Security Auditor (EWS)

<p align="center">
  <a href="https://pypi.org/project/lexmark-security-auditor/">
    <img src="https://img.shields.io/pypi/v/lexmark-security-auditor.svg?cacheSeconds=300" alt="PyPI Version">
  </a>
  <a href="https://pypi.org/project/lexmark-security-auditor/">
    <img src="https://img.shields.io/pypi/pyversions/lexmark-security-auditor.svg?cacheSeconds=300" alt="Python Versions">
  </a>
  <a href="https://github.com/hacktivism-github/netauto/blob/development/LICENSE">
    <img src="https://img.shields.io/github/license/hacktivism-github/netauto.svg" alt="MIT License">
  </a>
</p>


Enterprise-grade security auditing and hardening tool for Lexmark MX710 (and compatible models) via Embedded Web Server (EWS).

Built with Playwright + Python, this tool enables controlled, automated security enforcement at scale.

## Version 0.2.0 Highlights

✅ MX Series (Username + Password authentication)

✅ MS Series (Password-Only authentication)

✅ Automatic model detection (MX vs MS)

✅ MS Function Protection hardening (Admin menus protection)

✅ Idempotent execution

✅ Session-aware login handling

✅ Structured CSV/JSON reporting

✅ Modular workflow architecture

## Overview

The __Lexmark Security Auditor__ was developed to:

- Audit administrative exposure on Lexmark printers

- Enforce Basic Security (authentication enforcement)

- Harden MS password-only devices

- Protect administrative menus (MS Series)

- Disable insecure services (TCP 80 – HTTP)

- Operate safely at scale across multiple devices

- Provide compliance-ready reporting

## Key Features
### Security Audit

- Detects if admin/security pages are:

    - OPEN

    - AUTH required

    - UNKNOWN

- Detection based on:

    - Sensitive admin endpoints

    - Login redirects

    - HTTP status codes

    - Page content heuristics

## Basic Security Enforcement

### MX Series (Username + Password)

Automates:

1. ```/cgi-bin/dynamic/config/config.html```

2. Navigate to Security settings

3. Set:

    - Authentication Type: UsernamePassword

    - Admin ID

    - Password

4. Apply configuration

---

### MS Series (Password-Only Mode)

Automates:

1. ```/cgi-bin/dynamic/printer/config/secure/auth/lite-password.html```

2. Set Admin Password

3. Detect login enforcement

4. Re-authenticate (password-only)

5. Harden administrative functions:

    - Remote Security Menu

    - Remote Config Menu

    - Network/Ports Menu

    - Firmware Updates

    - Remote Management

    - Import/Export Config

    - IPP (Internet Printing Protocol)

    - And more (model-dependent)

✔ Automatically selects strongest available protection

✔ Avoids selecting "Disabled" unless explicitly needed

✔ Fully idempotent

---
## HTTP Hardening (TCP 80 Disable)

Authenticates (MX or MS models)

Navigates to:

```
/cgi-bin/dynamic/config/secure/ports.html
```
Unchecks:
```
TCP 80 (HTTP)
```

- Submits

- Verifies

- Logs out

✔ Idempotent
✔ Safe to re-run
✔ Login-aware

---
## Architecture 
```
lexmark_security_auditor/
│
├── cli.py
├── runner.py
│
├── models.py
├── reporting.py
├── ews_client.py
│
└── workflows/
    ├── probe.py
    ├── identify.py
    ├── auth.py
    ├── ports.py
    ├── model.py
    ├── basic_security.py              # MX
    ├── basic_security_ms.py           # MS password-only
    └── basic_security_ms_templates.py # MS function protection
```
---
| Module                           | Responsibility                   |
| -------------------------------- | -------------------------------- |
| `runner.py`                      | Orchestration & decision logic   |
| `identify.py`                    | Model detection (MX vs MS)       |
| `probe.py`                       | Exposure detection               |
| `auth.py`                        | Session handling & login         |
| `basic_security.py`              | MX security enforcement          |
| `basic_security_ms.py`           | MS password-only enforcement     |
| `basic_security_ms_templates.py` | MS function protection hardening |
| `ports.py`                       | TCP 80 disable logic             |
| `ews_client.py`                  | EWS navigation abstraction       |
| `reporting.py`                   | CSV/JSON export                  |

---

### Arquitetura do Código (Package / Components)

![Architecture Diagram ](https://raw.githubusercontent.com/hacktivism-github/netauto/development/lexmark-security-auditor/docs/arch-2026-02-27-075812.png)

### Execution Flow (w/ login + disable)

Execution Flow

1. Probe exposure

2. Detect model (MX / MS)

3. Apply Basic Security

4. (MS) Harden function templates

5. Disable HTTP (if requested)

6. Generate report

![Execution Flow (w/ login + disable) ](https://raw.githubusercontent.com/hacktivism-github/netauto/development/lexmark-security-auditor/docs/arch-2026-02-27-081049.png)

---

## Installation
```
pip install lexmark-security-auditor==0.2.0
```
Development mode:

```
pip install -e .
```

This enables:
```
lexmark-audit ...
```

Or:

```
python -m lexmark_security_auditor.cli ...
```
---

## Usage Examples

__Note:__ If you're on Powershell replace the ``` \ ``` by ``` ` ```

### Audit Only
```
lexmark-audit \
  --hosts printers.txt \
  --https
```
### Apply Basic Security
```
lexmark-audit \
  --hosts printers.txt \
  --https \
  --apply-basic-security \
  --new-admin-user <ID do usuário> \
  --new-admin-pass "Senha"
  ```

### Disable HTTP (Authenticated)
```
lexmark-audit \
  --hosts printers.txt \
  --https \
  --disable-http \
  --auth-user <ID do usuário> \
  --auth-pass "Senha"
```
### With Reporting
```
lexmark-audit \
  --hosts printers.txt \
  --https \
  --disable-http \
  --auth-user <ID do usuário> \
  --auth-pass "Senha" \
  --report-csv report.csv
  ```
---
## Output Fields (CSV/JSON)

| Field                  | Description             |
| ---------------------- | ----------------------- |
| host                   | Printer IP              |
| probe_result           | OPEN / AUTH / UNKNOWN   |
| evidence               | Detection details       |
| model                  | Detected model          |
| family                 | MX / MS                 |
| basic_security_applied | Boolean                 |
| http_disabled          | Boolean                 |
| status                 | ok / timeout / error    |
| error                  | Error message           |
| extra                  | Model-specific metadata |

For MS devices, extra may include:

- ms_templates_ok

- ms_templates_changed

- ms_templates_total

---

## Security Considerations

- Credentials are passed via CLI (consider secure vault integration)

- HTTPS recommended

- Designed for internal network use

- Session cookies handled via Playwright context

- Idempotent operations to avoid configuration drift

## Design Principles

- Modular

- Idempotent

- Stateless between hosts

- Session-aware

- Explicit authentication

- Clear separation of concerns

- Enterprise reporting ready

## Requirements

- Python 3.9+

- Playwright

- Chromium (installed via playwright install)

## Roadmap (Future Enhancements)

- Vault integration (HashiCorp)

- SNMP configuration hardening

- Parallel host execution

- Compliance summary dashboard

- Unit test coverage

- Docker container image

## Disclaimer

This tool is provided __"as is"__, without warranty of any kind, express or implied.

```lexmark-security-auditor``` performs automated configuration changes on network-connected devices (e.g., enabling Basic Security, modifying TCP/IP port access settings). Improper use may result in:

- Loss of remote access to devices

- Service disruption

- Configuration lockout

- Network communication impact

The author assumes __no liability__ for any damage, data loss, service interruption, or operational impact resulting from the use of this software.

### Intended Use

This tool is intended for:

- Authorized administrators

- Controlled environments

- Lab validation prior to production rollout

- Security hardening under change-management processes

You are solely responsible for:

- Ensuring proper authorization before accessing devices

- Validating configuration changes in a test environment

- Backing up device configurations prior to execution

- Following your organization's change control policies

### Security Responsibility

Disabling TCP 80 (HTTP) and enforcing authentication may restrict access methods. Ensure that:

- HTTPS (TCP 443) remains enabled

- Valid administrative credentials are known

- Recovery procedures are documented

### No Vendor Affiliation

This project is not affiliated with, endorsed by, or supported by Lexmark International, Inc.

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