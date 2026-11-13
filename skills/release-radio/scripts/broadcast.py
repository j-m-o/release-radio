"""The WREL broadcast script: a 1940s radio announcer reads your two weeks.

The script is written by rules from the score: every sentence states a fact that is
in the data, plus a fixed period flourish per kind of day, and nothing else.
Stretches of the same weather become one segment. No people are ever named.

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import re
from datetime import date, datetime

STATION = "W. R. E. L."


def _suffix(n):
    return "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def spoken_date(iso):
    d = date.fromisoformat(iso)
    return f"{d:%A}, {d:%B} {d.day}{_suffix(d.day)}"


def short_date(iso):
    d = date.fromisoformat(iso)
    return f"{d:%A} the {d.day}{_suffix(d.day)}"


def plural(n, word, many=None):
    return f"{n} {word if n == 1 else (many or word + 's')}"


def spoken_id(incident_id):
    """INC-07 becomes 'incident number 7' so a voice reads it naturally."""
    m = re.match(r"^[A-Za-z]+-?0*(\d+)$", incident_id)
    return f"incident number {m.group(1)}" if m else f"incident {incident_id}"


def spoken_test(name):
    words = [w for w in re.split(r"[_\-.]+", name) if w and w.lower() != "test" and len(w) > 1]
    return " ".join(words) or name


def part_of_day(iso):
    h = datetime.fromisoformat(iso.replace("Z", "+00:00")).hour
    return "that morning" if h < 12 else ("that afternoon" if h < 18 else "that evening")


def _total(run, key):
    return sum(b["facts"][key] for b in run)


def _when(run):
    a, b = run[0]["date"], run[-1]["date"]
    if len(run) == 1:
        return f"On {spoken_date(a)}"
    if len(run) == 2:
        return f"On {spoken_date(a)} and {short_date(b)}"
    return f"From {spoken_date(a)} through {short_date(b)}"


def _steady(run, subject, first):
    deploys, runs = _total(run, "deploys"), _total(run, "runs")
    opener = f"{_when(run)}, fair skies over {subject}." if first or len(run) > 1 else \
        f"{_when(run)}, the crews were back at work."
    builds = f"all {runs} builds on the main line came back clean" if runs else "there were no builds on record"
    line = f"{opener} {plural(deploys, 'deploy')} went out, and {builds}."
    if len(run) > 1:
        line += " A team in step, ladies and gentlemen."
    return line


def _failed(run):
    fails, runs = _total(run, "failed_runs"), _total(run, "runs")
    flaky = sorted({t for b in run for t in b["facts"]["flaky"]})
    line = f"{_when(run)}, the weather turned. {fails} of {runs} builds failed"
    if flaky:
        line += f", and a flaky test called {spoken_test(flaky[0])} was heard stuttering in the wings"
    line += ". Rough going on the main line."
    return line


def _freeze(run):
    if len(run) == 1:
        return f"{_when(run)}, not one deploy and not one build. A deploy freeze. All quiet on the main line."
    return f"{_when(run)}, a deploy freeze. {plural(len(run), 'day')} without a deploy or a build. All quiet on the main line."


def _incident(run):
    f0 = run[0]["facts"]
    parts = []
    if f0["opened"]:
        inc = f0["opened"][0]
        t = datetime.fromisoformat(inc["at"].replace("Z", "+00:00"))
        parts.append(f"We interrupt this program with an urgent bulletin. On {spoken_date(run[0]['date'])}, "
                     f"at {t:%H:%M} Greenwich time, {spoken_id(inc['id'])} struck the {inc['service']} service.")
    elif f0["still_open"]:
        inc = f0["still_open"][0]
        parts.append(f"{_when(run)}, {spoken_id(inc['id'])} was still raging over the {inc['service']} service.")
    else:
        parts.append(f"{_when(run)}, trouble on the line.")
    if f0["rollbacks"]:
        rb = f0["rollbacks"][0]
        parts.append(f"A rollback of {rb['service']} was ordered {part_of_day(rb['at'])}.")
    if f0["burn"] is not None and f0["burn"] > 1.0:
        parts.append(f"The error budget was burning at {f0['burn']:.1f} times the safe rate.")
    if f0["opened"]:
        parts.append("Stay tuned to this station for further developments.")
    if len(run) > 1:
        parts.append(f"The storm held through {short_date(run[-1]['date'])}.")
    return " ".join(parts)


def _recovered(run, subject):
    f0 = run[0]["facts"]
    if not f0["resolved"]:
        return _steady(run, subject, False)
    inc = f0["resolved"][0]
    line = (f"And then, on {spoken_date(run[0]['date'])}, after {inc['hours']} long hours, {spoken_id(inc['id'])} "
            f"was resolved. The all clear has sounded.")
    rest = run[1:]
    if rest:
        deploys, runs = _total(rest, "deploys"), _total(rest, "runs")
        line += (f" In the {plural(len(rest), 'day')} that followed, {plural(deploys, 'deploy')} went out"
                 + (f", and all {runs} builds came back clean." if runs else "."))
    return line


def runs_of(bars):
    out = []
    for b in bars:
        if out and out[-1][-1]["state"] == b["state"]:
            out[-1].append(b)
        else:
            out.append([b])
    return out


def script(score):
    subject, bars = score["subject"], score["bars"]
    segs = [{"id": "sign-on", "kind": "sign-on", "bars": None, "text": (
        f"Good evening, ladies and gentlemen, and welcome to the Release Hour, on station {STATION} "
        f"Tonight, the news from {subject}: {plural(len(bars), 'day')} on the main line, "
        f"and every word straight from the record. We call it: {score['title']}.")}]
    first = True
    for run in runs_of(bars):
        state = run[0]["state"]
        if state == "steady":
            text = _steady(run, subject, first)
        elif state == "failed":
            text = _failed(run)
        elif state == "freeze":
            text = _freeze(run)
        elif state == "incident":
            text = _incident(run)
        else:
            text = _recovered(run, subject)
        first = False
        segs.append({"id": f"bars-{run[0]['bar']}-{run[-1]['bar']}", "kind": state,
                     "bars": [run[0]["bar"], run[-1]["bar"]], "text": text})
    deploys, builds, incidents = score["totals"]["deploys"], score["totals"]["runs"], score["totals"]["incidents"]
    static = ""
    if score["static"]:
        static = f" A note for the engineers: tonight's signal carried static, because the station had no {', '.join(score['static'])}."
    segs.append({"id": "sign-off", "kind": "sign-off", "bars": None, "text": (
        f"And that was {score['title']}. {plural(deploys, 'deploy')}, {plural(builds, 'build')} and "
        f"{plural(incidents, 'incident')}, and every word of it straight from the record.{static} "
        f"This is {STATION} wishing you green builds and quiet pagers. Good night.")})
    return segs


def cue_sheet_md(score, segs):
    """A script for reading it live, with the theme cues."""
    lines = [f"# WREL: {score['title']}", "",
             "A cue sheet for reading the broadcast live. Play the theme, read each block, play the theme out.", "",
             "> THEME: let it play a few seconds, then start reading over it as it fades", ""]
    for s in segs:
        if s["kind"] == "incident":
            lines += ["> CHIME: the station chime before the bulletin", ""]
        if s["kind"] == "sign-off":
            lines += ["> THEME: bring it back in quietly under the sign-off", ""]
        days = ""
        if s["bars"]:
            a, b = s["bars"]
            days = f" (day {a})" if a == b else f" (days {a} to {b})"
        lines += [f"## {s['id'].replace('-', ' ').capitalize()}{days}", "", s["text"], ""]
    lines += ["> THEME: up full to play the show out", ""]
    return "\n".join(lines)


def read_text(segs):
    """The whole script for one recorded read: one paragraph per segment, with a clear pause between."""
    return "\n\n".join(s["text"] for s in segs) + "\n"
