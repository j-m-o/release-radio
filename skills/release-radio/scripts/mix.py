"""Mixes the WREL broadcast. The theme opens and fades under the announcer's sign-on,
the announcer reads each segment on an old valve radio, a station chime sounds before
an urgent bulletin, and the theme comes back under the sign-off to play the show out.
Light crackle on the line throughout. Standard library only. Deterministic.

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import io
import math
import random
import struct
import wave

RATE = 22050
THEME_GAIN = 0.8
DUCK = 0.14          # theme level under the announcer
INTRO_SECONDS = 6.5  # theme alone before the announcer comes in
OUTRO_UNDER = 7.0    # seconds of theme under the end of the sign off


# ---------------------------------------------------------------- audio in and out

def load_wav(path):
    """Any 8, 16 or 24-bit PCM WAV, mono or stereo, any rate: returns mono floats at 22.05 kHz."""
    with wave.open(str(path)) as w:
        ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width == 2:
        vals = struct.unpack(f"<{n * ch}h", raw)
        scale = 32768.0
    elif width == 1:
        vals = [b - 128 for b in raw]
        scale = 128.0
    elif width == 3:
        vals = [int.from_bytes(raw[i:i + 3], "little", signed=True) for i in range(0, len(raw), 3)]
        scale = 8388608.0
    else:
        raise ValueError(f"{path}: unsupported sample width {width}")
    mono = [sum(vals[i:i + ch]) / (ch * scale) for i in range(0, len(vals), ch)]
    if rate == RATE:
        return mono
    step, out, pos = rate / RATE, [], 0.0
    while pos < len(mono) - 1:
        i = int(pos)
        frac = pos - i
        out.append(mono[i] * (1 - frac) + mono[i + 1] * frac)
        pos += step
    return out


def _pcm(samples):
    return b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples)


def write_wav(samples, path):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(_pcm(samples))


def wav_bytes(samples):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(_pcm(samples))
    return buf.getvalue()


# ---------------------------------------------------------------- one read, split into segments

def _frames(x, ms=20):
    step = int(RATE * ms / 1000)
    return step, [math.sqrt(sum(v * v for v in x[i:i + step]) / max(1, len(x[i:i + step]))) for i in range(0, len(x), step)]


def trim(x, floor=0.01):
    loud = [i for i, v in enumerate(x) if abs(v) > floor]
    if not loud:
        return x
    return x[max(0, loud[0] - 400):loud[-1] + 2000]


def _pauses(x):
    step, rms = _frames(x)
    voiced = sorted(v for v in rms if v > 0.005)
    floor = max(0.004, 0.12 * voiced[len(voiced) // 2]) if voiced else 0.004
    gaps, i = [], 0
    while i < len(rms):
        if rms[i] < floor:
            j = i
            while j < len(rms) and rms[j] < floor:
                j += 1
            if i > 0 and j < len(rms) and (j - i) * step >= 0.2 * RATE:
                gaps.append(((i + j) // 2 * step, (j - i) * step / RATE))
            i = j
        else:
            i += 1
    return gaps


def split_read(x, segs):
    """Split one take of the whole script into its segments.

    An announcer's pauses between paragraphs are not always longer than his
    dramatic pauses inside one, so this picks the set of pauses that best fits
    each paragraph's expected length from its word count, preferring longer
    pauses, by dynamic programming. Each piece is then checked against its word
    count, so a bad split fails loudly instead of putting the wrong words under
    the wrong caption."""
    gaps = _pauses(x)
    need = len(segs) - 1
    if len(gaps) < need:
        raise ValueError(f"found {len(gaps)} pauses, need {need}: record the read with a clear pause between paragraphs")
    words = [len(s["text"].split()) for s in segs]
    per_word = len(x) / sum(words)
    expect = [w * per_word for w in words]
    pos = [0] + [g[0] for g in gaps] + [len(x)]
    length = [0.0] + [g[1] for g in gaps] + [0.0]
    end = len(pos) - 1

    def cost(a, b, k):
        d = max(1, pos[b] - pos[a])
        return 4.0 * math.log(d / expect[k]) ** 2 - length[b]

    inf = float("inf")
    best = [[inf] * len(pos) for _ in range(len(segs) + 1)]
    back = [[0] * len(pos) for _ in range(len(segs) + 1)]
    best[0][0] = 0.0
    for k in range(len(segs)):
        for b in range(1, len(pos)):
            if (k == len(segs) - 1) != (b == end):
                continue
            for a in range(b):
                if best[k][a] < inf:
                    c = best[k][a] + cost(a, b, k)
                    if c < best[k + 1][b]:
                        best[k + 1][b], back[k + 1][b] = c, a
    cuts, b = [], end
    for k in range(len(segs), 0, -1):
        cuts.append(pos[b])
        b = back[k][b]
    bounds = [0] + sorted(cuts)
    pieces = [trim(x[bounds[k]:bounds[k + 1]]) for k in range(len(segs))]
    rate = sum(len(p) for p in pieces) / sum(words)
    for s, p, w in zip(segs, pieces, words):
        ratio = len(p) / (w * rate)
        if not 0.6 < ratio < 1.6:
            raise ValueError(f"segment {s['id']} came out {ratio:.1f}x its expected length: check the read for extra pauses")
    return {s["id"]: p for s, p in zip(segs, pieces)}


# ---------------------------------------------------------------- the radio sound

def _biquad(x, b0, b1, b2, a1, a2):
    y, x1, x2, y1, y2 = [], 0.0, 0.0, 0.0, 0.0
    for v in x:
        o = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, o
        y.append(o)
    return y


def _coeffs(kind, f, q=0.707):
    w = 2 * math.pi * f / RATE
    alpha, c = math.sin(w) / (2 * q), math.cos(w)
    if kind == "lp":
        b0, b1, b2 = (1 - c) / 2, 1 - c, (1 - c) / 2
    else:
        b0, b1, b2 = (1 + c) / 2, -(1 + c), (1 + c) / 2
    a0 = 1 + alpha
    return b0 / a0, b1 / a0, b2 / a0, -2 * c / a0, (1 - alpha) / a0


def filt(x, kind, f):
    return _biquad(x, *_coeffs(kind, f))


def radio_voice(x):
    """A narrow valve-radio band, a little saturation, normalised."""
    y = filt(filt(filt(x, "hp", 300), "hp", 300), "lp", 3200)
    y = filt(y, "lp", 3600)
    y = [math.tanh(1.8 * v) for v in y]
    peak = max(1e-9, max(abs(v) for v in y))
    return [0.8 * v / peak for v in y]


def crackle(n, rng, hiss=0.004, pops_per_sec=2.0):
    out = [(rng.random() * 2 - 1) * hiss for _ in range(n)]
    for _ in range(int(n / RATE * pops_per_sec)):
        i = rng.randrange(n)
        amp = rng.uniform(0.02, 0.08) * (1 if rng.random() < 0.5 else -1)
        for k in range(min(40, n - i)):
            out[i + k] += amp * math.exp(-k / 6)
    return out


def chime():
    """Three ascending bell tones (C, E, G): the station's bulletin chime."""
    out = [0.0] * int(RATE * 2.0)
    for k, f in enumerate((523.25, 659.25, 783.99)):
        start = int(k * 0.42 * RATE)
        for i in range(int(1.3 * RATE)):
            if start + i >= len(out):
                break
            t = i / RATE
            env = math.exp(-t * 3.4) * min(1.0, i / 60)
            out[start + i] += 0.22 * env * (math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * 2.76 * f * t))
    return out


def silence(seconds):
    return [0.0] * int(seconds * RATE)


def _ramp(i, a, b, ga, gb):
    """Gain at sample i on a straight line from (a, ga) to (b, gb), clamped."""
    if i <= a:
        return ga
    if i >= b:
        return gb
    return ga + (gb - ga) * (i - a) / (b - a)


# ---------------------------------------------------------------- the broadcast

def build(segs, voices, theme=None):
    """segs: the script. voices: {segment id: samples}. theme: samples or None.
    Returns (samples, cues); cues say what is on the air when, for captions."""
    rng = random.Random(1947)
    out, cues = [], []

    def mark(kind, seg, t0, t1):
        cues.append({"t0": round(t0 / RATE, 3), "t1": round(t1 / RATE, 3), "kind": kind, "segment": seg})

    def place(chunk, at):
        if at + len(chunk) > len(out):
            out.extend([0.0] * (at + len(chunk) - len(out)))
        for i, v in enumerate(chunk):
            out[at + i] += v

    first, last, middle = segs[0], segs[-1], segs[1:-1]
    v0 = radio_voice(voices[first["id"]])
    if theme:
        intro = int(INTRO_SECONDS * RATE)
        start_v = intro - int(0.3 * RATE)
        duck_end = start_v + int(0.8 * RATE)
        fade_from = start_v + len(v0)
        stop = min(len(theme), fade_from + int(1.5 * RATE))
        bed = [theme[i] * THEME_GAIN * _ramp(i, start_v - int(0.5 * RATE), duck_end, 1.0, DUCK)
               * _ramp(i, fade_from, stop, 1.0, 0.0) for i in range(stop)]
        place(bed, 0)
        mark("theme", None, 0, start_v)
    else:
        place(chime(), 0)
        mark("chime", None, 0, len(out))
        start_v = len(out) + int(0.3 * RATE)
    place(v0, start_v)
    mark("voice", first["id"], start_v, start_v + len(v0))
    cursor = start_v + len(v0)

    for seg in middle:
        cursor += int(0.7 * RATE)
        if seg["kind"] == "incident":
            c = chime()
            place(c, cursor)
            mark("chime", seg["id"], cursor, cursor + len(c))
            cursor += len(c) + int(0.2 * RATE)
        v = radio_voice(voices[seg["id"]])
        place(v, cursor)
        mark("voice", seg["id"], cursor, cursor + len(v))
        cursor += len(v)

    cursor += int(0.7 * RATE)
    vl = radio_voice(voices[last["id"]])
    place(vl, cursor)
    mark("voice", last["id"], cursor, cursor + len(vl))
    end_v = cursor + len(vl)
    if theme:
        enter = max(cursor, end_v - int(OUTRO_UNDER * RATE))  # the theme sneaks in under the last lines
        rise_a, rise_b = end_v + int(0.2 * RATE), end_v + int(1.0 * RATE)
        n = len(theme)
        fade_a = n - int(2.5 * RATE)
        bed = [theme[i] * THEME_GAIN * _ramp(i, 0, int(1.2 * RATE), 0.0, DUCK)
               * _ramp(enter + i, rise_a, rise_b, 1.0, 1.0 / DUCK)
               * _ramp(i, fade_a, n, 1.0, 0.0) for i in range(n)]
        place(bed, enter)
        mark("theme", None, end_v, max(end_v, enter + n))
    else:
        c = chime()
        place(c, end_v + int(0.5 * RATE))
        mark("chime", None, end_v + int(0.5 * RATE), end_v + int(0.5 * RATE) + len(c))

    out.extend(silence(0.3))
    hiss = crackle(len(out), rng)
    out = [s + h for s, h in zip(out, hiss)]
    peak = max(1e-9, max(abs(s) for s in out))
    if peak > 0.95:
        out = [0.95 * s / peak for s in out]
    return out, cues
