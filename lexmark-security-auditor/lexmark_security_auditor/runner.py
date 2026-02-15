from __future__ import annotations

from typing import List, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .models import CheckResult, now_utc_iso
from .ews_client import LexmarkEWSClient
from .workflows.probe import probe_open_access
from .workflows.basic_security import apply_basic_security
from .workflows.ports import disable_http_tcp80
from .workflows.auth import ensure_authenticated_session, logout


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

            # Context principal (pode incluir http_credentials se quiseres, mas aqui não dependemos disso)
            context = browser.new_context(
                ignore_https_errors=True,
                http_credentials=(
                    {"username": auth_user, "password": auth_pass}
                    if auth_user and auth_pass
                    else None
                ),
            )
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
                # Disable HTTP (TCP/80)
                # -------------------------
                if disable_http:
                    print("    [*] Disabling HTTP (TCP/80)...")

                    ok_http = False
                    did_login = False

                    # Melhor prática: autenticar DIRETO no target (ports.html),
                    # para o login "goto" levar exatamente onde queremos.
                    target_after_login = "/cgi-bin/dynamic/config/secure/ports.html"

                    if auth_user and auth_pass:
                        print("    [*] Ensuring authenticated session (form-based login)...")
                        did_login = ensure_authenticated_session(
                            client,
                            username=auth_user,
                            password=auth_pass,
                            # 🔥 IMPORTANTE: força auth no alvo que vamos operar
                            # (vais precisar ajustar a assinatura em auth.py — ver nota abaixo)
                            target_path=target_after_login,
                        )

                        if did_login:
                            ok_http = disable_http_tcp80(client)
                            logout(client)  # best effort
                        else:
                            ok_http = False
                    else:
                        # Sem credenciais: tenta (só funciona se device estiver OPEN)
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

                # -------------------------
                # Apply Basic Security
                # -------------------------
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