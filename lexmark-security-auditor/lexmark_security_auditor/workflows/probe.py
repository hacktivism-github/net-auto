from typing import Dict, Any
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from ..ews_client import LexmarkEWSClient

PROBE_PATHS = [
    "/cgi-bin/dynamic/printer/config/secure/auth/manageusers.html?info=normal",
    "/cgi-bin/dynamic/printer/config/secure/auth/users.html?info=normal",
    "/cgi-bin/dynamic/printer/config/secure/auth/usergroups.html?info=normal",
]

OPEN_MARKERS = (
    "Gerenciar contas internas",
    "Adicionar uma conta interna",
    "Configurar grupos para uso com contas internas",
    "Configuração de segurança",
    "Configuração básica de segurança",
    "Internal Accounts",
    "Manage Internal Accounts",
)

AUTH_MARKERS = (
    "access denied",
    "unauthorized",
    "autenticação necessária",
    "authentication required",
    "login",
    "logon",
)

AUTH_HINTS_IN_URL = ("login", "logon", "authenticate", "authfail", "session", "denied")


def probe_open_access(client: LexmarkEWSClient, timeout_s: float) -> Dict[str, Any]:
    timeout_ms = int(timeout_s * 1000)

    for path in PROBE_PATHS:
        url = client.base_url + path
        try:
            resp = client.page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            status = resp.status if resp else None
            final_url = (client.page.url or "").strip()

            if status in (401, 403):
                return {
                    "result": "AUTH",
                    "evidence": f"HTTP {status} on security URL.",
                    "http_status": str(status),
                    "final_url": final_url,
                }

            if any(k in final_url.lower() for k in AUTH_HINTS_IN_URL):
                return {
                    "result": "AUTH",
                    "evidence": f"Redirected to auth-related URL: {final_url}",
                    "http_status": str(status) if status else "na",
                    "final_url": final_url,
                }

            try:
                html = client.page.content()
            except Exception:
                html = ""

            if any(m.lower() in html.lower() for m in OPEN_MARKERS):
                return {
                    "result": "OPEN",
                    "evidence": f"Admin/Security page accessible without auth: {path}",
                    "http_status": str(status) if status else "na",
                    "final_url": final_url,
                }

            if any(m.lower() in html.lower() for m in AUTH_MARKERS):
                return {
                    "result": "AUTH",
                    "evidence": "Authentication hints detected in page content.",
                    "http_status": str(status) if status else "na",
                    "final_url": final_url,
                }

        except PlaywrightTimeoutError:
            continue
        except Exception:
            continue

    return {
        "result": "UNKNOWN",
        "evidence": "Unable to conclusively determine access control.",
        "http_status": "na",
        "final_url": "",
    }

