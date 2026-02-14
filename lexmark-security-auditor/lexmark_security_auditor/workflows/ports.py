# lexmark_security_auditor/workflows/ports.py
from __future__ import annotations

from typing import Optional
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def _is_login_page(client) -> bool:
    """
    Detecta se estamos numa página de login (form-based).
    Usa sinais robustos:
      - URL contém /login.html
      - existe #username e #password
    """
    try:
        url = (client.page.url or "").lower()
        if "login.html" in url:
            return True
        if client.page.locator("#username").count() > 0 and client.page.locator("#password").count() > 0:
            return True
    except Exception:
        pass
    return False


def _do_form_login(client, username: str, password: str) -> bool:
    """
    Executa login via form, conforme teus selectors:
      #username
      #password
      Enviar: input[type=submit][value=Enviar] (fallback para o teu selector mais específico)
    """
    page = client.page

    try:
        page.wait_for_selector("#username", timeout=client.timeout_ms)
        page.locator("#username").fill(username)
        page.locator("#password").fill(password)

        # Preferir o teu selector específico (quando existir)
        submit = page.locator(
            '#login_form > table:nth-child(6) > tbody > tr > td:nth-child(1) > input[type="submit"]'
        )
        if submit.count() == 0:
            # Fallback robusto
            submit = page.locator('input[type="submit"][value="Enviar"]')
        if submit.count() == 0:
            submit = page.locator('input[type="submit"]').first

        submit.first.click(timeout=client.timeout_ms)
        page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        # Se ainda estiver em login, falhou
        if _is_login_page(client):
            client.dump("ports_login_failed_still_on_login")
            return False

        return True

    except PlaywrightTimeoutError:
        client.dump("ports_login_timeout")
        return False
    except Exception:
        client.dump("ports_login_exception")
        return False


def disable_http_tcp80(client, auth_user: Optional[str] = None, auth_pass: Optional[str] = None) -> bool:
    """
    Desactiva TCP 80 (HTTP) em:
      /cgi-bin/dynamic/config/secure/ports.html

    - Funciona em dois cenários:
      A) Sem Basic Security (OPEN): navega direto e desmarca.
      B) Com Basic Security (AUTH): detecta login e autentica via form.

    HTML checkbox:
      <input type="checkbox" id="vac.255.GUIPORTENABLE.3" name="vac.255.GUIPORTENABLE.3" value="1" ...>

    Submit:
      <input type="submit" value="Enviar">
    """
    page = client.page

    try:
        # 1) Entrar em Configurações (pode disparar login)
        client.goto("/cgi-bin/dynamic/config/config.html", wait_until="domcontentloaded")

        # Se caiu no login, autenticar (se tivermos creds)
        if _is_login_page(client):
            if not (auth_user and auth_pass):
                client.dump("ports_needs_auth_but_no_creds")
                return False

            if not _do_form_login(client, auth_user, auth_pass):
                return False

            # após login, normalmente já estás em Configurações/Segurança,
            # mas não confiamos — seguimos o fluxo.

        # 2) Ir para Segurança e depois Ports
        client.goto("/cgi-bin/dynamic/config/secure/security.html", wait_until="domcontentloaded")

        # Em alguns firmwares, ao entrar em security.html volta a pedir login
        if _is_login_page(client):
            if not (auth_user and auth_pass):
                client.dump("ports_needs_auth_on_security_but_no_creds")
                return False
            if not _do_form_login(client, auth_user, auth_pass):
                return False
            client.goto("/cgi-bin/dynamic/config/secure/security.html", wait_until="domcontentloaded")

        # Opcional: clicar no link "Acesso à porta TCP/IP" (mais “humano”)
        # Se falhar, seguimos por URL direto.
        try:
            link_ports = page.locator('a[href="/cgi-bin/dynamic/config/secure/ports.html"]')
            if link_ports.count() > 0:
                link_ports.first.click(timeout=client.timeout_ms)
                page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)
            else:
                client.goto("/cgi-bin/dynamic/config/secure/ports.html", wait_until="domcontentloaded")
        except Exception:
            client.goto("/cgi-bin/dynamic/config/secure/ports.html", wait_until="domcontentloaded")

        # Se ao entrar em ports.html pedir login novamente:
        if _is_login_page(client):
            if not (auth_user and auth_pass):
                client.dump("ports_needs_auth_on_ports_but_no_creds")
                return False
            if not _do_form_login(client, auth_user, auth_pass):
                return False
            client.goto("/cgi-bin/dynamic/config/secure/ports.html", wait_until="domcontentloaded")

        # 3) Desmarcar TCP 80 (HTTP) — usar NAME (não #id por causa dos dots)
        cb = page.locator("input[type='checkbox'][name='vac.255.GUIPORTENABLE.3']")
        if cb.count() == 0:
            # fallback por ID (ainda sem CSS '#', para evitar parsing issues)
            cb = page.locator("input[type='checkbox'][id='vac.255.GUIPORTENABLE.3']")

        if cb.count() == 0:
            client.dump("ports_no_tcp80_checkbox")
            return False

        # desmarcar apenas se estiver checked
        if cb.first.is_checked():
            cb.first.click(timeout=client.timeout_ms)

        # 4) Submit "Enviar" (idealmente o submit dentro do form de ports)
        submit = page.locator('form[action*="ports.html"] input[type="submit"][value="Enviar"]')
        if submit.count() == 0:
            submit = page.locator('input[type="submit"][value="Enviar"]')
        if submit.count() == 0:
            submit = page.locator("input[type='submit'], button[type='submit']").first

        submit.first.click(timeout=client.timeout_ms)
        page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        # 5) Validar que TCP80 ficou off
        # (Re-localize para evitar stale handles)
        cb2 = page.locator("input[type='checkbox'][name='vac.255.GUIPORTENABLE.3']").first
        ok = not cb2.is_checked()

        if not ok:
            client.dump("ports_tcp80_still_checked_after_submit")

        return ok

    except PlaywrightTimeoutError:
        client.dump("ports_timeout")
        return False
    except Exception:
        client.dump("ports_exception")
        return False
