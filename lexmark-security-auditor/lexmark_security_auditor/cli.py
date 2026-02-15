import argparse
import sys
from typing import List, Optional
from importlib.metadata import version as pkg_version, PackageNotFoundError

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

def get_version() -> str:
    """
    Returns installed package version.
    Falls back to '0.0.0-dev' if running locally without installation.
    """
    try:
        return pkg_version("lexmark-security-auditor")
    except PackageNotFoundError:
        return "0.0.0-dev"


def parse_args(argv: Optional[List[str]] = None):
    p = argparse.ArgumentParser(
        prog="lexmark-audit",
        description="Lexmark MX710 security auditor + hardening (Basic Security + disable HTTP) via Playwright.",
    )

    p.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
        help="Show version and exit.",
    )

    # p.add_argument(
    #     "-v", "--version", 
    #     action="version", 
    #     version=f"lexmark_security_auditor {__version__}"
    #     )        

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--check-only", 
        metavar="HOST", 
        help="Check a single printer IP/host."
        )
    
    g.add_argument(
        "--hosts", 
        help="Path to file containing printer IPs/hosts (one per line)."
        )

    p.add_argument(
        "--https", 
        action="store_true", 
        help="Use HTTPS instead of HTTP."
        )
    
    p.add_argument(
        "--timeout", 
        type=float, 
        default=12.0, 
        help="Timeout seconds for page loads."
        )
    
    p.add_argument(
        "--headful", 
        action="store_true", 
        help="Run browser visible (headful)."
        )
    
    p.add_argument(
        "--debug-html",
        action="store_true",
        help="Dump HTML on errors (helps tuning selectors).",
        )

    p.add_argument(
        "--report-csv", 
        help="Write results to CSV (optional)."
        )
    
    p.add_argument(
        "--report-json", 
        help="Write results to JSON (optional)."
        )

    p.add_argument(
        "--apply-basic-security", 
        action="store_true",
        help="Apply Basic Security workflow (Configurações -> Segurança -> Configuração de segurança)."
        )
    
    p.add_argument(
        "--disable-http", 
        action="store_true",
        help="Disable TCP 80 (HTTP) in 'Acesso à porta TCP/IP'."
        )

    p.add_argument(
        "--new-admin-user", 
        help="Admin user ID."
        )
    
    p.add_argument(
        "--new-admin-pass", 
        help="Admin password."
        )
    
    p.add_argument(
        "--auth-user", 
        help="Username for authenticated EWS access"
        )
    
    p.add_argument(
        "--auth-pass", 
        help="Password for authenticated EWS access"
        )

    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    # if args.apply_basic_security or args.disable_http:
    #     if not args.new_admin_user or not args.new_admin_pass:
    #         raise SystemExit("[!] --new-admin-user and --new-admin-pass are required for hardening actions.")

    # Se for aplicar basic security, precisa de new-admin-*
    if args.apply_basic_security:
        if not args.new_admin_user or not args.new_admin_pass:
            print("[!] --new-admin-user and --new-admin-pass are required with --apply-basic-security.")
            sys.exit(1)

    # Se for apenas desactivar HTTP sem aplicar basic security,
    # precisa de auth-user/pass
    if args.disable_http and not args.apply_basic_security:
        if not args.auth_user or not args.auth_pass:
            print("[!] --auth-user and --auth-pass are required when disabling HTTP on already protected devices.")
            sys.exit(1)


    if args.check_only:
        hosts = [args.check_only]
    else:
        hosts = load_hosts(args.hosts)
        if not hosts:
            raise SystemExit(f"[!] No hosts found in {args.hosts}.")

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
        auth_user=args.auth_user,
        auth_pass=args.auth_pass,
    )


    if args.report_csv and results:
        write_csv(args.report_csv, results)
        print(f"[✓] CSV report written to {args.report_csv}")

    if args.report_json and results:
        write_json(args.report_json, results)
        print(f"[✓] JSON report written to {args.report_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
