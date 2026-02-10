import argparse
import sys
from typing import List

from .runner import run
from .reporting import write_csv, write_json


def load_hosts(path: str) -> List[str]:
    hosts: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            hosts.append(line)
    return hosts


def parse_args():
    p = argparse.ArgumentParser(
        prog="lexmark-audit",
        description="Lexmark MX710 security auditor + hardening (Basic Security + disable HTTP) via Playwright.",
    )

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check-only", metavar="HOST", help="Check a single printer IP/host.")
    g.add_argument("--hosts", help="Path to file containing printer IPs/hosts (one per line).")

    p.add_argument("--https", action="store_true", help="Use HTTPS instead of HTTP.")
    p.add_argument("--timeout", type=float, default=12.0, help="Timeout seconds for page loads.")
    p.add_argument("--headful", action="store_true", help="Run browser visible (headful).")
    p.add_argument("--debug-html", action="store_true", help="Dump HTML on errors (helps tuning).")

    p.add_argument("--report-csv", help="Write results to CSV (optional).")
    p.add_argument("--report-json", help="Write results to JSON (optional).")

    # Workflows
    p.add_argument("--apply-basic-security", action="store_true",
                   help="Apply Basic Security workflow (set auth type UsernamePassword + user/pass).")
    p.add_argument("--disable-http", action="store_true",
                   help="Disable TCP 80 (HTTP) on ports page.")

    p.add_argument("--new-admin-user", help="Admin user ID to configure (e.g. bai-admin).")
    p.add_argument("--new-admin-pass", help="Admin password to configure.")

    return p.parse_args()


def main():
    args = parse_args()

    # validations
    if args.apply_basic_security and (not args.new_admin_user or not args.new_admin_pass):
        print("[!] --new-admin-user and --new-admin-pass are required with --apply-basic-security")
        sys.exit(1)

    # Note: disable-http can run without creds if OPEN; but for the retry-after-basic-security we need creds.
    if args.disable_http and args.apply_basic_security and (not args.new_admin_user or not args.new_admin_pass):
        print("[!] For disable-http retry after basic security, credentials are required. Provide --new-admin-user/--new-admin-pass.")
        sys.exit(1)

    if args.check_only:
        hosts = [args.check_only]
        print(f"Check-only mode: 1 host ({args.check_only})")
    else:
        try:
            hosts = load_hosts(args.hosts)
        except Exception as e:
            print(f"[!] Could not read hosts file '{args.hosts}': {e}")
            sys.exit(1)
        if not hosts:
            print(f"[!] No hosts found in {args.hosts}.")
            sys.exit(1)
        print(f"Batch mode: {len(hosts)} host(s) loaded from {args.hosts}")

    results = run(
        hosts=hosts,
        https=args.https,
        headful=args.headful,
        timeout=args.timeout,
        debug_html=args.debug_html,
        apply_basic=args.apply_basic_security,
        disable_http=args.disable_http,
        new_user=args.new_admin_user,
        new_pass=args.new_admin_pass,
    )

    if args.report_csv:
        try:
            write_csv(args.report_csv, results)
            print(f"\n[✓] CSV report written to {args.report_csv}")
        except Exception as e:
            print(f"\n[!] Failed to write CSV report: {e}")

    if args.report_json:
        try:
            write_json(args.report_json, results)
            print(f"[✓] JSON report written to {args.report_json}")
        except Exception as e:
            print(f"[!] Failed to write JSON report: {e}")

    print("\n[*] Done.\n")

