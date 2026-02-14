# Lexmark Security Auditor

## Install (editable)
pip install -e .

## Playwright browser install (one-time)
python -m playwright install chromium

## Examples
lexmark-audit --check-only <IP address> --https --headful --apply-basic-security --new-admin-user <your admin user> --new-admin-pass "<your secure pass>"
lexmark-audit --hosts printers.txt --https --disable-http --apply-basic-security --new-admin-user <your admin user> --new-admin-pass "<your secure pass>" --report-csv out.csv