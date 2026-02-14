from __future__ import annotations

from typing import List, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .models import CheckResult, now_utc_iso
from .ews_client import LexmarkEWSClient
from .workflows.probe import probe_open_access
from .workflows.basic_security import apply_basic_security
from .workflows.ports import disable_http_tcp80
from .workflows.disable_http_auth import disable_http_tcp80_with_login

def normalize_base_url(host: str, https: bool) -> str:
    host = host.strip()
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    scheme = "https" if https else "http"
    return f"{scheme}://{host}".rstrip("/")


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

            # Context 1: (optional) with http_credentials from CLI (auth_user/auth_pass)
            context = browser.new_context(
                 ignore_https_errors=True,
            #     http_credentials=(
            #         {"username": auth_user, "password": auth_pass}
            #         if auth_user and auth_pass
            #         else None
            #     )
            )
            page = context.new_page()
            client = LexmarkEWSClient(page, base_url=base_url, timeout_s=timeout, debug_html=debug_html)

            try:
                print("    -> Probing admin/security URLs...")
                out = probe_open_access(client, timeout_s=timeout)
                res.probe_result = out["result"]
                res.evidence = out["evidence"]
                res.http_status = out["http_status"]
                res.final_url = out["final_url"]

                print(f"\n[RESULT] {host}: {res.probe_result}")
                print(f"         Evidence: {res.evidence}")

                # 1) Disable HTTP first (if requested) while still unauth/open
                http_disabled_first_try = False
                if disable_http:
                    print("    [*] Disabling HTTP (TCP/80)...")
                    http_disabled_first_try = disable_http_tcp80(
                        client,
                        auth_user=auth_user,
                        auth_pass=auth_pass,
                    )
                    res.http_disabled = bool(http_disabled_first_try)
                    print("    [✓] HTTP disabled.") #if http_disabled_first_try else "    [!] Failed to disable HTTP.")


                # 2) Apply Basic Security (if requested)
                basic_ok = False
                if apply_basic:
                    print("    [*] Applying Basic Security workflow...")
                    basic_ok = apply_basic_security(client, username=new_user or "", password=new_pass or "")
                    res.basic_security_applied = bool(basic_ok)
                    print("    [✓] Basic Security workflow applied." if basic_ok else "    [!] Failed to apply Basic Security workflow.")


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
                context.close()
                results.append(res)

        browser.close()

    return results
