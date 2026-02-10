from __future__ import annotations

from typing import List, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .models import CheckResult, now_utc_iso
from .ews_client import LexmarkEWSClient
from .workflows.probe import probe_open_access
from .workflows.basic_security import apply_basic_security
from .workflows.ports import disable_http_tcp80


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

            # Context 1: no credentials
            context = browser.new_context(ignore_https_errors=True)
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
                    http_disabled_first_try = disable_http_tcp80(client)
                    res.http_disabled = bool(http_disabled_first_try)
                    print("    [✓] HTTP disabled." if http_disabled_first_try else "    [!] Failed to disable HTTP (may require auth).")

                # 2) Apply Basic Security (if requested)
                basic_ok = False
                if apply_basic:
                    print("    [*] Applying Basic Security workflow...")
                    basic_ok = apply_basic_security(client, username=new_user or "", password=new_pass or "")
                    res.basic_security_applied = bool(basic_ok)
                    print("    [✓] Basic Security workflow applied." if basic_ok else "    [!] Failed to apply Basic Security workflow.")

                # 3) If disable-http failed and we applied basic security, retry with authenticated context
                if disable_http and (not res.http_disabled) and apply_basic and (new_user and new_pass):
                    print("    [*] Retrying disable HTTP with authenticated context (http_credentials)...")
                    context2 = browser.new_context(
                        ignore_https_errors=True,
                        http_credentials={"username": new_user, "password": new_pass},
                    )
                    page2 = context2.new_page()
                    client2 = LexmarkEWSClient(page2, base_url=base_url, timeout_s=timeout, debug_html=debug_html)

                    try:
                        ok2 = disable_http_tcp80(client2)
                        res.http_disabled = bool(ok2)
                        print("    [✓] HTTP disabled after auth retry." if ok2 else "    [!] Still failed to disable HTTP after auth retry.")
                    finally:
                        context2.close()

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

