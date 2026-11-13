"""Player page, The Record and console output for Release Radio.

The player is one offline HTML file. With a mixed broadcast it plays that, with
captions. Without one, it plays the theme and the browser's own voice reads the
script. Either way the timeline lights up the days being read, and a speaker can
read it live from the script cards with the theme and chime buttons.

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import base64
import html
import json
from datetime import date

NAVY, SOFT, SKY, PAPER = "#1B2F5E", "#3A4E7A", "#DCEBF8", "#F4F8FC"
GOLD, PURPLE, CORAL, MINT = "#F6B94B", "#8E7BC9", "#F4846B", "#7CCBB0"
STATE_COLOR = {"steady": SKY, "failed": CORAL, "incident": PURPLE, "recovered": MINT, "freeze": "transparent"}
STATE_LABEL = {"steady": "fair skies", "failed": "rough going", "incident": "incident", "recovered": "all clear",
               "freeze": "freeze"}


def _height(bar):
    f = bar["facts"]
    if bar["state"] == "freeze":
        return 24
    return min(120, 40 + 8 * f["deploys"] + 3 * f["runs"] + 12 * (len(f["opened"]) + len(f["still_open"])))


def _label(seg):
    if not seg["bars"]:
        return seg["id"].replace("-", " ").capitalize()
    a, b = seg["bars"]
    return f"Day {a}" if a == b else f"Days {a} to {b}"


def record_md(score, segs):
    t = score["totals"]
    lines = [f"# The Record: {score['title']}", "",
             f"WREL Release Radio | {score['subject']} | {score['window']['start']} to {score['window']['end']}", "",
             f"{t['deploys']} deploys | {t['runs']} main-branch builds ({t['failed_runs']} failed) | {t['incidents']} incident"
             + ("s" if t["incidents"] != 1 else ""), "",
             "Every line the announcer reads comes from rules over this evidence. Same data, same broadcast.", ""]
    if score["static"]:
        lines += [f"Static on the line: no usable {', '.join(score['static'])}. The broadcast says so instead of guessing.", ""]
    for name, probs in score["source_problems"].items():
        lines.append(f"Set aside: {name}.json ({'; '.join(probs)})")
    if score["source_problems"]:
        lines.append("")
    by_bar = {b["bar"]: b for b in score["bars"]}
    for s in segs:
        if not s["bars"]:
            continue
        lines += [f"## {_label(s)}", "", f"> {s['text']}", "", "| Day | Date | Conditions | Evidence |", "|---|---|---|---|"]
        for n in range(s["bars"][0], s["bars"][1] + 1):
            b = by_bar[n]
            lines.append(f"| {n} | {b['date']} | {STATE_LABEL[b['state']]} | {'; '.join(b['evidence'])} |")
        lines.append("")
    lines += ["Advisory only. A person decides what any of this means.", ""]
    return "\n".join(lines)


def console(score):
    t = score["totals"]
    out = [f"WREL RELEASE RADIO  {score['title']}",
           f"{len(score['bars'])} days  {t['deploys']} deploys  {t['runs']} builds  {t['incidents']} incidents"]
    for b in score["bars"]:
        out.append(f"  {b['bar']:>2} {b['date']} {STATE_LABEL[b['state']]:<11} {'; '.join(b['evidence'][:2])}")
    if score["static"]:
        out.append(f"  static: missing {', '.join(score['static'])}")
    return "\n".join(out)


RADIO = """<svg viewBox="0 0 420 400" class="radio" aria-hidden="true">
<path d="M40 380 L40 190 C40 70 120 20 210 20 C300 20 380 70 380 190 L380 380 Z" fill="{u}" stroke="{n}" stroke-width="6" stroke-linejoin="round"/>
<path d="M66 360 L66 196 C66 96 132 48 210 48 C288 48 354 96 354 196 L354 360 Z" fill="none" stroke="{n}" stroke-width="3" opacity=".55"/>
<g fill="{n}">
<path d="M104 250 L104 170 C104 130 126 104 150 104 C174 104 196 130 196 170 L196 250 Z"/>
<path d="M224 250 L224 170 C224 130 246 104 270 104 C294 104 316 130 316 170 L316 250 Z"/>
</g>
<g stroke="{u}" stroke-width="3" opacity=".7">
<line x1="150" y1="104" x2="150" y2="250"/><line x1="127" y1="118" x2="127" y2="250"/><line x1="173" y1="118" x2="173" y2="250"/>
<line x1="270" y1="104" x2="270" y2="250"/><line x1="247" y1="118" x2="247" y2="250"/><line x1="293" y1="118" x2="293" y2="250"/>
</g>
<rect x="150" y="62" width="120" height="30" rx="8" fill="{p}" stroke="{n}" stroke-width="3"/>
<text x="210" y="84" text-anchor="middle" fill="{n}" font-family="Lexend, system-ui, sans-serif" font-size="18" font-weight="700" letter-spacing="3">WREL</text>
<circle cx="210" cy="305" r="44" fill="{p}" stroke="{n}" stroke-width="5"/>
<circle cx="210" cy="305" r="34" class="dial" fill="{g}" stroke="{n}" stroke-width="2"/>
<g stroke="{n}" stroke-width="2"><line x1="210" y1="275" x2="210" y2="282"/><line x1="181" y1="305" x2="188" y2="305"/>
<line x1="232" y1="305" x2="239" y2="305"/><line x1="189" y1="284" x2="194" y2="289"/><line x1="231" y1="284" x2="226" y2="289"/></g>
<line x1="210" y1="305" x2="228" y2="283" stroke="{n}" stroke-width="3" stroke-linecap="round" class="needle"/>
<circle cx="110" cy="318" r="22" fill="{n}"/><circle cx="110" cy="318" r="9" fill="{g}"/>
<circle cx="310" cy="318" r="22" fill="{n}"/><circle cx="310" cy="318" r="9" fill="{g}"/>
<rect x="30" y="372" width="360" height="16" rx="6" fill="{n}"/>
</svg>"""


def page(score, segs, broadcast=None, theme_wav=None):
    """broadcast: (wav bytes, cues) when a voiced broadcast was mixed. theme_wav: the theme, for the
    browser-voice fallback and the live-read buttons."""
    esc = html.escape
    t = score["totals"]
    radio = RADIO.format(n=NAVY, p=PAPER, g=GOLD, u=PURPLE)
    days = []
    for b in score["bars"]:
        cls = "day freeze" if b["state"] == "freeze" else "day"
        tip = f"Day {b['bar']}, {b['date']}: {STATE_LABEL[b['state']]}. " + "; ".join(b["evidence"])
        days.append(f'<button class="{cls}" data-day="{b["bar"]}" style="height:{_height(b)}px;'
                    f'background:{STATE_COLOR[b["state"]]}" title="{esc(tip)}" aria-label="{esc(tip)}"></button>')
    cards = "".join(f'<li class="cue" data-seg="{esc(s["id"])}"><span class="lbl">{esc(_label(s))}</span>'
                    f'<p>{esc(s["text"])}</p></li>' for s in segs)
    by_bar = {b["bar"]: b for b in score["bars"]}
    record = []
    for s in segs:
        if not s["bars"]:
            continue
        rows = []
        for n in range(s["bars"][0], s["bars"][1] + 1):
            b = by_bar[n]
            d = date.fromisoformat(b["date"])
            items = "".join(f"<li>{esc(e)}</li>" for e in b["evidence"])
            rows.append(f'<div class="rday" data-day="{n}"><span class="dl"><i style="background:{STATE_COLOR[b["state"]]}"></i>'
                        f'Day {n} &middot; {d:%a %b} {d.day} &middot; {STATE_LABEL[b["state"]]}</span><ul>{items}</ul></div>')
        record.append(f'<section class="rseg" data-seg="{esc(s["id"])}"><h3>{esc(_label(s))}</h3>{"".join(rows)}</section>')
    static = ""
    if score["static"]:
        static = (f'<p class="static">Static on the line: no usable {esc(", ".join(score["static"]))}. '
                  'The broadcast says so instead of guessing.</p>')
    bc_tag = th_tag = ""
    if broadcast:
        bc_tag = f'<audio id="b" src="data:audio/wav;base64,{base64.b64encode(broadcast[0]).decode("ascii")}" preload="auto"></audio>'
    if theme_wav:
        th_tag = f'<audio id="t" src="data:audio/wav;base64,{base64.b64encode(theme_wav).decode("ascii")}" preload="auto"></audio>'
    voice_note = ("Announcer voice by ElevenLabs." if broadcast else
                  "The announcer is your browser's own voice until a recorded read is mixed in.")
    data = json.dumps({"segs": [{"id": s["id"], "text": s["text"], "bars": s["bars"], "kind": s["kind"]} for s in segs],
                       "cues": broadcast[1] if broadcast else None})
    return TEMPLATE.format(
        title=esc(score["title"]), subject=esc(score["subject"]), start=esc(score["window"]["start"]),
        end=esc(score["window"]["end"]), ndays=len(score["bars"]), deploys=t["deploys"], runs=t["runs"],
        incidents=t["incidents"], inc_s="" if t["incidents"] == 1 else "s", radio=radio, days="".join(days),
        cards=cards, record="".join(record), static=static, voice_note=voice_note, bc_tag=bc_tag, th_tag=th_tag,
        data=data, NAVY=NAVY, SOFT=SOFT, SKY=SKY, PAPER=PAPER, GOLD=GOLD, PURPLE=PURPLE, CORAL=CORAL, MINT=MINT)


TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WREL Release Radio: {title}</title>
<style>
:root {{ --navy:{NAVY}; --soft:{SOFT}; --sky:{SKY}; --paper:{PAPER}; --gold:{GOLD}; --purple:{PURPLE}; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:#A9CBEB; color:var(--navy); font:17px/1.5 "Atkinson Hyperlegible", system-ui, sans-serif; }}
main {{ max-width:1180px; margin:32px auto; padding:36px; background:var(--paper); border:4px solid var(--navy); border-radius:28px; }}
h1, h2, h3 {{ font-family:Lexend, system-ui, sans-serif; margin:0; }}
h1 {{ font-size:44px; letter-spacing:.04em; }}
h1 span {{ color:var(--purple); }}
.tag {{ color:var(--soft); margin:2px 0 24px; }}
.top {{ display:grid; grid-template-columns:340px 1fr; gap:40px; align-items:center; }}
.radio {{ width:100%; height:auto; }}
.playing .dial {{ animation:glow 1.6s ease-in-out infinite; }}
@keyframes glow {{ 0%,100% {{ fill:{GOLD}; }} 50% {{ fill:#FFE1A1; }} }}
.now {{ font-size:14px; text-transform:uppercase; letter-spacing:.12em; color:var(--purple); font-weight:700; }}
h2.track {{ font-size:32px; margin:4px 0 12px; }}
.chips span {{ display:inline-block; padding:4px 14px; margin:0 8px 8px 0; border:2px solid var(--navy); border-radius:999px; background:#fff; font-weight:700; }}
.controls {{ display:flex; gap:14px; align-items:center; margin-top:14px; flex-wrap:wrap; }}
#play {{ width:64px; height:64px; border-radius:50%; border:4px solid var(--navy); background:var(--gold); color:var(--navy); font-size:24px; cursor:pointer; }}
.small {{ border:2px solid var(--navy); background:#fff; color:var(--navy); border-radius:999px; padding:6px 16px; font:inherit; font-weight:700; cursor:pointer; }}
button:focus-visible {{ outline:3px solid var(--purple); outline-offset:3px; }}
.progress {{ flex:1; min-width:160px; height:14px; background:var(--sky); border:2px solid var(--navy); border-radius:999px; overflow:hidden; }}
.progress i {{ display:block; height:100%; width:0; background:var(--gold); }}
#clock {{ font-variant-numeric:tabular-nums; min-width:60px; }}
.onair {{ margin-top:18px; background:var(--navy); color:var(--paper); border-radius:16px; padding:14px 18px; min-height:110px; }}
.onair .lbl {{ color:var(--gold); font-weight:700; font-size:13px; letter-spacing:.14em; text-transform:uppercase; }}
.onair p {{ margin:4px 0 0; font-size:18px; }}
.timeline {{ margin:32px 0 6px; display:flex; align-items:flex-end; gap:10px; height:130px; border-bottom:3px solid var(--navy); padding:0 4px; }}
.day {{ flex:1; border:3px solid var(--navy); border-bottom:none; border-radius:10px 10px 0 0; cursor:pointer; padding:0; transition:transform .2s; }}
.day.freeze {{ border-style:dashed; }}
.day.on {{ background:var(--gold) !important; transform:translateY(-6px); }}
.legend {{ display:flex; flex-wrap:wrap; gap:18px; font-size:15px; color:var(--soft); margin-bottom:30px; }}
.legend i {{ display:inline-block; width:14px; height:14px; border:2px solid var(--navy); border-radius:4px; margin-right:6px; vertical-align:-2px; }}
.sechead {{ display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; margin:0 0 6px; }}
h2.sec {{ font-size:24px; }}
.hint {{ color:var(--soft); margin:0 0 14px; }}
.script {{ list-style:none; padding:0; margin:0 0 30px; display:grid; grid-template-columns:repeat(auto-fill,minmax(330px,1fr)); gap:14px; }}
.cue {{ background:#fff; border:3px solid var(--navy); border-radius:16px; padding:14px 16px; }}
.cue.on {{ border-color:var(--gold); box-shadow:0 0 0 3px var(--gold); }}
.cue .lbl {{ font-size:13px; color:var(--purple); text-transform:uppercase; letter-spacing:.1em; font-weight:700; }}
.cue p {{ margin:6px 0 0; }}
.record {{ background:var(--navy); color:var(--paper); border-radius:20px; padding:28px 32px; }}
.record > h2 {{ color:var(--gold); font-size:24px; margin-bottom:4px; }}
.record > p {{ margin:0 0 16px; color:var(--sky); }}
.rseg {{ border-top:2px solid var(--soft); padding:14px 0 6px; }}
.rseg h3 {{ font-size:15px; color:var(--gold); text-transform:uppercase; letter-spacing:.1em; margin-bottom:8px; }}
.rseg.on h3 {{ color:#FFE1A1; }}
.rday {{ display:grid; grid-template-columns:260px 1fr; gap:12px; padding:4px 8px; border-radius:8px; }}
.rday.on {{ background:var(--soft); }}
.rday .dl i {{ display:inline-block; width:12px; height:12px; border:2px solid var(--paper); border-radius:3px; margin-right:8px; vertical-align:-1px; }}
.rday ul {{ margin:0; padding-left:18px; }}
.static {{ background:#fff; border:2px dashed var(--purple); border-radius:12px; padding:10px 14px; }}
.foot {{ margin-top:22px; font-size:14px; color:var(--soft); }}
@media (max-width:860px) {{ .top {{ grid-template-columns:1fr; }} .radio {{ max-width:300px; }} main {{ margin:0; border-radius:0; }} .rday {{ grid-template-columns:1fr; }} }}
@media (prefers-reduced-motion:reduce) {{ .playing .dial {{ animation:none; }} .day {{ transition:none; }} .day.on {{ transform:none; }} }}
</style></head>
<body><main>
<h1>WREL <span>RELEASE RADIO</span></h1>
<p class="tag">The Release Hour. Every word straight from the record.</p>
<section class="top">
<div>{radio}</div>
<div>
<div class="now">Tonight on the Release Hour</div>
<h2 class="track">{title}</h2>
<div class="chips"><span>{ndays} days</span><span>{deploys} deploys</span><span>{runs} builds</span><span>{incidents} incident{inc_s}</span></div>
<div class="controls"><button id="play" aria-label="Play the broadcast">&#9654;</button>
<div class="progress"><i id="prog"></i></div><span id="clock">0:00</span></div>
<div class="onair" aria-live="polite"><div class="lbl" id="onlbl">WREL</div><p id="caption">Press play for tonight's broadcast.</p></div>
<p>{subject} &middot; {start} to {end}</p>
{static}
</div>
</section>
<div class="timeline" role="group" aria-label="One bar per day">{days}</div>
<div class="legend"><span><i style="background:{SKY}"></i>fair skies</span><span><i style="background:{CORAL}"></i>rough going</span>
<span><i style="background:{PURPLE}"></i>incident</span><span><i style="background:{MINT}"></i>all clear</span>
<span><i style="border-style:dashed"></i>freeze</span><span><i style="background:{GOLD}"></i>on the air now</span></div>
<div class="sechead"><h2 class="sec">Tonight's script</h2>
<button class="small" id="themebtn">&#9835; Play the theme</button><button class="small" id="chimebtn">&#128276; Chime</button></div>
<p class="hint">Reading it live? Start the theme, read over it as it fades, ring the chime before the bulletin and bring the theme back for the sign-off.</p>
<ol class="script">{cards}</ol>
<section class="record"><h2>The Record</h2><p>The evidence behind every line, day by day.</p>{record}</section>
<p class="foot">Every line is written by rules from the data in The Record. Theme music generated with ElevenLabs. {voice_note}
Advisory only: a person decides what it means. Release Radio by Jessica Mosley.</p>
</main>
{bc_tag}
{th_tag}
<script>
const D = {data};
const bc = document.getElementById('b'), th = document.getElementById('t');
const btn = document.getElementById('play'), cap = document.getElementById('caption'), lbl = document.getElementById('onlbl');
const days = [...document.querySelectorAll('.day')], rdays = [...document.querySelectorAll('.rday')];
const cards = [...document.querySelectorAll('.cue')], rsegs = [...document.querySelectorAll('.rseg')];
const segById = Object.fromEntries(D.segs.map(s => [s.id, s]));
const fmt = s => Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
const sleep = ms => new Promise(r => setTimeout(r, ms));
let run = 0;
function mark(id) {{
  const s = id ? segById[id] : null, a = s && s.bars ? s.bars[0] : 0, z = s && s.bars ? s.bars[1] : -1;
  days.forEach(d => d.classList.toggle('on', +d.dataset.day >= a && +d.dataset.day <= z));
  rdays.forEach(d => d.classList.toggle('on', +d.dataset.day >= a && +d.dataset.day <= z));
  cards.forEach(c => c.classList.toggle('on', c.dataset.seg === id));
  rsegs.forEach(c => c.classList.toggle('on', c.dataset.seg === id));
}}
function say(l, t) {{ lbl.textContent = l; cap.textContent = t; }}
function onAir(on) {{
  document.body.classList.toggle('playing', on);
  btn.innerHTML = on ? '&#10074;&#10074;' : '&#9654;';
  btn.setAttribute('aria-label', on ? 'Stop' : 'Play the broadcast');
}}
function tick(a) {{
  document.getElementById('prog').style.width = (100 * a.currentTime / (a.duration || 1)) + '%';
  document.getElementById('clock').textContent = fmt(a.currentTime);
}}
function stop() {{
  run++;
  if (window.speechSynthesis) speechSynthesis.cancel();
  if (bc) bc.pause(); if (th) th.pause();
  onAir(false); mark(null);
}}
let ac = null;
function chime() {{
  ac = ac || new (window.AudioContext || window.webkitAudioContext)();
  [523.25, 659.25, 783.99].forEach((f, k) => {{
    const o = ac.createOscillator(), g = ac.createGain(), t0 = ac.currentTime + k * 0.42;
    o.frequency.value = f; o.connect(g); g.connect(ac.destination);
    g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(0.25, t0 + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + 1.3); o.start(t0); o.stop(t0 + 1.4);
  }});
  return sleep(1900);
}}
function fade(a, to, ms) {{
  const from = a.volume, t0 = performance.now();
  return new Promise(res => (function step(now) {{
    const k = Math.min(1, (now - t0) / ms); a.volume = from + (to - from) * k;
    k < 1 ? requestAnimationFrame(step) : res();
  }})(performance.now()));
}}
function pickVoice() {{
  const vs = window.speechSynthesis ? speechSynthesis.getVoices() : [];
  for (const n of ['Daniel', 'Google UK English Male', 'Arthur', 'Fred', 'Ralph', 'Microsoft George', 'Alex'])
    {{ const v = vs.find(v => v.name.includes(n)); if (v) return v; }}
  return vs.find(v => v.lang && v.lang.startsWith('en')) || null;
}}
function speak(text) {{
  return new Promise(res => {{
    if (!window.speechSynthesis) {{ setTimeout(res, 2500); return; }}
    const u = new SpeechSynthesisUtterance(text); u.rate = 0.92; u.pitch = 0.8;
    const v = pickVoice(); if (v) u.voice = v; u.onend = res; u.onerror = res; speechSynthesis.speak(u);
  }});
}}
async function browserBroadcast() {{
  const token = ++run; onAir(true);
  const live = () => token === run;
  if (th) {{ th.currentTime = 0; th.volume = 0.8; th.play(); say('WREL', 'The theme.'); await sleep(6200); if (!live()) return; fade(th, 0.12, 800); }}
  for (const [i, s] of D.segs.entries()) {{
    if (!live()) return;
    if (s.kind === 'incident') {{ say('Bulletin', 'We interrupt this program.'); await chime(); if (!live()) return; }}
    if (s.kind === 'sign-off' && th) {{ th.currentTime = 0; th.volume = 0; th.play(); fade(th, 0.12, 1200); }}
    mark(s.id); say('On the air', s.text);
    await speak(s.text);
    if (i === 0 && th) {{ await fade(th, 0, 1200); th.pause(); }}
    await sleep(400);
  }}
  if (th && live()) {{ say('WREL', 'Good night.'); await fade(th, 0.8, 900); await sleep(Math.max(0, (th.duration - th.currentTime - 2.5) * 1000)); await fade(th, 0, 2400); th.pause(); }}
  if (live()) {{ onAir(false); mark(null); say('Off the air', 'Good night.'); }}
}}
btn.onclick = () => {{
  if (document.body.classList.contains('playing')) return stop();
  if (bc) {{ run++; bc.currentTime = 0; bc.play(); onAir(true); }} else browserBroadcast();
}};
if (bc) {{
  bc.ontimeupdate = () => {{
    tick(bc);
    const c = D.cues.find(c => bc.currentTime >= c.t0 && bc.currentTime < c.t1);
    if (!c) return;
    if (c.kind === 'voice') {{ mark(c.segment); say('On the air', segById[c.segment].text); }}
    else if (c.kind === 'chime') {{ mark(null); say('Bulletin', 'We interrupt this program.'); }}
    else if (c.kind === 'theme') {{ mark(null); say('WREL', bc.currentTime < 30 ? 'The Release Hour.' : 'Good night.'); }}
  }};
  bc.onended = () => {{ onAir(false); mark(null); say('Off the air', 'Good night.'); }};
}} else if (th) {{
  th.ontimeupdate = () => tick(th);
}}
document.getElementById('themebtn').onclick = () => {{
  if (!th) return;
  if (!th.paused) return fade(th, 0, 1500).then(() => th.pause());
  stop(); th.currentTime = 0; th.volume = 0.8; th.play();
}};
document.getElementById('chimebtn').onclick = () => chime();
days.forEach(d => d.onclick = () => {{
  const n = +d.dataset.day, s = D.segs.find(s => s.bars && n >= s.bars[0] && n <= s.bars[1]);
  if (s) {{ mark(s.id); say('Day ' + n, d.title); }}
}});
if (window.speechSynthesis) speechSynthesis.getVoices();
</script>
</body></html>
"""
