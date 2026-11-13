"""Data contract checker for Release Radio.

A file that fails is set aside. If a source is missing or set aside, the broadcast
carries static: the sign off and The Record say which data was missing.

Usage: python check_data.py path/to/data   (exit 1 when any file fails)

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import json
import sys
from datetime import datetime
from pathlib import Path

CONTRACT = {
    "deployments": ("deployments", ["id", "at"], ["at"]),
    "ci_runs": ("runs", ["id", "started_at"], ["started_at"]),
    "incidents": ("incidents", ["id", "opened_at"], ["opened_at", "resolved_at"]),
    "slo_daily": ("days", ["date", "burn_rate"], []),
}


def _is_time(v):
    try:
        datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def check(name, data):
    if name not in CONTRACT:
        return []
    key, fields, times = CONTRACT[name]
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        return [f"'{key}' must be a list"]
    problems = []
    for i, rec in enumerate(data[key]):
        if not isinstance(rec, dict):
            problems.append(f"{key}[{i}] is not an object")
            continue
        gone = [f for f in fields if f not in rec]
        if gone:
            problems.append(f"{key}[{i}] missing {', '.join(gone)}")
        for t in times:
            if rec.get(t) and not _is_time(rec[t]):
                problems.append(f"{key}[{i}].{t} is not an ISO time")
        if name == "slo_daily" and not isinstance(rec.get("burn_rate"), (int, float)):
            problems.append(f"{key}[{i}].burn_rate must be a number")
        if len(problems) >= 3:
            break
    return problems[:3]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    failed = 0
    for name in CONTRACT:
        p = Path(argv[0]) / f"{name}.json"
        if not p.exists():
            print(f"  -  {name}.json not provided (the broadcast will carry static)")
            continue
        try:
            problems = check(name, json.loads(p.read_text()))
        except ValueError as e:
            problems = [f"not valid JSON ({e})"]
        print(("FAIL " if problems else "OK   ") + f"{name}.json" + (": " + "; ".join(problems) if problems else ""))
        failed += bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
