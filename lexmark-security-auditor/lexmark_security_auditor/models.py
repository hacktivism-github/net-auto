from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CheckResult:
    host: str
    timestamp: str
    scheme: str

    probe_result: str = "UNKNOWN"  # OPEN | AUTH | UNKNOWN
    evidence: str = ""
    http_status: str = "na"
    final_url: str = ""

    basic_security_applied: bool = False
    http_disabled: bool = False

    status: str = "ok"
    error: str = ""

    extra: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("extra") is None:
            d["extra"] = {}
        return d

