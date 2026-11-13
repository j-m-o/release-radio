# Data contract

Put these files in one folder. Any can be missing: the sign off then says the signal carried static, and The Record says which source was missing. A file that fails the contract is set aside the same way.

## manifest.json

```json
{"subject": "Storefront", "title": "Optional broadcast title", "as_of": "2026-11-08T22:00:00Z", "days": 14,
 "provenance": {"deployments": {"source": "github deployments", "fetched_at": "2026-11-08T22:00:00Z"}}}
```

## deployments.json

```json
{"deployments": [{"id": "d-0101", "at": "2026-10-26T09:12:00Z", "service": "checkout", "status": "success"}]}
```

`status` is `success` or `rolled_back`. Required: `id`, `at`.

## ci_runs.json

```json
{"runs": [{"id": "r-0101", "started_at": "2026-10-26T08:05:00Z", "branch": "main", "status": "passed",
           "service": "checkout", "flaky_failures": ["test_cart_total_rounding_b"]}]}
```

A run fails when `status` is `failed`, `failure` or `error`. Without `status`, a run fails when `real_failures` is non-empty (the Quality Tea Leaves shape). Only `branch: main` is played. Required: `id`, `started_at`.

## incidents.json

```json
{"incidents": [{"id": "INC-07", "service": "checkout", "severity": "SEV2",
                "opened_at": "2026-11-03T10:12:00Z", "resolved_at": "2026-11-05T12:40:00Z"}]}
```

Leave `resolved_at` out while an incident is still open. Required: `id`, `opened_at`.

## slo_daily.json

```json
{"days": [{"date": "2026-11-03", "slo": "checkout availability 99.9%", "burn_rate": 2.3}]}
```

Required: `date`, `burn_rate` (a number; 1.0 means the error budget burns exactly on pace).

## Never include

Names, emails or handles of people. Commit messages. Anything secret.
