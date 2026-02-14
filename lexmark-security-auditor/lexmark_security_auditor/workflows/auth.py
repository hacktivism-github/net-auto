# lexmark_security_auditor/workflows/auth.py
from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def _find_login_context(page):
    """
    Alguns EWS metem o login em frames.
    Vamos procurar em page + todas as frames por inputs típicos de login.
    """
    candidates = [page] + list(page.frames)

    for ctx in candidates:
        try:
            # Tentativa 1: nomes comuns
            u = ctx.locator("input[name='username'], input#username, input[name='user'], input[name='userid']")
            p = ctx.locator("input[type='password'], input[name='password'], input#password")
            if u.count() > 0 and p.count() > 0:
                return ctx
        except Exception:
            continue

    return None


def login_form_based(client, username: str, password: str) -> bool:
    """
    Login via /cgi-bin/dynamic/printer/login.html (form-based).
    Estratégia:
      - assume que a page já foi redirecionada para login (ou está prestes a ser)
      - encontra o contexto (page/frame) que contém os inputs
      - preenche e submete
      - valida se saímos do login (URL e ausência de campos)
    """
    page = client.page

    try:
        # garantir que o DOM da página de login está carregado
        page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        ctx = _find_login_context(page)
        if ctx is None:
            # tenta esperar um pouco e procurar de novo
            page.wait_for_timeout(800)
            ctx = _find_login_context(page)

        if ctx is None:
            client.dump("login_no_form_found")
            return False

        # localizar username
        user_loc = ctx.locator(
            "input[name='username'], input#username, input[name='user'], input[name='userid']"
        ).first

        # localizar password
        pass_loc = ctx.locator(
            "input[type='password'], input[name='password'], input#password"
        ).first

        user_loc.fill(username)
        pass_loc.fill(password)

        # Botão submit: várias hipóteses
        submit = ctx.locator(
            "input[type='submit'], button[type='submit'], input[name='submit'], button"
        )

        # preferências por texto
        preferred = submit.filter(has_text="Login")
        if preferred.count() == 0:
            preferred = submit.filter(has_text="Entrar")
        if preferred.count() == 0:
            preferred = submit.filter(has_text="OK")
        if preferred.count() == 0:
            preferred = submit.filter(has_text="Submit")
        if preferred.count() == 0:
            preferred = submit

        preferred.first.click(timeout=client.timeout_ms)

        # esperar navegação/redirect após login
        page.wait_for_load_state("domcontentloaded", timeout=client.timeout_ms)

        # Heurística de sucesso:
        # - URL já não contém login
        # - e não vemos de novo os inputs
        url_now = (page.url or "").lower()
        if "login" not in url_now:
            return True

        # alguns casos voltam para login mas com erro; verificar se inputs continuam visíveis
        ctx2 = _find_login_context(page)
        if ctx2 is None:
            # já não encontro form — provável sucesso
            return True

        # ainda em login
        client.dump("login_still_on_login")
        return False

    except PlaywrightTimeoutError:
        client.dump("login_timeout")
        return False
    except Exception:
        client.dump("login_exception")
        return False
