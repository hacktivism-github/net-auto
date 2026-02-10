import csv
import json
from typing import List
from .models import CheckResult


def write_csv(path: str, results: List[CheckResult]) -> None:
    rows = [r.to_dict() for r in results]
    if not rows:
        return

    # Flatten extra if present (keep as JSON string)
    for row in rows:
        row["extra"] = json.dumps(row.get("extra", {}), ensure_ascii=False)

    fieldnames = list(rows[0].keys())

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_json(path: str, results: List[CheckResult]) -> None:
    payload = [r.to_dict() for r in results]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

