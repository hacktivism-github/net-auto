from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ..ews_client import LexmarkEWSClient


def disable_http_tcp80_with_login(
    client: LexmarkEWSClient,
    username: str,
    password: str,
) -> bool:
    """
    Disable TCP 80 (HTTP) on Lexmark MX710 EWS, assuming Basic Security is already enabled.

    Flow (based on your observed UI):
      1) Open Configurações: /cgi-bin/dynamic/config/config.html
         -> triggers login form
      2) Fill:
         - ID do usuário: #username
         - Senha: #password
         - Enviar: #login_form > table:nth-child(6) > tbody > tr > td:nth-child(1) > input[type=submit]
      3) After login, land on Configurações/Segurança
      4) Click "Acesso à porta TCP/IP" (link to /cgi-bin/dynamic/config/secure/ports.html)
      5) In ports.html:
         - Uncheck checkbox id/name "vac.255.GUIPORTENABLE.3"
         - Click "Enviar" (submit)
      6) Logout: /cgi-bin/dynamic/printer/logout.html

    Returns True if it successfully unchecks TCP 80 and submits.
    """

    try:
        # 1) Go to Configurações (this is what triggers the login form)
        client.goto("/cgi-bin/dynamic/config/config.html", wait_until="domcontentloaded")

        # 2) Login form (selectors provided by you)
        client.page.wait_for_selector("#username", timeout=client.timeout_ms)
        client.page.locator("#username").fill(username)
        client.page.locator("#password").fill(password)

        # "Enviar" on login form (your exact selector)
        submit_login = client.page.locator(
            '#login_form > table:nth-child(6) > tbody > tr > td:nth-child(1) > input[type="submit"]'
        )
        if submit_login.count() == 0:
            # safe fallback (in case table structure changes slightly)
            submit_login = client.page.locator('input[type="submit"][value="Enviar"]').first

        submit_login.first.click(timeout=client.timeout_ms)
        client.page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        # 3) Now we should be on Configurações/Segurança
        # Click "Acesso à porta TCP/IP"
        # Prefer robust link selector first
        link_ports = client.page.locator('a[href="/cgi-bin/dynamic/config/secure/ports.html"]')
        if link_ports.count() == 0:
            # Your exact CSS selector (fallback)
            link_ports = client.page.locator("body > table:nth-child(3) > tbody > tr:nth-child(10) > td > a")

        if link_ports.count() == 0:
            client.dump("disable_http_no_ports_link")
            return False

        link_ports.first.click(timeout=client.timeout_ms)
        client.page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        # 4) ports.html: uncheck TCP 80 (HTTP)
        # IMPORTANT: do NOT use "#vac.255.GUIPORTENABLE.3" because ".255" breaks CSS parsing.
        tcp80 = client.page.locator('input[type="checkbox"][name="vac.255.GUIPORTENABLE.3"]')
        if tcp80.count() == 0:
            tcp80 = client.page.locator('input[type="checkbox"][id="vac.255.GUIPORTENABLE.3"]')

        if tcp80.count() == 0:
            client.dump("disable_http_no_tcp80_checkbox")
            return False

        # Only click if currently checked
        if tcp80.first.is_checked():
            tcp80.first.click(timeout=client.timeout_ms)

        # 5) Submit "Enviar" on ports page
        submit_ports = client.page.locator('form[action*="ports.html"] input[type="submit"][value="Enviar"]')
        if submit_ports.count() == 0:
            # fallback: first submit in that form
            submit_ports = client.page.locator('form[action*="ports.html"] input[type="submit"]').first

        submit_ports.first.click(timeout=client.timeout_ms)
        client.page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        # 6) Logout (best effort)
        try:
            client.goto("/cgi-bin/dynamic/printer/logout.html", wait_until="domcontentloaded")
        except Exception:
            pass

        return True

    except PlaywrightTimeoutError:
        client.dump("disable_http_timeout")
        return False
    except Exception as e:
        print(f"    [!] Failed to disable TCP 80 (HTTP) with login: {e}")
        client.dump("disable_http_exception")
        return False
