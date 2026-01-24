#!/usr/bin/env python3
import argparse
import csv
import getpass
import json
import sys
import time
from datetime import datetime, timezone
from typing import List, Optional

from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from apc_ups_security_auditor import __version__


def load_hosts(path: str) -> List[str]:
    hosts: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            hosts.append(line)
    return hosts


def login_via_ui(page, username: str, password: str, timeout: float) -> Optional[bool]:
    """
    Returns:
      True  -> login succeeded
      False -> login failed
      None  -> unexpected error / timeout
    """
    try:
        page.wait_for_selector("input[name='login_username']", timeout=5000)
        print("    [*] Login page ready.")

        # Set language
        try:
            lang_select = page.locator("select").first
            lang_select.select_option(label="English")
            print("    [*] Set language to English.")
        except Exception as e:
            print(f"    [debug] Could not set language (maybe already English): {e}")

        time.sleep(0.5)

        # Fill username & password
        filled = False
        try:
            page.fill("input[name='login_username']", username)
            page.fill("input[name='login_password']", password)
            filled = True
        except Exception:
            try:
                page.locator("input[type='text']").first.fill(username)
                page.locator("input[type='password']").first.fill(password)
                filled = True
            except Exception as e:
                print(f"    [!] Could not find login fields: {e}")

        if not filled:
            return None

        print("    [*] Filled username and password.")

        # Click Log On
        try:
            page.get_by_role("button", name="Log On").click()
        except Exception:
            page.get_by_text("Log On", exact=False).click()

        print("    [*] Clicked Log On, waiting for home page...")

        try:
            page.wait_for_url("**/home.htm*", timeout=timeout * 1000)
            print("    [✓] Login successful.")
            return True
        except PlaywrightTimeoutError:
            print("    [-] Login did not reach home.htm – credentials probably NOT valid.")
            return False

    except PlaywrightTimeoutError:
        print("    [!] Timeout while loading login page.")
        return None
    except Exception as e:
        print(f"    [!] Unexpected error during login: {e}")
        return None


def change_password_via_ui(page, new_password: str, current_password: str = "apc") -> bool:
    print("    [*] Navigating to User Management (click-only navigation)...")

    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)

        print("      -> Clicking 'Configuration'")
        page.get_by_role("link", name="Configuration").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        print("      -> Clicking 'Security'")
        page.get_by_role("link", name="Security").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        print("      -> Clicking 'Local Users'")
        page.get_by_role("link", name="Local Users").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        print("      -> Clicking 'Management' (Local Users / userman.htm)")
        page.locator("a[href*='userman.htm']").first.click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.5)

        print("      -> Clicking user 'apc' under Super User Management")
        page.locator("a[href*='usercfg.htm'][href*='user=apc']").first.click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.5)

        print("      -> Filling Current / New / Confirm Password fields...")
        password_inputs = page.locator("input[type='password']")
        count = password_inputs.count()
        if count < 3:
            print(f"      [!] ERROR: Found only {count} password fields (expected 3).")
            return False

        password_inputs.nth(0).fill(current_password)
        password_inputs.nth(1).fill(new_password)
        password_inputs.nth(2).fill(new_password)

        print("      -> Clicking 'Next' (or fallback 'Apply')...")
        submitted = False
        try:
            page.get_by_role("button", name="Next").click(timeout=5000)
            submitted = True
        except Exception:
            pass

        if not submitted:
            try:
                page.get_by_role("button", name="Apply").click(timeout=5000)
                submitted = True
            except Exception:
                pass

        if not submitted:
            print("      [!] ERROR: Could not click Next or Apply.")
            return False

        print("      -> Waiting for final confirmation page...")
        try:
            page.wait_for_url("**/usrcnfrm*", timeout=5000)
        except Exception:
            pass

        print("      -> Clicking FINAL 'Apply'")
        try:
            page.get_by_role("button", name="Apply").click(timeout=5000)
        except Exception as e:
            print(f"      [!] Could not click final Apply: {e}")
            return False

        page.wait_for_load_state("networkidle", timeout=10000)
        print("    [✓] Password change fully confirmed.")
        return True

    except Exception as e:
        print(f"    [!] Error during password change navigation: {e}")
        return False


def create_admin_user_via_ui(page, new_username: str, new_password: str, headful: bool = False) -> bool:
    """
    Clean version (your pasted one had duplicated blocks).
    """
    print("    [*] Navigating to Local Users to create admin user...")

    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)

        print("      -> Clicking 'Configuration'")
        page.get_by_role("link", name="Configuration").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        print("      -> Clicking 'Security'")
        page.get_by_role("link", name="Security").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        print("      -> Clicking 'Local Users'")
        page.get_by_role("link", name="Local Users").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        print("      -> Opening 'Management' (user list)")
        page.locator("a[href*='userman.htm']").first.click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.5)

        print("      -> Clicking 'Add User'…")
        added = False
        for attempt in range(3):
            try:
                if attempt == 0:
                    page.get_by_role("button", name="Add User").click(timeout=5000)
                elif attempt == 1:
                    page.locator("input[value='Add User']").first.click(timeout=5000)
                else:
                    page.locator("a[href*='useradd']").first.click(timeout=5000)
                added = True
                break
            except Exception:
                pass

        if not added:
            print("      [!] Could not find an 'Add User' control.")
            return False

        page.wait_for_load_state("domcontentloaded", timeout=10000)
        time.sleep(0.5)
        print(f"      -> Now on page: {page.url}")

        print("      -> Enabling new user (ticking 'Enable' checkbox)…")
        try:
            page.get_by_label("Enable").check()
        except Exception:
            try:
                page.locator("input[type='checkbox']").first.check()
            except Exception as e:
                print(f"      [!] Could not tick 'Enable' checkbox: {e}")
                return False

        print(f"      -> Filling new admin user: {new_username}")
        filled_username = False
        try:
            text_inputs = page.locator("input[type='text'], input:not([type])")
            if text_inputs.count() > 0:
                text_inputs.first.fill(new_username)
                filled_username = True
        except Exception:
            pass

        if not filled_username:
            try:
                generic = page.locator("input:not([type='hidden']):not([type='password'])").first
                generic.fill(new_username)
                filled_username = True
            except Exception:
                pass

        if not filled_username:
            print("      [!] Could not locate username field.")
            return False

        print("      -> Filling password fields…")
        pwd_inputs = page.locator("input[type='password']")
        if pwd_inputs.count() < 2:
            print(f"      [!] Could not find two password fields (found {pwd_inputs.count()}).")
            return False

        pwd_inputs.nth(0).fill(new_password)
        pwd_inputs.nth(1).fill(new_password)

        print("      -> Setting user role (Super User / Administrator) if possible…")
        try:
            role_select = page.locator("select[name='user_role'], select[name='usertype'], select[name*='Type']")
            if role_select.count() > 0:
                try:
                    role_select.first.select_option(label="Super User")
                except Exception:
                    try:
                        role_select.first.select_option(label="Administrator")
                    except Exception:
                        pass
            else:
                try:
                    page.get_by_label("Super User").check()
                except Exception:
                    pass
        except Exception:
            pass

        print("      -> Clicking 'Next'…")
        next_clicked = False
        try:
            page.locator("input[value^='Next'], button:has-text('Next')").first.click(timeout=5000)
            next_clicked = True
        except Exception:
            pass
        if not next_clicked:
            try:
                page.get_by_text("Next", exact=False).click(timeout=5000)
                next_clicked = True
            except Exception:
                pass
        if not next_clicked:
            print("      [!] Could not click 'Next' button.")
            return False

        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            time.sleep(0.5)
        except Exception:
            pass

        print("      -> On confirmation page, clicking 'Apply'…")
        applied = False
        try:
            page.get_by_role("button", name="Apply").click(timeout=5000)
            applied = True
        except Exception:
            pass
        if not applied:
            try:
                page.locator("input[value='Apply']").first.click(timeout=5000)
                applied = True
            except Exception:
                pass
        if not applied:
            print("      [!] Could not click final 'Apply'.")
            return False

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        time.sleep(0.5)
        print("    [✓] New admin user creation flow completed (Next + Apply).")
        return True

    except PlaywrightTimeoutError:
        print("    [!] Timeout while creating admin user.")
        return False
    except Exception as e:
        print(f"    [!] Exception while creating admin user: {e}")
        return False


# =============================================================================
# SNMP HELPERS
# =============================================================================

def nmc_session_url(page, leaf: str) -> str:
    """
    Builds a URL like:
      https://<origin>/NMC/<session_token>/<leaf>
    using the current page.url (already logged in).
    """
    u = urlsplit(page.url)
    origin = f"{u.scheme}://{u.netloc}"

    # Example path:
    #   /NMC/Zy9wbbR_77NnYhPa0FG_HQ/snmpusra.htm
    path = u.path
    i = path.find("/NMC/")
    if i == -1:
        # fallback: just go to root-relative leaf
        return f"{origin}/{leaf.lstrip('/')}"
    rest = path[i + len("/NMC/"):]          # "<token>/snmpusra.htm"
    token = rest.split("/", 1)[0]          # "<token>"
    return f"{origin}/NMC/{token}/{leaf.lstrip('/')}"

def goto_snmpv3_access(page) -> bool:
    try:
        url = nmc_session_url(page, "snmpu.htm")
        page.goto(url, wait_until="domcontentloaded", timeout=15_000)

        # Page-unique markers
        page.wait_for_selector("text=Configure SNMPv3 Access", timeout=15_000)
        page.wait_for_selector("form[name='SNMPv3AccessFrm']", timeout=15_000)
        return True
    except Exception as e:
        print(f"    [!] Failed to navigate to SNMPv3 Access: {e}")
        return False
    
def enable_snmpv3_access(page) -> bool:
    try:
        if not goto_snmpv3_access(page):
            return False

        print("    [*] SNMPv3: enabling SNMPv3 Access ...")

        enable_cb = page.locator("input[type='checkbox'][name='arak_snmp3Access']")
        apply_btn = page.locator("input[type='submit'][name='submit'][value='Apply']").first

        enable_cb.wait_for(state="attached", timeout=15_000)

        # Tick only if needed
        if not enable_cb.is_checked():
            enable_cb.check()

        # Apply (may or may not navigate)
        try:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=15_000):
                apply_btn.click()
        except Exception:
            apply_btn.click()

        page.wait_for_load_state("networkidle", timeout=15_000)
        print("    [✓] SNMPv3 Access enabled.")
        return True

    except Exception as e:
        print(f"    [!] Error enabling SNMPv3 Access: {e}")
        return False

def goto_snmpv3_user_profiles(page) -> bool:
    try:
        url = nmc_session_url(page, "snmpusrs.htm")
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(0.2)
        return True
    except Exception as e:
        print(f"    [!] Failed to navigate to SNMPv3 User Profiles: {e}")
        return False


def configure_snmpv3_user_profile(
    page,
    profile_name: str,      # what you click in the table, e.g. "apc snmp profile1"
    new_username: str,      # what you set in the edit page, e.g. "ZABBAI"
    auth_proto: str,        # "SHA" | "MD5" | "None"
    priv_proto: str,        # "AES" | "DES" | "None"
    auth_pass: str | None,
    priv_pass: str | None,
) -> bool:
    """
    Works with NMC3 HTML like:

      <input type="text" name="i1usmUserName" ...>
      <input type="text" name="i2usmUserAuthPassphrase" ...>
      <input type="text" name="i2usmUserCryptPassphrase" ...>

      <input type="radio" name="authProtocol" value="authSHA">
      <input type="radio" name="privProtocol" value="privAES">
    """

    AUTH_MAP = {"SHA": "authSHA", "MD5": "authMD5", "None": "authNone"}
    PRIV_MAP = {"AES": "privAES", "DES": "privDES", "None": "privNone"}

    try:
        if not goto_snmpv3_user_profiles(page):
            return False

        print(f"    [*] SNMPv3: opening USER PROFILES entry '{profile_name}' ...")

        # Click entry in snmpusrs.htm
        clicked = False
        for attempt in range(3):
            try:
                page.get_by_role("link", name=profile_name).click(timeout=8000)
                clicked = True
                break
            except Exception:
                pass
            try:
                page.locator("a", has_text=profile_name).first.click(timeout=8000)
                clicked = True
                break
            except Exception:
                pass
            try:
                page.get_by_text(profile_name, exact=True).click(timeout=8000)
                clicked = True
                break
            except Exception:
                pass

        if not clicked:
            print(f"    [!] Could not find SNMPv3 user profile TABLE entry for '{profile_name}'.")
            return False

        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(0.2)

        # Ensure we are on the edit page
        page.wait_for_selector("text=Configure User Profile", timeout=10000)

        # --- Fill fields by *name* (most reliable) ---
        print(f"    [*] SNMPv3: setting User Name = '{new_username}'")
        page.fill("input[name='i1usmUserName']", new_username)

        # Passphrases are input[type=text] in your HTML
        if auth_proto != "None":
            if not auth_pass:
                print("    [!] SNMPv3: auth proto requires --snmpv3-auth-pass.")
                return False
            print("    [*] SNMPv3: setting Authentication Passphrase")
            page.fill("input[name='i2usmUserAuthPassphrase']", auth_pass)

        if priv_proto != "None":
            if not priv_pass:
                print("    [!] SNMPv3: priv proto requires --snmpv3-priv-pass.")
                return False
            print("    [*] SNMPv3: setting Privacy Passphrase")
            page.fill("input[name='i2usmUserCryptPassphrase']", priv_pass)

        # --- Select radio protocols by value ---
        auth_value = AUTH_MAP.get(auth_proto, "authNone")
        priv_value = PRIV_MAP.get(priv_proto, "privNone")

        print(f"    [*] SNMPv3: setting Authentication Protocol = {auth_proto}")
        page.check(f"input[type='radio'][name='authProtocol'][value='{auth_value}']")

        print(f"    [*] SNMPv3: setting Privacy Protocol = {priv_proto}")
        page.check(f"input[type='radio'][name='privProtocol'][value='{priv_value}']")

        # Apply (this page uses input submit)
        print("    [*] SNMPv3: clicking Apply")

        # Ensure the page/form is there and stable
        page.wait_for_load_state("domcontentloaded", timeout=15000)

        apply = None

        # Try the most specific selectors first, then fallbacks
        candidates = [
            "input[type='submit'][name='submit'][value='Apply']",
            "input[type='submit'][value='Apply']",
            "button:has-text('Apply')",
            "input[value='Apply']",
        ]
        for sel in candidates:
            loc = page.locator(sel)
            if loc.count() > 0:
                apply = loc.first
                break

        if apply is None:
            # last resort: role-based
            try:
                apply = page.get_by_role("button", name="Apply")
            except Exception:
                apply = None

        if apply is None:
            raise RuntimeError("Could not locate Apply button on SNMPv3 user profile page.")

        # Scroll + click (some firmwares hide/disable until scrolled)
        apply.scroll_into_view_if_needed(timeout=5000)

        # Click and expect navigation back to user profiles (very common behavior)
        try:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
                apply.click(timeout=10000)
        except Exception:
            # If it doesn't navigate (some firmwares do in-place POST), click anyway and wait for network idle
            apply.click(timeout=10000)

        # After Apply, the device often returns to snmpusrs.htm or shows a success page
        page.wait_for_load_state("networkidle", timeout=30000)

        page.wait_for_url("**/snmpusrs.htm*", timeout=15000)
        page.wait_for_selector("text=Configure SNMPv3 User Profiles", timeout=15000)        

        page.wait_for_load_state("networkidle", timeout=15000)
        print("    [✓] SNMPv3 user profile updated successfully.")
        return True
    except Exception as e:
        print(f"    [!] Error configuring SNMPv3 user profile: {e}")
        return False

def goto_snmpv3_access_control(page) -> bool:
    try:
        url = nmc_session_url(page, "snmpusra.htm")
        page.goto(url, wait_until="domcontentloaded", timeout=15_000)

        # This page is the LIST page with the table of users
        page.wait_for_selector("text=Configure SNMPv3 Access Control", timeout=15_000)
        page.wait_for_selector("table", timeout=15_000)
        return True
    except Exception as e:
        print(f"    [!] Failed to navigate to SNMPv3 Access Control: {e}")
        return False


def enable_snmpv3_access_control(page, username: str, nms_host: str) -> bool:
    try:
        if not goto_snmpv3_access_control(page):
            return False

        print(f"    [*] SNMPv3: enabling access control for '{username}' (NMS: {nms_host}) ...")

        # 1) Click the user hyperlink in the LIST table (e.g. "ZABBAI")
        user_link = page.locator("table a", has_text=username).first
        user_link.wait_for(state="visible", timeout=15_000)

        with page.expect_navigation(wait_until="domcontentloaded", timeout=15_000):
            user_link.click()

        # 2) Now we should be on snmpccfg.htm?user=<n>
        # Wait for the actual form fields by NAME (most reliable)
        enable_cb = page.locator("input[name='i1usmUserAccessEnable']")
        nms_input = page.locator("input[name='i1usmUserAccessAddr']")
        apply_btn = page.locator("input[type='submit'][value='Apply'], button:has-text('Apply')").first

        enable_cb.wait_for(state="attached", timeout=15_000)
        nms_input.wait_for(state="visible", timeout=15_000)

        # 3) Enable (only if not already enabled)
        if not enable_cb.is_checked():
            enable_cb.check()

        # 4) Replace 0.0.0.0 with the provided NMS IP
        # (fill replaces the whole value; no extra wait needed)
        nms_input.fill(nms_host)

        # 5) Apply (often navigates back to list)
        apply_btn.scroll_into_view_if_needed(timeout=5_000)
        try:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=20_000):
                apply_btn.click()
        except Exception:
            # Some firmwares may POST without changing URL
            apply_btn.click()

        page.wait_for_load_state("networkidle", timeout=20_000)
        print("    [✓] SNMPv3 access control enabled.")
        return True

    except Exception as e:
        print(f"    [!] Error enabling SNMPv3 access control: {e}")
        return False


def goto_snmpv1_access(page) -> bool:
    try:
        url = nmc_session_url(page, "snmp.htm")
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(0.2)
        return True
    except Exception as e:
        print(f"    [!] Failed to navigate to SNMPv1 Access: {e}")
        return False


def disable_snmpv1(page) -> bool:
    try:
        if not goto_snmpv1_access(page):
            return False

        print("    [*] SNMPv1: disabling (best-effort) ...")

        # Uncheck Enable (if present)
        try:
            cb = page.get_by_label("Enable")
            if cb.is_checked():
                cb.uncheck()
        except Exception:
            # fallback: first checkbox on page
            cbs = page.locator("input[type='checkbox']")
            if cbs.count() > 0:
                try:
                    if cbs.first.is_checked():
                        cbs.first.uncheck()
                except Exception:
                    # last resort: click it
                    cbs.first.click()

        time.sleep(0.2)

        # Click Apply (SNMP pages often use <input type="submit" value="Apply">)
        apply_btn = page.locator("input[type='submit'][value='Apply'], input[name='submit'][value='Apply']").first
        apply_btn.scroll_into_view_if_needed()
        apply_btn.click(timeout=15000, force=True)

        page.wait_for_load_state("networkidle", timeout=20000)
        print("    [✓] SNMPv1 disabled (best-effort).")
        return True

    except Exception as e:
        print(f"    [!] Failed to disable SNMPv1: {e}")
        return False


def run_snmp_hardening_if_requested(args, page, result) -> None:
    """
    Runs SNMPv3 hardening steps if --snmpv3-enable was requested.
    Updates `result` in-place. Never raises (best-effort) — stores errors in result["error"].
    """

    if not args.snmpv3_enable:
        return

    # record intent / parameters in report
    result["snmpv3_profile"] = args.snmpv3_profile
    result["snmpv3_user"] = args.snmpv3_user
    result["snmpv3_auth_proto"] = args.snmpv3_auth_proto
    result["snmpv3_priv_proto"] = args.snmpv3_priv_proto
    result["snmpv3_nms"] = args.snmpv3_nms

    try:
        # 1) Update user profile
        ok_profile = configure_snmpv3_user_profile(
            page,
            profile_name=args.snmpv3_profile,
            new_username=args.snmpv3_user,
            auth_proto=args.snmpv3_auth_proto,
            priv_proto=args.snmpv3_priv_proto,
            auth_pass=args.snmpv3_auth_pass,
            priv_pass=args.snmpv3_priv_pass,
        )

        # 2) Enable SNMPv3 Access (snmpu.htm) BEFORE ACL
        ok_snmpv3_access = False
        if ok_profile:
            ok_snmpv3_access = enable_snmpv3_access(page)  # <-- you add/use this

        # 3) Configure SNMPv3 Access Control (ACL)
        ok_acl = False
        if ok_profile and ok_snmpv3_access:
            ok_acl = enable_snmpv3_access_control(
                page,
                username=args.snmpv3_user,
                nms_host=args.snmpv3_nms,
            )

        # report outcomes
        result["snmpv3_configured"] = bool(ok_profile)
        result["snmpv3_access_enabled"] = bool(ok_acl)  # keep your existing field name

        # optional: add an extra field if you want visibility
        result["snmpv3_access_page_enabled"] = bool(ok_snmpv3_access)

        if args.disable_snmpv1 and ok_acl:
            result["snmpv1_disabled"] = bool(disable_snmpv1(page))

    except Exception as e:
        result["snmpv3_configured"] = False
        result["snmpv3_access_enabled"] = False
        if not result.get("error"):
            result["error"] = f"snmp_hardening_failed: {e}"


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "APC/Schneider UPS (NMC3) automation tool: "
            "log in, optionally create a new admin user, optionally harden SNMP, and report results."
        )
    )

    parser.add_argument("--version", action="version", version=f"apc-ups-audit {__version__}")

    # INPUT / CONNECTION
    parser.add_argument("--hosts", help="Path to file containing UPS IPs/hostnames (one per line).")
    parser.add_argument("--check-only", metavar="HOST", help="Check ONLY one UPS host for default credentials and exit.")
    parser.add_argument("--https", action="store_true", help="Use HTTPS instead of HTTP to open the web UI.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout seconds for page loads and login.")
    parser.add_argument("--headful", action="store_true", help="Run browser headful (visible). Default headless.")

    # DEFAULT CREDENTIALS
    parser.add_argument("--default-user", default="apc", help="Default username to test first (default: apc).")
    parser.add_argument("--default-pass", default="apc", help="Default password to test first (default: apc).")
    parser.add_argument("--apc-new-pass", help="New hardened password for default user when default creds work.")

    # FALLBACK
    parser.add_argument("--current-user", default="apc", help="Fallback username when default login fails.")
    parser.add_argument("--current-pass", help="Fallback password when default login fails.")

    # ADMIN
    parser.add_argument("--create-admin", action="store_true", help="Create a new Super User admin account.")
    parser.add_argument("--new-admin-user", help="New admin username (used with --create-admin).")
    parser.add_argument("--new-admin-pass", help="New admin password (prompted if omitted and not --auto).")

    parser.add_argument("--auto", action="store_true", help="Run without interactive prompts.")

    # REPORTING
    parser.add_argument("--report-csv", help="Path to CSV report file.")
    parser.add_argument("--report-json", help="Path to JSON report file.")

    # ----------------------------------------------------------------------
    # PHASE 2 – SNMP HARDENING
    # ----------------------------------------------------------------------
    parser.add_argument(
        "--snmpv3-enable",
        action="store_true",
        help="Configure and enable SNMPv3 on hosts where login succeeds.",
    )

    parser.add_argument(
        "--snmpv3-profile",
        default="apc snmp profile1",
        help="SNMPv3 profile entry name to click in the UI table (default: 'apc snmp profile1').",
    )

    # IMPORTANT: this should match the *visible* username in the UI (e.g. ZABBAI),
    # because we use it later to click the Access Control hyperlink.
    parser.add_argument(
        "--snmpv3-user",
        default="ZABBAI",
        help="SNMPv3 User Name to set inside the profile AND to click in Access Control (e.g. ZABBAI).",
    )

    parser.add_argument(
        "--snmpv3-auth-proto",
        choices=["SHA", "MD5", "None"],
        default="SHA",
        help="SNMPv3 authentication protocol (default: SHA).",
    )

    parser.add_argument(
        "--snmpv3-priv-proto",
        choices=["AES", "DES", "None"],
        default="AES",
        help="SNMPv3 privacy protocol (default: AES).",
    )

    parser.add_argument(
        "--snmpv3-auth-pass",
        help="SNMPv3 authentication passphrase (prompted if omitted and not --auto, required if auth-proto != None).",
    )

    parser.add_argument(
        "--snmpv3-priv-pass",
        help="SNMPv3 privacy passphrase (prompted if omitted and not --auto, required if priv-proto != None).",
    )

    parser.add_argument(
        "--snmpv3-nms",
        help="NMS IP/Host Name to allow in SNMPv3 access control (e.g. 172.31.59.116).",
    )

    parser.add_argument(
        "--disable-snmpv1",
        action="store_true",
        help="Disable SNMPv1 after SNMPv3 access control was successfully enabled.",
    )

    args = parser.parse_args()

    # EARLY VALIDATION
    if not args.check_only and not args.hosts:
        parser.error("one of the arguments --hosts or --check-only is required")
    if args.check_only and args.hosts:
        parser.error("--check-only cannot be used together with --hosts")

    # fallback prompt only if user differs
    if args.current_user != args.default_user and not args.current_pass:
        if args.auto:
            print("[!] --current-pass is required when --current-user differs and --auto is used.")
            sys.exit(1)
        args.current_pass = getpass.getpass(f"Password for fallback user {args.current_user}: ")

    # create-admin validation
    if args.create_admin:
        if not args.new_admin_user:
            print("[!] --new-admin-user is required when using --create-admin.")
            sys.exit(1)

        if not args.new_admin_pass:
            if args.auto:
                print("[!] --new-admin-pass is required with --create-admin when using --auto.")
                sys.exit(1)
            while True:
                p1 = getpass.getpass("New admin user password: ")
                p2 = getpass.getpass("Confirm new admin user password: ")
                if p1 != p2:
                    print("Passwords do not match, try again.")
                elif not p1:
                    print("Password cannot be empty.")
                else:
                    args.new_admin_pass = p1
                    break

    # ----------------------------------------------------------------------
    # SNMPv3 validation / prompting (only if requested)
    # ----------------------------------------------------------------------
    if args.snmpv3_enable:
        if not args.snmpv3_profile:
            print("[!] --snmpv3-profile is required when using --snmpv3-enable.")
            sys.exit(1)
        if not args.snmpv3_user:
            print("[!] --snmpv3-user is required when using --snmpv3-enable.")
            sys.exit(1)
        if not args.snmpv3_nms:
            print("[!] --snmpv3-nms is required when using --snmpv3-enable.")
            sys.exit(1)

        if args.snmpv3_auth_proto != "None" and not args.snmpv3_auth_pass:
            if args.auto:
                print("[!] --snmpv3-auth-pass is required when --snmpv3-auth-proto != None and --auto is used.")
                sys.exit(1)
            args.snmpv3_auth_pass = getpass.getpass("SNMPv3 Authentication Passphrase: ")

        if args.snmpv3_priv_proto != "None" and not args.snmpv3_priv_pass:
            if args.auto:
                print("[!] --snmpv3-priv-pass is required when --snmpv3-priv-proto != None and --auto is used.")
                sys.exit(1)
            args.snmpv3_priv_pass = getpass.getpass("SNMPv3 Privacy Passphrase: ")

    # LOAD HOSTS
    if args.check_only:
        hosts = [args.check_only.strip()]
    else:
        try:
            hosts = load_hosts(args.hosts)
        except Exception as e:
            print(f"[!] Could not read hosts file '{args.hosts}': {e}")
            sys.exit(1)
        if not hosts:
            print(f"[!] No hosts found in {args.hosts}.")
            sys.exit(1)

    scheme = "https" if args.https else "http"
    if args.check_only:
        print(f"Check-only mode: 1 host ({hosts[0]})")
    else:
        print(f"Loaded {len(hosts)} host(s) from {args.hosts}")
    print(f"Using scheme: {scheme.upper()}")
    print(f"Browser will be {'HEADFUL (visible)' if args.headful else 'headless'}.\n")

    results = []
    csv_fields = [
        "host",
        "timestamp",
        "login_ok",
        "default_login_ok",
        "fallback_login_ok",
        "apc_password_hardened",
        "admin_created",
        "new_admin_user",
        "snmpv3_configured",
        "snmpv3_access_page_enabled",
        "snmpv3_access_enabled",
        "snmpv3_profile",
        "snmpv3_user",
        "snmpv3_auth_proto",
        "snmpv3_priv_proto",
        "snmpv3_nms",
        "snmpv1_disabled",
        "status",
        "error",
    ]

    apc_new_password = args.apc_new_pass
    apc_password_prompted = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)

        for host in hosts:
            url = f"{scheme}://{host}/"
            print("\n==============================================================")
            print(f"[*] Processing host: {host}")
            print("==============================================================")
            print(f"    -> Opening {url} ...")

            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            result = {
                "host": host,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "login_ok": False,
                "default_login_ok": False,
                "fallback_login_ok": False,
                "apc_password_hardened": False,
                "admin_created": False,
                "new_admin_user": args.new_admin_user if args.create_admin else "",
                "snmpv3_configured": False,
                "snmpv3_access_page_enabled": False,
                "snmpv3_access_enabled": False,
                "snmpv3_profile": "",
                "snmpv3_user": "",
                "snmpv3_auth_proto": "",
                "snmpv3_priv_proto": "",
                "snmpv3_nms": "",
                "snmpv1_disabled": False,
                "status": "unknown",
                "error": "",
            }

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=args.timeout * 1000)

                # STEP 1 – default login
                print(f"    -> Trying default credentials {args.default_user}/{args.default_pass} …")
                logged_default = login_via_ui(page, args.default_user, args.default_pass, args.timeout)

                # check-only
                if args.check_only:
                    if logged_default is True:
                        print(f"\n[RESULT] {host}: DEFAULT CREDENTIALS VALID ({args.default_user}/{args.default_pass})")
                        sys.exit(0)
                    elif logged_default is False:
                        print(f"\n[RESULT] {host}: default credentials NOT valid")
                        sys.exit(2)
                    else:
                        print(f"\n[RESULT] {host}: could not determine (timeout/error)")
                        sys.exit(3)

                if logged_default:
                    result["login_ok"] = True
                    result["default_login_ok"] = True
                    result["status"] = "default_login_ok"
                    print(
                        f"    [✓] Default login succeeded as {args.default_user}. "
                        f"Hardening password and creating admin if requested…"
                    )

                    # STEP 2 – harden apc password
                    if apc_new_password is None:
                        if args.auto:
                            print("[!] Default creds valid but --apc-new-pass missing in --auto mode.")
                            result["status"] = "error"
                            result["error"] = "missing_apc_new_pass_in_auto_mode"
                            results.append(result)
                            context.close()
                            continue

                        if not apc_password_prompted:
                            while True:
                                p1 = getpass.getpass(f"New hardened password for '{args.default_user}': ")
                                p2 = getpass.getpass(f"Confirm new hardened password for '{args.default_user}': ")
                                if p1 != p2:
                                    print("Passwords do not match, try again.")
                                elif not p1:
                                    print("Password cannot be empty.")
                                else:
                                    apc_new_password = p1
                                    apc_password_prompted = True
                                    break

                    print(f"    -> Hardening password for '{args.default_user}' on {host}…")
                    hardened = change_password_via_ui(page, apc_new_password, current_password=args.default_pass)
                    if hardened:
                        result["apc_password_hardened"] = True
                    else:
                        result["error"] = result["error"] or "apc_harden_failed"

                    # STEP 3 – create admin (optional)
                    if args.create_admin:
                        print(f"    -> Creating new admin user '{args.new_admin_user}' …")
                        created = create_admin_user_via_ui(page, args.new_admin_user, args.new_admin_pass, args.headful)
                        if created:
                            result["admin_created"] = True
                            result["status"] = "admin_created"
                        else:
                            result["error"] = result["error"] or "admin_create_failed"

                    # STEP 4 – SNMP HARDENING (optional)  ✅ single source of truth
                    run_snmp_hardening_if_requested(args, page, result)

                else:
                    # STEP 2 – fallback login
                    print("    [-] Default login failed or undetermined. Trying fallback credentials…")

                    page.goto(url, wait_until="domcontentloaded", timeout=args.timeout * 1000)

                    if not args.current_pass:
                        print("    [-] No fallback credentials provided; skipping host.")
                        result["status"] = "login_failed"
                        result["error"] = "default_login_failed_no_fallback"
                        results.append(result)
                        context.close()
                        continue

                    print(f"    -> Trying fallback login as {args.current_user} …")
                    logged_fallback = login_via_ui(page, args.current_user, args.current_pass, args.timeout)

                    if not logged_fallback:
                        print("    [-] Fallback login FAILED.")
                        result["status"] = "login_failed"
                        result["error"] = "both_logins_failed"
                        results.append(result)
                        context.close()
                        continue

                    print("    [✓] Fallback login successful.")
                    result["login_ok"] = True
                    result["fallback_login_ok"] = True
                    result["status"] = "logged_in_fallback"

                    # STEP 3 – create admin (optional)
                    if args.create_admin:
                        print(f"    -> Creating new admin user '{args.new_admin_user}' …")
                        created = create_admin_user_via_ui(page, args.new_admin_user, args.new_admin_pass, args.headful)
                        if created:
                            result["admin_created"] = True
                            result["status"] = "admin_created"
                        else:
                            result["error"] = result["error"] or "admin_create_failed"

                    # STEP 4 – SNMP HARDENING (optional)  ✅ single source of truth
                    run_snmp_hardening_if_requested(args, page, result)

                if args.headful and not args.auto:
                    input("    -> Press ENTER to continue to the next host: ")

            except PlaywrightTimeoutError:
                print(f"    [!] TIMEOUT while processing {url}.")
                result["status"] = "timeout"
                result["error"] = "timeout"
            except Exception as e:
                print(f"    [!] Error while processing {host}: {e}")
                result["status"] = "error"
                result["error"] = str(e)
            finally:
                context.close()
                results.append(result)

        browser.close()

    # CSV report
    if args.report_csv:
        try:
            with open(args.report_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csv_fields)
                writer.writeheader()
                writer.writerows(results)
            print(f"\n[✓] CSV report written to {args.report_csv}")
        except Exception as e:
            print(f"\n[!] Failed to write CSV report: {e}")

    # JSON report
    if args.report_json:
        try:
            with open(args.report_json, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"[✓] JSON report written to {args.report_json}")
        except Exception as e:
            print(f"[!] Failed to write JSON report: {e}")

    print("\n[*] All hosts processed.\n")


if __name__ == "__main__":
    main()