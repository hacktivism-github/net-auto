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

        # 4) Management (user list) - you already used userman.htm before
        print("      -> Opening 'Management' (user list)")
        page.locator("a[href*='userman.htm']").first.click(timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.5)

        # 5) Click "Add User" or equivalent
        print("      -> Clicking 'Add User'...")
        added = False
        try:
            page.get_by_role("button", name="Add User").click(timeout=5000)
            added = True
        except Exception:
            pass

        if not added:
            # Older firmwares may use an <input> or link instead of a button
            try:
                page.locator("input[value='Add User']").first.click(timeout=5000)
                added = True
            except Exception:
                pass

        if not added:
            print("      [!] Could not find an 'Add User' control.")
            return False

        page.wait_for_load_state("domcontentloaded")
        time.sleep(0.5)

        # 6) Fill username and password fields
        print(f"      -> Filling new admin user: {new_username}")

        # These selectors may need adjustment based on actual HTML;
        # start with simple name-based or label-based selectors.
        page.fill("input[name='username']", new_username)

        # Assume password fields are type='password' and there are at least two:
        pwd_inputs = page.locator("input[type='password']")
        if pwd_inputs.count() < 2:
            print("      [!] Could not find both password fields.")
            return False

        pwd_inputs.nth(0).fill(new_password)
        pwd_inputs.nth(1).fill(new_password)

        # 7) Select Super User role if necessary (depends on UI)
        # Example: dropdown or radio button:
        try:
            # Example: a select with name 'user_role' or similar
            role_select = page.locator("select[name='user_role']")
            if role_select.count() > 0:
                role_select.select_option("Super User")
            else:
                # Fallback for radio/checkbox labelled "Super User"
                page.get_by_label("Super User").check()
        except Exception:
            # if role defaults to Super User on this page, it's ok
            pass

        # 8) Click Apply / OK
        print("      -> Clicking 'Apply' to create new admin user...")
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

        page.wait_for_load_state("networkidle", timeout=10000)
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
        description="Headful APC/Schneider UPS audit (NMC3) for default credentials "
                    "via full UI automation."
    )
    parser.add_argument(
        "--hosts",
        required=True,
        help="Path to file containing UPS IPs/hostnames (one per line).",
    )
    parser.add_argument(
        "--username",
        default="apc",
        help="Username to test (default: apc).",
    )
    parser.add_argument(
        "--default-pass",
        default="apc",
        help="Default password to test (default: apc).",
    )
    parser.add_argument(
        "--new-pass",
        help="New password to set when default is found. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--current-user",
        default="apc",
        help="Username to use for initial login (default: apc)",
    )
    parser.add_argument(
        "--current-pass",
        help="Password to use for initial login. If omitted, will prompt.",
    )
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
        help="New admin password to set (used with --create-admin). If omitted, will prompt.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run without interactive prompts for admin creation (non-interactive mode).",
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help="Use HTTPS instead of HTTP to open the web UI.",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run the browser in headful mode (visible window). Default is headless.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout (seconds) for page loads and login (default: 30).",
    )
    parser.add_argument(
        "--auto-change",
        action="store_true",
        help="Automatically change password on hosts with default credentials, without prompting.",
    )
    parser.add_argument(
        "--report-csv",
        help="Path to CSV report file to write scan results (optional).",
    )
    parser.add_argument(
        "--report-json",
        help="Path to JSON report file to write scan results (optional).",
    )
    args = parser.parse_args()

    if not args.new_pass:
        pw1 = getpass.getpass("New password to use on devices with default creds: ")
        pw2 = getpass.getpass("Confirm new password: ")
        if pw1 != pw2:
            print("Passwords do not match. Aborting.")
            sys.exit(1)
        args.new_pass = pw1

    # If we are creating an admin and no new-admin-pass was provided, prompt once
    if args.create_admin and not args.new_admin_pass:
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

    # If no current-pass was provided, prompt once
    if not args.current_pass:
        args.current_pass = getpass.getpass(f"Password for {args.current_user}: ")

    scheme = "https" if args.https else "http"
    hosts = load_hosts(args.hosts)

    print(f"Loaded {len(hosts)} host(s) from {args.hosts}")
    print(f"Using scheme: {scheme.upper()}")
    print(f"Browser will be {'HEADFUL (visible)' if args.headful else 'headless'}.\n")
    results = []  # para CSV/JSON    

    default_hosts = []
    not_default_hosts = []
    unknown_hosts = []


    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        for host in hosts:
            url = f"{scheme}://{host}/"
            print(f"[*] Opening {url} ...")

            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()

            # valores por defeito para o relatório
            result = {
                "host": host,
                "timestamp": datetime.utcnow().isoformat(),
                #"default_credentials": None,   # True / False / None | Removed on version 0.1.4
                #"password_changed": False, # Removed on version 0.1.4
                "login_ok": False, # Added on version 0.1.4
                "admin_created": False, # Added on version 0.1.4
                "new_admin_user": args.new_admin_user if args.create_admin else "", # Added on version 0.1.4
                "status": "unknown",           # ok / timeout / error / unknown
                "error": "",
            }

            try:
                page.goto(url, wait_until="domcontentloaded",
                          timeout=args.timeout * 1000)

'''
                logged_in = login_via_ui(
                    page,
                    username=args.username,
                    password=args.default_pass,
                    timeout=args.timeout,
                )

                if logged_in is True:
                    print(f"    [+] Default credentials are valid on {host}.")
                    result["default_credentials"] = True
                    result["status"] = "ok"
                    # decidir se muda password automaticamente ou pergunta
                    do_change = False
                    if args.auto_change:
                        do_change = True
                        print("    [*] --auto-change enabled: will change password automatically.")
                    else:
                        while True:
                            ans = input(
                                "    -> Attempt password change via web UI now? [y/N]: "
                            ).strip().lower()
                            if ans in ("y", "yes"):
                                do_change = True
                                break
                            elif ans in ("n", "no", ""):
                                do_change = False
                                print("    [ ] Skipping password change on this host.")
                                break
                            else:
                                print("    Please answer 'y' or 'n'.")

                    if do_change:
                        success = change_password_via_ui(
                            page,
                            new_password=args.new_pass,
                            current_password=args.default_pass,
                        )
                        if success:
                            result["password_changed"] = True
                        else:
                            result["password_changed"] = False
                            result["error"] = "password_change_failed"

                elif logged_in is False:
                    print(f"    [-] Default credentials are NOT accepted on {host}.")
                    result["default_credentials"] = False
                    result["status"] = "ok"
                else:
                    print(f"    [!] Could not determine login status for {host}.")
                    result["default_credentials"] = None
                    result["status"] = "unknown"

                if args.headful:
                    input("    -> Press ENTER to continue to the next host: ")

            except PlaywrightTimeoutError:
                print(f"    [!] Timeout while loading {url}.")
                result["status"] = "timeout"
                result["error"] = "timeout"
            except Exception as e:
                print(f"    [!] Error while processing {host}: {e}")
                result["status"] = "error"
                result["error"] = str(e)
            finally:
                results.append(result)
                context.close()

        browser.close()
'''

                if not logged_in:
                    print(f"    [-] Login failed for {host} with {args.current_user}.")
                    result["status"] = "login_failed"
                    results.append(result)
                    context.close()
                    continue

                print(f"    [✓] Login successful on {host} as {args.current_user}.")
                result["login_ok"] = True
                result["status"] = "ok"

                # ---- PHASE 1: CREATE NEW ADMIN ----
                if args.create_admin:
                    do_create = True

                    if not args.auto:
                        # Ask per host if not in --auto mode
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
                        success = create_admin_user_via_ui(
                            page,
                            new_username=args.new_admin_user,
                            new_password=args.new_admin_pass,
                            headful=args.headful,
                        )
                        if success:
                            result["admin_created"] = True
                        else:
                            result["admin_created"] = False
                            result["status"] = "admin_create_failed"
                            result["error"] = "create_admin_failed"

                if args.headful:
                    input("    -> Press ENTER to continue to the next host: ")

            except PlaywrightTimeoutError:
                print(f"    [!] Timeout while processing {url}.")
                result["status"] = "timeout"
                result["error"] = "timeout"
            except Exception as e:
                print(f"    [!] Error while processing {host}: {e}")
                result["status"] = "error"
                result["error"] = str(e)
            finally:
                results.append(result)
                context.close()

        browser.close()
        
    # escrever CSV se solicitado
    if args.report_csv:
        #fieldnames = ["host", "timestamp", "default_credentials", | Removed on version 0.1.4
        #              "password_changed", "status", "error"] | Removed on version 0.1.4
        fieldnames = ["host", "timestamp", "login_ok", "admin_created",
                      "new_admin_user", "status", "error"]  # Added on version 0.1.4
        try:
            with open(args.report_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in results:
                    writer.writerow(row)
            print(f"\n[✓] CSV report written to {args.report_csv}")
        except Exception as e:
            print(f"\n[!] Failed to write CSV report: {e}")

    # escrever JSON se solicitado
    if args.report_json:
        try:
            with open(args.report_json, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"[✓] JSON report written to {args.report_json}")
        except Exception as e:
            print(f"[!] Failed to write JSON report: {e}")

    print("\n=== SUMMARY ===")
    print(f"Hosts with DEFAULT credentials still valid: {len(default_hosts)}")
    for h in default_hosts:
        print(f"  - {h}")

    print(f"\nHosts where default is NOT accepted: {len(not_default_hosts)}")
    for h in not_default_hosts:
        print(f"  - {h}")

    print(f"\nHosts with UNKNOWN status: {len(unknown_hosts)}")
    for h in unknown_hosts:
        print(f"  - {h}")


if __name__ == "__main__":
    main()
