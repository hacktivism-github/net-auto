#!/usr/bin/env python3
import argparse
import getpass
import sys
from typing import List, Optional

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
import csv
import json
from datetime import datetime


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
        page.wait_for_load_state("domcontentloaded", timeout=timeout * 1000)

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
        try:
            page.get_by_label("User Name").fill(username)
            page.get_by_label("Password").fill(password)
            filled = True
        except Exception:
            # Fallback if labels are not wired correctly
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
            print("    [✓] Login successful (default creds worked).")
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
    Create a new Super User admin account using the NMC3 web UI.

    Returns True if creation appears successful, False otherwise.
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

        # Try button
        try:
            page.get_by_role("button", name="Add User").click(timeout=5000)
            added = True
        except Exception:
            pass

        # Try input[value='Add User']
        if not added:
            try:
                page.locator("input[value='Add User']").first.click(timeout=5000)
                added = True
            except Exception:
                pass

        # Try explicit link to useradd.htm
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

        # Some firmwares incorrectly land on usercfg.htm?user=
        current_url = page.url.lower()
        if "usercfg.htm" in current_url and "user=" in current_url and current_url.endswith("user="):
            print("      [!] Landed on usercfg.htm?user= (empty). Trying fallback to useradd.htm …")
            try:
                # Simple fallback: swap to useradd.htm
                fallback_url = current_url.replace("usercfg.htm?user=", "useradd.htm")
                page.goto(fallback_url, timeout=8000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(0.5)
                current_url = page.url.lower()
            except Exception as e:
                print(f"      [!] Fallback to useradd.htm failed: {e}")
                return False

        print(f"      -> Now on page: {current_url}")

        # 6) Ensure access is enabled if such checkbox exists
        try:
            enable_chk = page.get_by_label("Enable")
            if enable_chk.is_visible():
                enable_chk.check()
                print("      -> Enabled access for new user.")
        except Exception:
            # Not all firmwares need this or map the label the same way
            pass

        # 7) Fill username
        print(f"      -> Filling new admin user: {new_username}")
        filled_username = False

        # Try a named username input first
        try:
            page.fill("input[name='username']", new_username)
            filled_username = True
        except Exception:
            pass

        # Try label-based selector
        if not filled_username:
            try:
                page.get_by_label("User Name").fill(new_username)
                filled_username = True
            except Exception:
                pass

        # Fallback: first empty text input
        if not filled_username:
            try:
                txt = page.locator("input[type='text']").first
                txt.fill(new_username)
                filled_username = True
            except Exception:
                pass

        if not filled_username:
            print("      [!] Could not locate username field.")
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

        # 9) Select Super User / Administrator role
        print("      -> Setting user role to Super User (if possible)…")
        try:
            # Try a role dropdown with a reasonable name
            role_select = page.locator("select[name='user_role'], select[name='usertype'], select[name*='Type']")
            if role_select.count() > 0:
                try:
                    role_select.first.select_option(label="Super User")
                except Exception:
                    # Fallback to Administrator if Super User is not present
                    try:
                        role_select.first.select_option(label="Administrator")
                    except Exception:
                        pass
            else:
                # Maybe it's a radio/checkbox
                try:
                    page.get_by_label("Super User").check()
                except Exception:
                    pass
        except Exception:
            # If nothing works, we just keep the default role.
            pass

        # 10) Click Apply / OK
        print("      -> Clicking 'Apply' to create new admin user…")
        submitted = False
        try:
            page.get_by_role("button", name="Apply").click(timeout=5000)
            submitted = True
        except Exception:
            pass

        if not submitted:
            try:
                page.locator("input[value='Apply']").first.click(timeout=5000)
                submitted = True
            except Exception:
                pass

        if not submitted:
            print("      [!] Could not click Apply to create user.")
            return False

        # 11) Wait for completion
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            # not fatal; some firmwares don't reach networkidle cleanly
            pass

        time.sleep(0.5)
        print("    [✓] New admin user creation flow completed (UI).")
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

    # ----------------------------------------------------------------------
    # INPUT / CONNECTION
    # ----------------------------------------------------------------------
    parser.add_argument(
        "--hosts",
        required=True,
        help="Path to file containing UPS IPs/hostnames (one per line).",
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help="Use HTTPS instead of HTTP to open the web UI.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout (seconds) for page loads and login (default: 30).",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run the browser in headful mode (visible window). Default is headless.",
    )

    # ----------------------------------------------------------------------
    # LOGIN CREDENTIALS (CURRENT USER)
    # ----------------------------------------------------------------------
    parser.add_argument(
        "--current-user",
        default="apc",
        help="Username to use for initial login (default: apc).",
    )
    parser.add_argument(
        "--current-pass",
        help="Password to use for initial login. If omitted, you will be prompted.",
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
        help="Run without interactive prompts for admin creation (non-interactive mode).",
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
    # VALIDATION / PASSWORD PROMPTS
    # ----------------------------------------------------------------------
    # current-pass (for login)
    if not args.current_pass:
        args.current_pass = getpass.getpass(f"Password for {args.current_user}: ")

    # new-admin-user / new-admin-pass validation
    if args.create_admin:
        if not args.new_admin_user:
            print("[!] --new-admin-user is required when using --create-admin.")
            sys.exit(1)

        if not args.new_admin_pass:
            if args.auto:
                print("[!] --new-admin-pass is required together with --create-admin and --auto.")
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
    try:
        hosts = load_hosts(args.hosts)
    except Exception as e:
        print(f"[!] Could not read hosts file '{args.hosts}': {e}")
        sys.exit(1)

    if not hosts:
        print(f"[!] No hosts found in {args.hosts}.")
        sys.exit(1)

    scheme = "https" if args.https else "http"
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
        "admin_created",
        "new_admin_user",
        "status",
        "error",
    ]

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
                "timestamp": datetime.utcnow().isoformat(),
                "login_ok": False,
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

                # LOGIN PHASE
                print(f"    -> Logging in as {args.current_user} …")
                logged_in = login_via_ui(
                    page,
                    username=args.current_user,
                    password=args.current_pass,
                    timeout=args.timeout,
                )

                if not logged_in:
                    # logged_in can be False or None; treat as failure here
                    print("    [-] Login FAILED.")
                    result["status"] = "login_failed"
                    result["error"] = "login_failed"
                    results.append(result)
                    context.close()
                    continue

                print("    [✓] Login successful.")
                result["login_ok"] = True
                result["status"] = "logged_in"

                # PHASE 1: CREATE NEW ADMIN USER
                if args.create_admin:
                    do_create = True

                    if not args.auto:
                        while True:
                            ans = input(
                                f"    -> Create new admin user '{args.new_admin_user}' on {host}? [y/N]: "
                            ).strip().lower()
                            if ans in ("y", "yes"):
                                do_create = True
                                break
                            elif ans in ("n", "no", ""):
                                do_create = False
                                break
                            else:
                                print("    Please answer 'y' or 'n'.")

                    if do_create:
                        print(f"    -> Creating new admin user '{args.new_admin_user}' …")
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
                            result["status"] = "admin_create_failed"
                            result["error"] = "admin_create_failed"

                if args.headful:
                    input("    -> Press ENTER to continue to the next host…")

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
