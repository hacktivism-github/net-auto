# lexmark_security_auditor/runner.py

from __future__ import annotations

from typing import List, Optional, Tuple

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .models import CheckResult, now_utc_iso
from .ews_client import LexmarkEWSClient

from .workflows.probe import probe_open_access
from .workflows.ports import disable_http_tcp80
from .workflows.auth import ensure_authenticated_session, logout

# Prefer the more precise detector (MX710 / MS811 etc.)
from .workflows.identify import identify_model

# MX workflow
from .workflows.basic_security import apply_basic_security

# MS workflow (password-only)
from .workflows.basic_security_ms import apply_basic_security_ms_password_only

# MS templates hardening (dropdowns)
# (you must have created this file as discussed)
from .workflows.basic_security_ms_templates import harden_ms_function_protection


def normalize_base_url(host: str, https: bool) -> str:
    host = host.strip()
    if host.startswith(("http://", "https://")):
        return host.rstrip("/")
    scheme = "https" if https else "http"
    return f"{scheme}://{host}".rstrip("/")


def _derive_login_credentials(
    family: Optional[str],
    apply_basic: bool,
    new_user: Optional[str],
    new_pass: Optional[str],
    auth_user: Optional[str],
    auth_pass: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Decide what credentials to use for authenticated actions (e.g., disable HTTP).
    Priority:
      1) If apply_basic ran, prefer the newly set creds:
         - MS: username="" (password-only), password=new_pass
         - MX: username=new_user, password=new_pass
      2) Else use provided auth_user/auth_pass (existing creds)
      3) Else None (will only work if device is OPEN)
    """
    if apply_basic and new_pass:
        if (family or "").upper() == "MS":
            return ("", new_pass)
        # MX or other that uses username+password
        if new_user:
            return (new_user, new_pass)

    if auth_user and auth_pass:
        return (auth_user, auth_pass)

    return (None, None)


def run(
    hosts: List[str],
    https: bool,
    headful: bool,
    timeout: float,
    debug_html: bool,
    apply_basic: bool,
    disable_http: bool,
    new_user: Optional[str],
    new_pass: Optional[str],
    auth_user: Optional[str] = None,
    auth_pass: Optional[str] = None,
) -> List[CheckResult]:

    scheme = "https" if https else "http"
    results: List[CheckResult] = []

    print(f"Using scheme: {scheme.upper()}")
    print(f"Browser will be {'HEADFUL (visible)' if headful else 'headless'}.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)

        for host in hosts:
            base_url = normalize_base_url(host, https=https)

            print("\n==============================================================")
            print(f"[*] Processing host: {host}")
            print("==============================================================")
            print(f"    -> Opening {base_url}/ ...")

            res = CheckResult(host=host, timestamp=now_utc_iso(), scheme=scheme, extra={})

            # Context per host
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            client = LexmarkEWSClient(
                page,
                base_url=base_url,
                timeout_s=timeout,
                debug_html=debug_html,
            )

            try:
                # -------------------------
                # Probe
                # -------------------------
                print("    -> Probing admin/security URLs...")
                out = probe_open_access(client, timeout_s=timeout)

                res.probe_result = out["result"]
                res.evidence = out["evidence"]
                res.http_status = out["http_status"]
                res.final_url = out["final_url"]

                print(f"\n[RESULT] {host}: {res.probe_result}")
                print(f"         Evidence: {res.evidence}")

                # -------------------------
                # Identify model/family (best effort)
                # -------------------------
                model_info = identify_model(client)
                res.extra["model"] = model_info.get("model")
                res.extra["family"] = model_info.get("family")
                if "evidence" in model_info:
                    res.extra["model_evidence"] = model_info.get("evidence")

                family = (model_info.get("family") or "").upper()

                # -------------------------
                # Apply Basic Security (recommended to do before disable-http if both flags)
                # -------------------------
                if apply_basic:
                    print("    [*] Applying Basic Security workflow...")

                    basic_ok = False

                    if family == "MS":
                        basic_ok = apply_basic_security_ms_password_only(
                            client,
                            admin_password=new_pass or "",
                        )
                        res.basic_security_applied = bool(basic_ok)

                        if basic_ok:
                            # After setting admin password, protect menus/functions
                            # Login is password-only (username empty)
                            did_login = ensure_authenticated_session(
                                client,
                                username="",
                                password=new_pass or "",
                                target_path="/cgi-bin/dynamic/printer/config/secure/auth/lite-password.html",
                            )

                            if did_login:
                                out2 = harden_ms_function_protection(client)
                                res.extra["ms_templates_ok"] = out2.get("ok", False)
                                res.extra["ms_templates_changed"] = out2.get("changed", 0)
                                res.extra["ms_templates_total"] = out2.get("total", 0)
                                logout(client)
                            else:
                                res.extra["ms_templates_ok"] = False
                                res.extra["ms_templates_error"] = "could_not_login_password_only"

                    else:
                        # Default to MX-style username+password
                        basic_ok = apply_basic_security(
                            client,
                            username=new_user or "",
                            password=new_pass or "",
                        )
                        res.basic_security_applied = bool(basic_ok)

                    print("    [✓] Basic Security workflow applied." if basic_ok else "    [!] Failed to apply Basic Security workflow.")

                # -------------------------
                # Disable HTTP (TCP/80)
                # -------------------------
                if disable_http:
                    print("    [*] Disabling HTTP (TCP/80)...")

                    # Decide which creds to use for this action
                    login_user, login_pass = _derive_login_credentials(
                        family=family,
                        apply_basic=apply_basic,
                        new_user=new_user,
                        new_pass=new_pass,
                        auth_user=auth_user,
                        auth_pass=auth_pass,
                    )

                    ok_http = False
                    did_login = False

                    target_after_login = "/cgi-bin/dynamic/config/secure/ports.html"

                    if login_pass is not None and login_user is not None:
                        # Authenticated attempt (works for both MX and MS; MS uses username="")
                        print("    [*] Ensuring authenticated session (form-based login)...")
                        did_login = ensure_authenticated_session(
                            client,
                            username=login_user,
                            password=login_pass,
                            target_path=target_after_login,
                        )

                        if did_login:
                            ok_http = disable_http_tcp80(client)
                            logout(client)  # best effort
                        else:
                            ok_http = False
                    else:
                        # No creds: only works if device is OPEN
                        ok_http = disable_http_tcp80(client)

                    res.http_disabled = bool(ok_http)

                    if ok_http:
                        print("    [✓] HTTP disabled (or already disabled).")
                    else:
                        url_now = (client.page.url or "").lower()
                        if "login.html" in url_now:
                            print("    [!] Failed to disable HTTP (authentication required / bounced to login).")
                        else:
                            print("    [!] Failed to disable HTTP (see debug dumps for selector/page issues).")

            except PlaywrightTimeoutError:
                res.status = "timeout"
                res.error = "timeout"
                print(f"    [!] TIMEOUT while processing {host}.")
                client.dump("runner_timeout")

            except Exception as e:
                res.status = "error"
                res.error = str(e)
                print(f"    [!] Error while processing {host}: {e}")
                client.dump("runner_error")

            finally:
                try:
                    context.close()
                except Exception:
                    pass
                results.append(res)

        browser.close()

    return results