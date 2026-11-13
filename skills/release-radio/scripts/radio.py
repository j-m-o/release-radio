"""Release Radio: WREL's Release Hour.

Turns a window of deploys, CI runs, incidents and SLO burn into a 1940s radio
broadcast. Rules sort each day into fair skies, rough going, a freeze, an
incident or the all clear; the announcer's script is written from those rules
and nothing else. Every line is backed by evidence in The Record. The same data
always makes the same broadcast. Read-only and standard library only; the
ElevenLabs voice is optional and the only network step.

Usage:
  python radio.py demo [--out DIR]
  python radio.py play --data DIR [--out DIR] [--days 14] [--as-of ISO]
  ... --voice elevenlabs --voice-id ID      (render Clyde through the ElevenLabs API)
  ... --voice-file read.mp3-as-wav          (use one recorded read of the whole script)

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
DEMO = SKILL_DIR / "assets" / "demo"
THEME = SKILL_DIR / "assets" / "theme" / "wrel_theme.wav"
SOURCES = ["manifest", "deployments", "ci_runs", "incidents", "slo_daily"]


def parse_ts(v):
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


def load_sources(data_dir):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import check_data

    found, problems = {}, {}
    for name in SOURCES:
        p = Path(data_dir) / f"{name}.json"
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
        except ValueError as e:
            problems[name] = [f"not valid JSON ({e})"]
            continue
        issues = check_data.check(name, data)
        (problems.__setitem__(name, issues) if issues else found.__setitem__(name, data))
    return found, problems


def run_failed(run):
    if "status" in run:
        return run["status"] in ("failed", "failure", "error")
    return bool(run.get("real_failures"))


def gather_days(src, start, days):
    """Group the raw records into one dict per day. Feature branches are ignored."""
    out = []
    for i in range(days):
        d0 = start + timedelta(days=i)
        d1 = d0 + timedelta(days=1)
        day = {"index": i, "date": d0.date().isoformat(), "deploys": [], "rollbacks": [], "runs": [],
               "incidents_open": [], "incidents_opened": [], "incidents_resolved": [], "burn": None}
        for dp in src.get("deployments", {}).get("deployments", []):
            if d0 <= parse_ts(dp["at"]) < d1:
                (day["rollbacks"] if dp.get("status") == "rolled_back" else day["deploys"]).append(dp)
        for r in src.get("ci_runs", {}).get("runs", []):
            if r.get("branch", "main") == "main" and d0 <= parse_ts(r["started_at"]) < d1:
                day["runs"].append(r)
        for inc in src.get("incidents", {}).get("incidents", []):
            opened = parse_ts(inc["opened_at"])
            resolved = parse_ts(inc["resolved_at"]) if inc.get("resolved_at") else None
            if opened < d1 and (resolved is None or resolved >= d0):
                day["incidents_open"].append(inc)
            if d0 <= opened < d1:
                day["incidents_opened"].append(inc)
            if resolved and d0 <= resolved < d1:
                day["incidents_resolved"].append(inc)
        burns = [x["burn_rate"] for x in src.get("slo_daily", {}).get("days", []) if x["date"] == day["date"]]
        day["burn"] = max(burns) if burns else None
        out.append(day)
    return out


def day_state(d, recovered):
    runs, fails = d["runs"], [r for r in d["runs"] if run_failed(r)]
    resolving = bool(d["incidents_resolved"]) and all(i in d["incidents_resolved"] for i in d["incidents_open"])
    if not (d["deploys"] or d["rollbacks"] or runs) and not d["incidents_open"]:
        return "freeze", fails, resolving
    if d["incidents_open"] and not resolving:
        return "incident", fails, resolving
    if fails:
        return "failed", fails, resolving
    return ("recovered" if (recovered or resolving) else "steady"), fails, resolving


def evidence_for(d, fails):
    ev = []
    for inc in d["incidents_opened"]:
        ev.append(f"{inc['id']} opened ({inc.get('service', 'unknown')})")
    for inc in d["incidents_resolved"]:
        hours = (parse_ts(inc["resolved_at"]) - parse_ts(inc["opened_at"])).total_seconds() / 3600
        ev.append(f"{inc['id']} resolved after {hours:.0f}h")
    for inc in d["incidents_open"]:
        if inc not in d["incidents_opened"] and inc not in d["incidents_resolved"]:
            ev.append(f"{inc['id']} still open ({inc.get('service', 'unknown')})")
    for rb in d["rollbacks"]:
        ev.append(f"rollback {rb['id']} ({rb.get('service', 'unknown')})")
    if d["burn"] is not None and d["burn"] > 1.0:
        ev.append(f"SLO burn {d['burn']:.1f}x (over 1.0)")
    if d["runs"]:
        ev.append(f"{len(fails)} of {len(d['runs'])} main-branch runs failed" if fails
                  else f"all {len(d['runs'])} main-branch runs passed")
    for r in fails[:3]:
        ev.append(f"run {r['id']} failed" + (f" ({r['service']})" if r.get("service") else ""))
    if len(fails) > 3:
        ev.append(f"{len(fails) - 3} more failed run" + ("s" if len(fails) > 4 else ""))
    flaky = sorted({t for r in d["runs"] for t in r.get("flaky_failures", [])})
    if flaky:
        ev.append(f"flaky {flaky[0]}" + (f" (+{len(flaky) - 1} more)" if len(flaky) > 1 else ""))
    if d["deploys"]:
        svc = sorted({x.get("service", "unknown") for x in d["deploys"]})
        ev.append(f"{len(d['deploys'])} deploy{'s' if len(d['deploys']) != 1 else ''} ({', '.join(svc)})")
    if not (d["deploys"] or d["rollbacks"] or d["runs"]):
        ev.append("deploy freeze: no deploys and no CI runs")
    return ev


def compose(data_dir, days=14, as_of=None):
    src, problems = load_sources(data_dir)
    manifest = src.get("manifest", {})
    days = int(manifest.get("days", days))
    end = parse_ts(as_of or manifest.get("as_of") or datetime.now(timezone.utc).isoformat())
    end_day = datetime(end.year, end.month, end.day, tzinfo=timezone.utc) + timedelta(days=1)
    start = end_day - timedelta(days=days)
    missing = [s for s in ("deployments", "ci_runs", "incidents", "slo_daily") if s not in src]
    bars, recovered = [], False
    for d in gather_days(src, start, days):
        state, fails, resolving = day_state(d, recovered)
        if resolving:
            recovered = True
        elif state == "incident":
            recovered = False
        facts = {
            "deploys": len(d["deploys"]), "runs": len(d["runs"]), "failed_runs": len(fails), "burn": d["burn"],
            "services": sorted({x.get("service", "unknown") for x in d["deploys"]}),
            "flaky": sorted({t for r in d["runs"] for t in r.get("flaky_failures", [])}),
            "opened": [{"id": i["id"], "service": i.get("service", "unknown"), "at": i["opened_at"]} for i in d["incidents_opened"]],
            "resolved": [{"id": i["id"], "service": i.get("service", "unknown"),
                          "hours": round((parse_ts(i["resolved_at"]) - parse_ts(i["opened_at"])).total_seconds() / 3600)}
                         for i in d["incidents_resolved"]],
            "still_open": [{"id": i["id"], "service": i.get("service", "unknown")} for i in d["incidents_open"]
                           if i not in d["incidents_opened"] and i not in d["incidents_resolved"]],
            "rollbacks": [{"id": r["id"], "service": r.get("service", "unknown"), "at": r["at"]} for r in d["rollbacks"]],
        }
        bars.append({"bar": d["index"] + 1, "date": d["date"], "state": state, "facts": facts,
                     "evidence": evidence_for(d, fails)})
    return {
        "title": manifest.get("title") or f"{manifest.get('subject', 'Your system')}: {days} days",
        "subject": manifest.get("subject", "unnamed system"),
        "window": {"start": start.date().isoformat(), "end": (end_day - timedelta(days=1)).date().isoformat(), "days": days},
        "bars": bars,
        "totals": {"deploys": sum(b["facts"]["deploys"] for b in bars), "runs": sum(b["facts"]["runs"] for b in bars),
                   "failed_runs": sum(b["facts"]["failed_runs"] for b in bars),
                   "incidents": len({i["id"] for b in bars for i in b["facts"]["opened"] + b["facts"]["still_open"]})},
        "static": missing,
        "sources": sorted(src),
        "source_problems": problems,
        "provenance": manifest.get("provenance", {}),
        "review": {"status": "pending_human_review", "note": "Every line of the broadcast is backed by The Record."},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="WREL's Release Hour: your release report, on the air.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("demo", "play"):
        p = sub.add_parser(name)
        p.add_argument("--out", default="radio")
        p.add_argument("--days", type=int, default=14)
        p.add_argument("--as-of", default=None)
        p.add_argument("--voice", choices=["browser", "elevenlabs"], default="browser",
                       help="browser: the page reads the script aloud. elevenlabs: render a real announcer.")
        p.add_argument("--voice-id", default=None, help="ElevenLabs voice id (for example Clyde, the vintage announcer)")
        p.add_argument("--model", default=None, help="ElevenLabs model id")
        p.add_argument("--voice-file", default=None,
                       help="A WAV of the whole script read in one take; it is split into segments at the pauses")
        p.add_argument("--theme", default=str(THEME), help="Theme music WAV for the open and close")
        if name == "play":
            p.add_argument("--data", required=True)
    args = ap.parse_args(argv)
    data = DEMO if args.cmd == "demo" else Path(args.data)
    if not data.is_dir():
        print(f"Data folder not found: {data}", file=sys.stderr)
        return 2
    score = compose(data, args.days, args.as_of)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import broadcast
    import mix
    import player
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    segs = broadcast.script(score)
    (out / "score.json").write_text(json.dumps(score, indent=2) + "\n")
    (out / "script.json").write_text(json.dumps(segs, indent=2) + "\n")
    (out / "script.md").write_text(broadcast.cue_sheet_md(score, segs))
    (out / "script.txt").write_text(broadcast.read_text(segs))
    (out / "the_record.md").write_text(player.record_md(score, segs))
    theme = mix.load_wav(args.theme) if args.theme and Path(args.theme).exists() else None
    voices = None
    if args.voice_file:
        voices = mix.split_read(mix.load_wav(args.voice_file), segs)
    elif args.voice == "elevenlabs":
        import voice
        paths = voice.render(segs, out / "voice", args.voice_id or voice.DEFAULT_VOICE,
                             args.model or voice.DEFAULT_MODEL, voice.api_key_from_env())
        voices = {k: voice.load_pcm(v) for k, v in paths.items()}
    mixed = None
    if voices:
        samples, cues = mix.build(segs, voices, theme)
        mix.write_wav(samples, out / "broadcast.wav")
        (out / "cues.json").write_text(json.dumps(cues, indent=1) + "\n")
        mixed = ((out / "broadcast.wav").read_bytes(), cues)
    theme_bytes = mix.wav_bytes(theme) if theme else None
    (out / "player.html").write_text(player.page(score, segs, mixed, theme_bytes))
    print(player.console(score))
    made = ["player.html", "broadcast.wav" if mixed else None, "script.md", "script.txt", "the_record.md"]
    print("\nWrote " + ", ".join(str(out / f) for f in made if f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
