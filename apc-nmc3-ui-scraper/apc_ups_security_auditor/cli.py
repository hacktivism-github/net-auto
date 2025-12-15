#!/usr/bin/env python3
import argparse
import getpass
import os
import sys
from typing import List, Optional

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
import csv
import json
#from datetime import datetime
from datetime import datetime, timezone
from apc_ups_security_auditor import __version__

DEFAULT_USER = "apc"
DEFAULT_PASS = "apc"


def load_hosts(path: str) -> List[str]:
    hosts = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            hosts.append(line)
    return hosts


def login_via_ui(page, username: str, password: str, timeout: float) -> Optional[bool]:
    """
    On the Schneider NMC3 login page:
      - Set Language = English
      - Type username and password
      - Click 'Log On'
      - Wait for home.htm

    Returns:
      True  -> login succeeded (default creds work)
      False -> login failed (default creds not accepted)
      None  -> some unexpected error
    """
    import time

    try:
        # Wait specifically for the username input, instead of "domcontentloaded"
        page.wait_for_selector("input[name='login_username']", timeout=5000)
        print("    [*] Login page ready.")

        
        # 1) Set language to English (you'll see the dropdown change)
        try:
            lang_select = page.locator("select").first
            # select_option can target by label:
            lang_select.select_option(label="English")
            print("    [*] Set language to English.")
        except Exception as e:
            print(f"    [debug] Could not set language (maybe already English): {e}")

        time.sleep(0.5)

        # 2) Fill username & password (you'll see the typing)
        filled = False

        # Preferred: use the explicit name= fields we know exist
        try:
            page.fill("input[name='login_username']", username)
            page.fill("input[name='login_password']", password)
            filled = True
        except Exception:
            # Fallback if something is different on some host/firmware
            try:
                page.locator("input[type='text']").first.fill(username)
                page.locator("input[type='password']").first.fill(password)
                filled = True
            except Exception as e:
                print(f"    [!] Could not find login fields: {e}")

        if not filled:
            return None

        print("    [*] Filled username and password.")
        

        # 3) Click "Log On"
        try:
            page.get_by_role("button", name="Log On").click()
        except Exception:
            # Fallback: any button with "Log On" text
            page.get_by_text("Log On", exact=False).click()

        print("    [*] Clicked Log On, waiting for home page...")
        # 4) Wait for home.htm (successful login)
        try:
            page.wait_for_url("**/home.htm*", timeout=timeout * 1000)
            print("    [✓] Login successful.")
            return True
        except PlaywrightTimeoutError:
            print("    [-] Login did not reach home.htm – default credentials probably NOT valid.")
            return False

    except PlaywrightTimeoutError:
        print("    [!] Timeout while loading login page.")
        return None
    except Exception as e:
        print(f"    [!] Unexpected error during login: {e}")
        return None

def change_password_via_ui(page, new_password: str, current_password: str = "apc") -> bool:
    """
    Fully automatic APC NMC3 password change via UI.
    Returns True if the flow appears to succeed, False otherwise.
    """

    import time
    print("    [*] Navigating to User Management (click-only navigation)...")

    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)

        # 1) Configuration
        print("      -> Clicking 'Configuration'")
        page.get_by_role("link", name="Configuration").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        # 2) Security
        print("      -> Clicking 'Security'")
        page.get_by_role("link", name="Security").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        # 3) Local Users
        print("      -> Clicking 'Local Users'")
        page.get_by_role("link", name="Local Users").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        # 4) Management (under userman.htm)
        print("      -> Clicking 'Management' (Local Users / userman.htm)")
        page.locator("a[href*='userman.htm']").first.click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.5)

        # 5) Click 'apc' (Super User)
        print("      -> Clicking user 'apc' under Super User Management")
        page.locator("a[href*='usercfg.htm'][href*='user=apc']").first.click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.5)

        # 6) Fill Current / New / Confirm password using password inputs
        print("      -> Filling Current / New / Confirm Password fields...")

        password_inputs = page.locator("input[type='password']")
        count = password_inputs.count()

        if count < 3:
            print(f"      [!] ERROR: Found only {count} password fields (expected 3).")
            return False

        # Order: Current, New, Confirm
        password_inputs.nth(0).fill(current_password)
        password_inputs.nth(1).fill(new_password)
        password_inputs.nth(2).fill(new_password)

        # 7) Click Next or Apply
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

        # 8) Final confirmation page
        print("      -> Waiting for final confirmation page...")
        try:
            page.wait_for_url("**/usrcnfrm*", timeout=5000)
        except Exception:
            # se o URL não bater certo, seguimos na mesma e tentamos clicar Apply
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


def create_admin_user_via_ui(
    page,
    new_username: str,
    new_password: str,
    headful: bool = False,
) -> bool:
    """
    Create a new Super User / Administrator account using the NMC3 web UI.

    Flow (as in your screenshots):
      - Configuration -> Security -> Local Users -> Management
      - Click "Add User"
      - Fill: User Name, New Password, Confirm Password, User Type, etc.
      - Click "Next"
      - On confirmation page, click "Apply"
    """

    import time
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    print("    [*] Navigating to Local Users to create admin user...")

    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)

        # 1) Configuration
        print("      -> Clicking 'Configuration'")
        page.get_by_role("link", name="Configuration").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        # 2) Security
        print("      -> Clicking 'Security'")
        page.get_by_role("link", name="Security").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        # 3) Local Users
        print("      -> Clicking 'Local Users'")
        page.get_by_role("link", name="Local Users").click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.3)

        # 4) Management (user list)
        print("      -> Opening 'Management' (user list)")
        page.locator("a[href*='userman.htm']").first.click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.5)

        # 5) Click "Add User"
        print("      -> Clicking 'Add User'…")
        added = False

        try:
            page.get_by_role("button", name="Add User").click(timeout=5000)
            added = True
        except Exception:
            pass

        if not added:
            try:
                page.locator("input[value='Add User']").first.click(timeout=5000)
                added = True
            except Exception:
                pass

        if not added:
            try:
                page.locator("a[href*='useradd']").first.click(timeout=5000)
                added = True
            except Exception:
                pass

        if not added:
            print("      [!] Could not find an 'Add User' control.")
            return False

        page.wait_for_load_state("domcontentloaded", timeout=10000)
        time.sleep(0.5)

        # After clicking "Add User" we land on usercfg.htm?user= (empty form)
        current_url = page.url
        print(f"      -> Now on page: {current_url}")

        # 6) Enable the user account
        print("      -> Enabling new user (ticking 'Enable' checkbox)…")
        try:
            # Preferred: checkbox with label "Enable"
            page.get_by_label("Enable").check()
        except Exception:
            # Fallback: first checkbox on the page
            try:
                page.locator("input[type='checkbox']").first.check()
            except Exception as e:
                print(f"      [!] Could not tick 'Enable' checkbox: {e}")
                return False

        # 7) Fill username
        print(f"      -> Filling new admin user: {new_username}")
        filled_username = False

        # Strategy 1: any obvious text input
        try:
            text_inputs = page.locator("input[type='text'], input:not([type])")
            if text_inputs.count() > 0:
                text_inputs.first.fill(new_username)
                filled_username = True
        except Exception:
            pass

        # Strategy 2: first non-hidden, non-password input
        if not filled_username:
            try:
                generic = page.locator(
                    "input:not([type='hidden']):not([type='password'])"
                ).first
                generic.fill(new_username)
                filled_username = True
            except Exception:
                pass

        if not filled_username:
            print("      [!] Could not locate username field (no suitable text input found).")
            return False

        # 8) Fill password & confirm password
        print("      -> Filling password fields…")
        pwd_inputs = page.locator("input[type='password']")
        count = pwd_inputs.count()
        if count < 2:
            print(f"      [!] Could not find two password fields (found {count}).")
            return False

        pwd_inputs.nth(0).fill(new_password)
        pwd_inputs.nth(1).fill(new_password)

        # 9) Select user role (Super User / Administrator) if possible
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

        # 10) Click "Next" on this page
        print("      -> Clicking 'Next'…")
        next_clicked = False
        try:
            # Try generic: any control whose value/text starts with 'Next'
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

        # Wait for confirmation page (usrcnfrm or similar)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            time.sleep(0.5)
        except Exception:
            pass

        # 11) On confirmation page, click "Apply"
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
        
def main():
    parser = argparse.ArgumentParser(
        description=(
            "APC/Schneider UPS (NMC3) automation tool: "
            "log in, optionally create a new admin user, and report results."
        )
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"apc-ups-audit {__version__}",
        help="Show program version and exit."
    )

    # ----------------------------------------------------------------------
    # INPUT / CONNECTION
    # ----------------------------------------------------------------------
    parser.add_argument(
        "--hosts",
        #required=True,
        help="Path to file containing UPS IPs/hostnames (one per line).",
    )

    parser.add_argument(
        "--check-only",
        metavar="HOST",
        help=(
            "Check ONLY one UPS host for default credentials (apc/apc). "
            "Print result and exit. Does not change anything."
        ),
    )

    parser.add_argument(
        "--https",
        action="store_true",
        help="Use HTTPS instead of HTTP to open the web UI.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Timeout (seconds) for page loads and login (default: 30).",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run the browser in headful mode (visible window). Default is headless.",
    )

    # ----------------------------------------------------------------------
    # DEFAULT CREDENTIALS (apc/apc)
    # ----------------------------------------------------------------------
    parser.add_argument(
        "--default-user",
        default="apc",
        help="Default username to test first (default: apc).",
    )
    parser.add_argument(
        "--default-pass",
        default="apc",
        help="Default password to test first (default: apc).",
    )
    parser.add_argument(
        "--apc-new-pass",
        help=(
            "New hardened password to set for the default user (e.g. 'apc') "
            "when default credentials are still valid. "
            "If omitted and not in --auto, you will be prompted once."
        ),
    )

    # ----------------------------------------------------------------------
    # LOGIN CREDENTIALS (CURRENT USER / FALLBACK)
    # ----------------------------------------------------------------------
    parser.add_argument(
        "--current-user",
        default="apc",
        help="Fallback username to use when default login fails (default: apc).",
    )
    parser.add_argument(
        "--current-pass",
        help=(
            "Fallback password to use when default login fails. "
            "If omitted and current-user != default-user, you may be prompted "
            "(except when using --auto)."
        ),
    )

    # ----------------------------------------------------------------------
    # PHASE 1 – CREATE NEW ADMIN USER
    # ----------------------------------------------------------------------
    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="Create a new Super User admin account on hosts where login succeeds.",
    )
    parser.add_argument(
        "--new-admin-user",
        help="New admin username to create (used with --create-admin).",
    )
    parser.add_argument(
        "--new-admin-pass",
        help=(
            "New admin password to set (used with --create-admin). "
            "If omitted and not in --auto, you will be prompted."
        ),
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run without interactive prompts (non-interactive mode).",
    )

    # ----------------------------------------------------------------------
    # REPORTING
    # ----------------------------------------------------------------------
    parser.add_argument(
        "--report-csv",
        help="Path to CSV report file to write scan results (optional).",
    )
    parser.add_argument(
        "--report-json",
        help="Path to JSON report file to write scan results (optional).",
    )

    args = parser.parse_args()

    # ----------------------------------------------------------------------
    # EARLY VALIDATION (hosts vs check-only)
    # ----------------------------------------------------------------------
    if not args.check_only and not args.hosts:
        parser.error("one of the arguments --hosts or --check-only is required")
    if args.check_only and args.hosts:
        parser.error("--check-only cannot be used together with --hosts")
    # ----------------------------------------------------------------------
    # VALIDATION / PASSWORD PROMPTS
    # ----------------------------------------------------------------------
    # NOTE: We do NOT prompt for a new APC password here anymore.
    #       It will only be requested if default login (apc/apc) succeeds
    #       AND --apc-new-pass was not provided.

    # current-pass (for fallback login)
    # Only prompt if current-user != default-user. For APC we rely on default
    # creds (apc/apc) first and only use fallback if explicitly configured.
    if args.current_user != args.default_user and not args.current_pass:
        if args.auto:
            print(
                "[!] --current-pass is required when using --current-user with --auto "
                "and it differs from --default-user."
            )
            sys.exit(1)
        else:
            args.current_pass = getpass.getpass(
                f"Password for fallback user {args.current_user}: "
            )

    # new-admin-user / new-admin-pass validation
    if args.create_admin:
        if not args.new_admin_user:
            print("[!] --new-admin-user is required when using --create-admin.")
            sys.exit(1)

        if not args.new_admin_pass:
            if args.auto:
                print(
                    "[!] --new-admin-pass is required together with --create-admin and --auto."
                )
                sys.exit(1)
            else:
                while True:
                    pwd1 = getpass.getpass("New admin user password: ")
                    pwd2 = getpass.getpass("Confirm new admin user password: ")
                    if pwd1 != pwd2:
                        print("Passwords do not match, try again.")
                    elif not pwd1:
                        print("Password cannot be empty.")
                    else:
                        args.new_admin_pass = pwd1
                        break

    # ----------------------------------------------------------------------
    # LOAD HOSTS
    # ----------------------------------------------------------------------

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
#    print(f"Loaded {len(hosts)} host(s) from {args.hosts}")
    if args.check_only:
        print(f"Check-only mode: 1 host ({hosts[0]})")
    else:
        print(f"Loaded {len(hosts)} host(s) from {args.hosts}")
    print(f"Using scheme: {scheme.upper()}")
    print(f"Browser will be {'HEADFUL (visible)' if args.headful else 'headless'}.\n")

    # ----------------------------------------------------------------------
    # PLAYWRIGHT LOOP
    # ----------------------------------------------------------------------
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

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
        "status",
        "error",
    ]

    # Cache for APC hardened password (prompt-once behavior)
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
                "login_ok": False,              # any successful login
                "default_login_ok": False,      # login with default creds?
                "fallback_login_ok": False,     # login with current-user/current-pass?
                "apc_password_hardened": False, # did we harden default user's password?
                "admin_created": False,
                "new_admin_user": args.new_admin_user if args.create_admin else "",
                "status": "unknown",
                "error": "",
            }

            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=args.timeout * 1000,
                )

                # ----------------------------------------------------------
                # STEP 1 – Try default credentials (apc/apc)
                # ----------------------------------------------------------
                print(
                    f"    -> Trying default credentials "
                    f"{args.default_user}/{args.default_pass} …"
                )
                logged_default = login_via_ui(
                    page,
                    username=args.default_user,
                    password=args.default_pass,
                    timeout=args.timeout,
                )

                # CHECK-ONLY: report and exit early (no changes)
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
                    # Default APS creds still valid
                    result["login_ok"] = True
                    result["default_login_ok"] = True
                    result["status"] = "default_login_ok"
                    print(
                        f"    [✓] Default login succeeded as {args.default_user}. "
                        f"Hardening password and creating admin if requested…"
                    )

                    # ------------------------------------------------------
                    # STEP 2 – Harden 'apc' password (only now decide password)
                    # ------------------------------------------------------
                    if apc_new_password is None:
                        if args.auto:
                            print(
                                "[!] Default APC credentials are valid but --apc-new-pass "
                                "was not provided while running with --auto."
                            )
                            result["status"] = "error"
                            result["error"] = "missing_apc_new_pass_in_auto_mode"
                            results.append(result)
                            context.close()
                            continue

                        if not apc_password_prompted:
                            while True:
                                pw1 = getpass.getpass(
                                    f"New hardened password for '{args.default_user}': "
                                )
                                pw2 = getpass.getpass(
                                    f"Confirm new hardened password for '{args.default_user}': "
                                )
                                if pw1 != pw2:
                                    print("Passwords do not match, try again.")
                                elif not pw1:
                                    print("Password cannot be empty.")
                                else:
                                    apc_new_password = pw1
                                    apc_password_prompted = True
                                    break

                    print(
                        f"    -> Hardening password for '{args.default_user}' "
                        f"on {host}…"
                    )
                    hardened = change_password_via_ui(
                        page,
                        new_password=apc_new_password,
                        current_password=args.default_pass,
                    )
                    if hardened:
                        print("    [✓] Default user password hardened successfully.")
                        result["apc_password_hardened"] = True
                    else:
                        print("    [!] Failed to harden default user password.")
                        result["error"] = result["error"] or "apc_harden_failed"

                    # ------------------------------------------------------
                    # STEP 3 – Create new admin user (if requested)
                    # ------------------------------------------------------
                    if args.create_admin:
                        print(
                            f"    -> Creating new admin user "
                            f"'{args.new_admin_user}' …"
                        )
                        created = create_admin_user_via_ui(
                            page,
                            new_username=args.new_admin_user,
                            new_password=args.new_admin_pass,
                            headful=args.headful,
                        )
                        if created:
                            print("    [✓] Admin user created successfully.")
                            result["admin_created"] = True
                            result["status"] = "admin_created"
                        else:
                            print("    [!] Admin user creation FAILED.")
                            result["admin_created"] = False
                            if not result["error"]:
                                result["error"] = "admin_create_failed"

                else:
                    # ------------------------------------------------------
                    # STEP 4 – Default login failed, try fallback (if any)
                    # ------------------------------------------------------
                    print(
                        "    [-] Default login failed or undetermined. "
                        "Trying fallback credentials (if configured)…"
                    )

                    # reload login page for a clean attempt
                    page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=args.timeout * 1000,
                    )

                    if not args.current_pass:
                        # No fallback password configured: give up on this host
                        print("    [-] No fallback credentials provided; skipping host.")
                        result["status"] = "login_failed"
                        result["error"] = "default_login_failed_no_fallback"
                        results.append(result)
                        context.close()
                        continue

                    print(
                        f"    -> Trying fallback login as {args.current_user} …"
                    )
                    logged_fallback = login_via_ui(
                        page,
                        username=args.current_user,
                        password=args.current_pass,
                        timeout=args.timeout,
                    )

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

                    # STEP 3 again – create admin (if requested) from fallback session
                    if args.create_admin:
                        print(
                            f"    -> Creating new admin user "
                            f"'{args.new_admin_user}' …"
                        )
                        created = create_admin_user_via_ui(
                            page,
                            new_username=args.new_admin_user,
                            new_password=args.new_admin_pass,
                            headful=args.headful,
                        )
                        if created:
                            print("    [✓] Admin user created successfully.")
                            result["admin_created"] = True
                            result["status"] = "admin_created"
                        else:
                            print("    [!] Admin user creation FAILED.")
                            result["admin_created"] = False
                            if not result["error"]:
                                result["error"] = "admin_create_failed"

                # Only pause between hosts if we're running headful AND not in --auto mode
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

    # ----------------------------------------------------------------------
    # REPORT: CSV
    # ----------------------------------------------------------------------
    if args.report_csv:
        try:
            with open(args.report_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csv_fields)
                writer.writeheader()
                for row in results:
                    writer.writerow(row)
            print(f"\n[✓] CSV report written to {args.report_csv}")
        except Exception as e:
            print(f"\n[!] Failed to write CSV report: {e}")

    # ----------------------------------------------------------------------
    # REPORT: JSON
    # ----------------------------------------------------------------------
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
