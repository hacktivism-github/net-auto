# APC UPS Security Auditor 

Automated default-credential detection and password hardening for Schneider Electric APC UPS devices (NMC3) using Playwright.

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

---

## Features

- ✔ Headful Playwright browser automation (you can visually watch every step)
- ✔ Securely logs in using default credentials
- ✔ Detects whether defaults are still accepted
- ✔ Prompts per-device for password hardening
- ✔ Fully automates:
  - Setting English language
  - Logging in
  - Clicking through menus (no hovers)
  - Navigating to User Management → apc
  - Filling Current/New/Confirm password
  - Clicking "Next" and the final "Apply"
- ✔ Supports `http` or `https`
- ✔ Per-device summary at the end
- ✔ Timeout control for slow devices
- ✔ Ignores expired/invalid SSL certificates

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

```bash
pip install playwright
playwright install
