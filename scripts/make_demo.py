"""Builds the demo data for Release Radio: "The Week Checkout Came Back".

Days 1 to 4 steady, days 5 and 6 rough (failures and a flaky test), day 7 a deploy
freeze, INC-07 opens on checkout on day 9 and resolves on day 11, then recovery.
Deterministic. Run from the repo root: python scripts/make_demo.py

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "skills" / "release-radio" / "assets" / "demo"
START = datetime(2026, 10, 26, tzinfo=timezone.utc)
SERVICES = ["checkout", "catalog", "search", "payments", "accounts"]
#        deploys runs failed flaky burn
PLAN = [(3, 8, 0, 0, 0.4), (4, 8, 0, 0, 0.5), (3, 8, 0, 0, 0.4), (4, 9, 0, 0, 0.6),
        (3, 9, 3, 1, 0.9), (2, 8, 2, 2, 0.8), (0, 0, 0, 0, 0.3),
        (3, 8, 0, 0, 0.5), (2, 9, 1, 0, 2.3), (1, 8, 0, 1, 1.6),
        (2, 8, 0, 0, 0.9), (4, 9, 0, 0, 0.5), (4, 8, 0, 0, 0.4), (5, 9, 0, 0, 0.4)]


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    rng = random.Random(7)
    OUT.mkdir(parents=True, exist_ok=True)
    deploys, runs, slo = [], [], []
    for i, (n_dep, n_run, n_fail, n_flaky, burn) in enumerate(PLAN):
        day = START + timedelta(days=i)
        for k in range(n_dep):
            deploys.append({"id": f"d-{i + 1:02d}{k + 1}", "at": iso(day + timedelta(hours=9 + 2 * k, minutes=rng.randint(0, 50))),
                            "service": SERVICES[(i + k) % len(SERVICES)], "status": "success"})
        fail_slots = set(rng.sample(range(n_run), n_fail)) if n_run else set()
        flaky_slots = set(rng.sample(sorted(set(range(n_run)) - fail_slots), n_flaky)) if n_run else set()
        for k in range(n_run):
            run = {"id": f"r-{i + 1:02d}{k + 1:02d}", "started_at": iso(day + timedelta(hours=8 + k, minutes=5)),
                   "branch": "main", "status": "failed" if k in fail_slots else "passed",
                   "service": SERVICES[(i + k) % len(SERVICES)],
                   "flaky_failures": ["test_cart_total_rounding_b"] if k in flaky_slots else []}
            runs.append(run)
        runs.append({"id": f"r-{i + 1:02d}fb", "started_at": iso(day + timedelta(hours=12)), "branch": "feature/new-banner",
                     "status": "failed", "flaky_failures": []})
        slo.append({"date": day.date().isoformat(), "slo": "checkout availability 99.9%", "burn_rate": burn})
    # Day 9 rollback, after the incident opened.
    deploys.append({"id": "d-09rb", "at": iso(START + timedelta(days=8, hours=14)), "service": "checkout", "status": "rolled_back"})
    incidents = [{"id": "INC-07", "service": "checkout", "severity": "SEV2",
                  "opened_at": iso(START + timedelta(days=8, hours=10, minutes=12)),
                  "resolved_at": iso(START + timedelta(days=10, hours=12, minutes=40))}]
    files = {
        "manifest": {"subject": "Storefront", "title": "The Week Checkout Came Back", "as_of": iso(START + timedelta(days=13, hours=22)),
                     "days": 14, "provenance": {
                         "deployments": {"source": "github deployments (demo)", "fetched_at": "2026-11-08T22:00:00Z"},
                         "ci_runs": {"source": "github actions (demo)", "fetched_at": "2026-11-08T22:00:00Z"},
                         "incidents": {"source": "incident tracker (demo)", "fetched_at": "2026-11-08T22:00:00Z"},
                         "slo_daily": {"source": "observability SLO export (demo)", "fetched_at": "2026-11-08T22:00:00Z"}}},
        "deployments": {"deployments": deploys},
        "ci_runs": {"runs": runs},
        "incidents": {"incidents": incidents},
        "slo_daily": {"days": slo},
    }
    for name, data in files.items():
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"Wrote demo data to {OUT}")


if __name__ == "__main__":
    main()
