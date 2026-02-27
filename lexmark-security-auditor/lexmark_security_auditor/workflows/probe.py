# lexmark_security_auditor/workflows/probe.py
from __future__ import annotations

#from http import client
from typing import Dict, Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..ews_client import LexmarkEWSClient

# --- Probe targets (MX + MS) ---
# Order matters: we try "security sensitive" pages first.
PROBE_PATHS = [
    # MX series - internal accounts pages (great for OPEN detection)
    "/cgi-bin/dynamic/printer/config/secure/auth/manageusers.html?info=normal",
    "/cgi-bin/dynamic/printer/config/secure/auth/users.html?info=normal",
    "/cgi-bin/dynamic/printer/config/secure/auth/usergroups.html?info=normal",

    # Common config/security pages (MX + MS often share these)
    "/cgi-bin/dynamic/config/config.html",
    "/cgi-bin/dynamic/config/secure/security.html",
    "/cgi-bin/dynamic/config/secure/ports.html",

    # MS series (password-only flow)
    "/cgi-bin/dynamic/printer/config/secure/auth/lite-password.html",
]

# --- OPEN heuristics ---
OPEN_MARKERS = (
    # PT
    "Gerenciar contas internas",
    "Adicionar uma conta interna",
    "Configurar grupos para uso com contas internas",
    "Configuração de segurança",
    "Configuração básica de segurança",
    "Acesso à porta TCP/IP",
    "Proteção de página da web por senha",

    # EN
    "Internal Accounts",
    "Manage Internal Accounts",
    "Security Settings",
    "Basic Security",
    "TCP/IP Port Access",
)

# If ports page loads and we can see the TCP80 checkbox, that's a strong OPEN signal.
PORTS_OPEN_MARKERS = (
    "vac.255.GUIPORTENABLE.3", # TCP 80 checkbox name/id on many Lexmark EWS
    "TCP 80 (HTTP)",
    "TCP 443 (HTTPS)",
)

# MS lite-password page signals (if accessible without login)
MS_LITE_PASSWORD_MARKERS = (
    "adminPassword1",
    "adminPassword2",
    "ModifyAdmin",
    "Config. de senha",
    "Criar senha do admin",
)

# --- AUTH heuristics ---
AUTH_MARKERS = (
    "access denied",
    "unauthorized",
    "autenticação necessária",
    "authentication required",
    "login",
    "logon",
    "habilite cookis", # seen on some login pages
    "enable cookie", # EN variant
)

# If URL contains these hints after navigation, treat as AUTH.
AUTH_HINTS_IN_URL = (
    "login.html",
    "login_type=",
    "logon",
    "authenticate",
    "authfail",
    "session",
    "denied",
)

# Detect actual login form presence (best signal)
LOGIN_FORM_SELECTORS = (
    "form#login_form",
    "#username",
    "#password",
)


def _looks_like_auth_redirect(final_url: str) -> bool:
    u = (final_url or "").lower()
    return any(h in u for h in AUTH_HINTS_IN_URL)


def _looks_like_login_form(html_lower: str) -> bool:
    # quick, cheap heuristics from page HTML
    return (
        "id=\"login_form\"" in html_lower
        or "name=\"username\"" in html_lower
        or "id=\"username\"" in html_lower
        or "id=\"password\"" in html_lower
)


def probe_open_access(client: LexmarkEWSClient, timeout_s: float) -> Dict[str, Any]:
    timeout_ms = int(timeout_s * 1000)

    for path in PROBE_PATHS:
        url = client.base_url + path
        try:
            resp = client.page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            status = resp.status if resp else None
            final_url = (client.page.url or "").strip()
            final_url_l = final_url.lower()

            # 1) Hard AUTH signals (HTTP codes)
            if status in (401, 403):
                return {
                    "result": "AUTH",
                    "evidence": f"HTTP {status} on security URL.",
                    "http_status": str(status),
                    "final_url": final_url,
                }

            # 2) Redirect/auth hints in URL
            if _looks_like_auth_redirect(final_url):
                return {
                    "result": "AUTH",
                    "evidence": f"Redirected to auth-related URL: {final_url}",
                    "http_status": str(status) if status is not None else "na",
                    "final_url": final_url,
                }

            # 3) Inspect HTML
            try:
                html = client.page.content()
            except Exception:
                html = ""
            html_l = (html or "").lower()

            # 3a) Login form presence (strong AUTH)
            if _looks_like_login_form(html_l):
                return {
                    "result": "AUTH",
                    "evidence": f"Login form detected when accessing: {path}",
                    "http_status": str(status) if status is not None else "na",
                    "final_url": final_url,
                }

            # 3b) Classic OPEN markers (MX)
            if any(m.lower() in html_l for m in OPEN_MARKERS):
                return {
                    "result": "OPEN",
                    "evidence": f"Admin/Security page accessible without auth: {path}",
                    "http_status": str(status) if status is not None else "na",
                    "final_url": final_url,
                }

            # 3c) Ports page OPEN marker (MX + MS)
            if any(m.lower() in html_l for m in PORTS_OPEN_MARKERS):
                return {
                    "result": "OPEN",
                    "evidence": f"TCP/IP ports page accessible without auth: {path}",
                    "http_status": str(status) if status is not None else "na",
                    "final_url": final_url,
                }

            # 3d) MS lite-password page accessible without auth
            if any(m.lower() in html_l for m in MS_LITE_PASSWORD_MARKERS):
                return {
                    "result": "OPEN",
                    "evidence": f"MS password setup page accessible without auth: {path}",
                    "http_status": str(status) if status is not None else "na",
                    "final_url": final_url,
                }

            # 3e) Softer AUTH markers in HTML (fallback)
            if any(m.lower() in html_l for m in AUTH_MARKERS):
                return {
                    "result": "AUTH",
                    "evidence": "Authentication hints detected in page content.",
                    "http_status": str(status) if status is not None else "na",
                    "final_url": final_url,
                }

        except PlaywrightTimeoutError:
            # try next path
            continue
        except Exception:
            # try next path
            continue

    return {
        "result": "UNKNOWN",
        "evidence": "Unable to conclusively determine access control.",
        "http_status": "na",
        "final_url": "",
    }
