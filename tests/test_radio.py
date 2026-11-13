"""Tests for Release Radio. Run: python -m unittest discover -s tests -v

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import io
import json
import math
import re
import shutil
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "release-radio" / "scripts"
DEMO = ROOT / "skills" / "release-radio" / "assets" / "demo"
sys.path.insert(0, str(SCRIPTS))

import broadcast  # noqa: E402
import check_data  # noqa: E402
import mix  # noqa: E402
import player  # noqa: E402
import radio  # noqa: E402


def fake_read(segs, words_per_sec=2.6, gap=0.9, sentence_gap=0.3):
    """A stand-in for a recorded read: a buzzing 'voice' per sentence, short pauses between
    sentences and a longer pause between paragraphs, like a real announcer."""
    out = []
    for k, s in enumerate(segs):
        sentences = [x for x in re.split(r"(?<=[.!?])\s+", s["text"]) if x]
        for j, sent in enumerate(sentences):
            n = int(len(sent.split()) / words_per_sec * mix.RATE)
            out += [0.4 * math.sin(i / 9) * (0.6 + 0.4 * math.sin(i / 1500)) for i in range(n)]
            if j < len(sentences) - 1:
                out += [0.0] * int(sentence_gap * mix.RATE)
        if k < len(segs) - 1:
            out += [0.0] * int(gap * mix.RATE)
    return out


class Score(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = radio.compose(DEMO)

    def test_one_entry_per_day(self):
        self.assertEqual(len(self.score["bars"]), 14)
        self.assertEqual(self.score["window"], {"start": "2026-10-26", "end": "2026-11-08", "days": 14})

    def test_story_states(self):
        states = [b["state"] for b in self.score["bars"]]
        self.assertEqual(states[:4], ["steady"] * 4)
        self.assertEqual(states[4:6], ["failed", "failed"])
        self.assertEqual(states[6], "freeze")
        self.assertEqual(states[7], "steady")
        self.assertEqual(states[8:10], ["incident", "incident"])
        self.assertEqual(states[10:], ["recovered"] * 4)

    def test_totals(self):
        self.assertEqual(self.score["totals"], {"deploys": 40, "runs": 109, "failed_runs": 6, "incidents": 1})

    def test_evidence_is_specific(self):
        day9 = self.score["bars"][8]["evidence"]
        self.assertEqual(day9[0], "INC-07 opened (checkout)")
        self.assertIn("rollback d-09rb (checkout)", day9)
        self.assertIn("SLO burn 2.3x (over 1.0)", day9)
        self.assertEqual(self.score["bars"][10]["evidence"][0], "INC-07 resolved after 50h")
        self.assertIn("deploy freeze: no deploys and no CI runs", self.score["bars"][6]["evidence"])

    def test_feature_branches_ignored(self):
        runs = json.loads((DEMO / "ci_runs.json").read_text())["runs"]
        self.assertEqual(self.score["totals"]["runs"], sum(1 for r in runs if r["branch"] == "main"))

    def test_status_free_runs_use_real_failures(self):
        self.assertTrue(radio.run_failed({"real_failures": ["t"]}))
        self.assertFalse(radio.run_failed({"real_failures": [], "flaky_failures": ["t"]}))


class Script(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = radio.compose(DEMO)
        cls.segs = broadcast.script(cls.score)
        cls.text = " ".join(s["text"] for s in cls.segs)

    def test_segments_cover_every_day_once(self):
        covered = [n for s in self.segs if s["bars"] for n in range(s["bars"][0], s["bars"][1] + 1)]
        self.assertEqual(covered, list(range(1, 15)))
        self.assertEqual((self.segs[0]["kind"], self.segs[-1]["kind"]), ("sign-on", "sign-off"))

    def test_script_states_the_facts(self):
        for fact in ("urgent bulletin", "incident number 7 struck the checkout service", "at 10:12 Greenwich time",
                     "2.3 times the safe rate", "after 50 long hours", "5 of 17 builds failed",
                     "40 deploys, 109 builds and 1 incident", "A deploy freeze"):
            self.assertIn(fact, self.text)

    def test_no_music_left_in_the_script(self):
        low = self.text.lower()
        for word in ("band", "music", "minor key", "c major", "siren", " bar ", " note"):
            self.assertNotIn(word, low, word)

    def test_no_em_dashes_or_people(self):
        self.assertNotIn(chr(0x2014), self.text)
        self.assertNotRegex(self.text, r"@\w")

    def test_deterministic(self):
        self.assertEqual(self.segs, broadcast.script(radio.compose(DEMO)))

    def test_spoken_helpers(self):
        self.assertEqual(broadcast.spoken_id("INC-07"), "incident number 7")
        self.assertEqual(broadcast.spoken_date("2026-11-01"), "Sunday, November 1st")
        self.assertEqual(broadcast.spoken_test("test_cart_total_rounding_b"), "cart total rounding")

    def test_cue_sheet_and_read_text(self):
        sheet = broadcast.cue_sheet_md(self.score, self.segs)
        self.assertEqual(sheet.count("> THEME"), 3)
        self.assertEqual(sheet.count("> CHIME"), 1)
        read = broadcast.read_text(self.segs)
        self.assertEqual(read.count("\n\n"), len(self.segs) - 1)


class MissingData(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        for f in DEMO.glob("*.json"):
            shutil.copy(f, self.dir / f.name)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_missing_source_is_announced(self):
        (self.dir / "slo_daily.json").unlink()
        score = radio.compose(self.dir)
        self.assertEqual(score["static"], ["slo_daily"])
        text = " ".join(s["text"] for s in broadcast.script(score))
        self.assertIn("carried static", text)
        self.assertNotIn("safe rate", text)

    def test_bad_source_is_set_aside(self):
        (self.dir / "incidents.json").write_text(json.dumps({"incidents": [{"id": "X"}]}))
        score = radio.compose(self.dir)
        self.assertIn("incidents", score["source_problems"])
        self.assertNotIn("incident", [b["state"] for b in score["bars"]])

    def test_open_incident_has_no_all_clear(self):
        data = json.loads((self.dir / "incidents.json").read_text())
        del data["incidents"][0]["resolved_at"]
        (self.dir / "incidents.json").write_text(json.dumps(data))
        score = radio.compose(self.dir)
        self.assertEqual(score["bars"][-1]["state"], "incident")
        self.assertNotIn("all clear", " ".join(s["text"] for s in broadcast.script(score)))


class Mixer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.score = radio.compose(DEMO)
        cls.segs = broadcast.script(cls.score)
        cls.theme = mix.load_wav(radio.THEME)

    def test_theme_asset(self):
        self.assertGreater(len(self.theme) / mix.RATE, 15)

    def test_split_one_read_into_segments(self):
        pieces = mix.split_read(fake_read(self.segs), self.segs)
        self.assertEqual(list(pieces), [s["id"] for s in self.segs])
        words = [len(s["text"].split()) for s in self.segs]
        lengths = [len(pieces[s["id"]]) for s in self.segs]
        self.assertEqual(lengths.index(max(lengths)), words.index(max(words)))

    def test_bad_read_fails_loudly(self):
        with self.assertRaises(ValueError):
            mix.split_read(fake_read(self.segs[:3]), self.segs)

    def test_broadcast_order_and_levels(self):
        voices = mix.split_read(fake_read(self.segs), self.segs)
        samples, cues = mix.build(self.segs, voices, self.theme)
        kinds = [c["kind"] for c in cues]
        self.assertEqual(kinds[0], "theme")
        self.assertEqual(kinds[-1], "theme")
        self.assertEqual(kinds.count("chime"), 1)
        chime_at = kinds.index("chime")
        self.assertEqual(cues[chime_at + 1]["segment"], "bars-9-10")
        self.assertEqual([c["segment"] for c in cues if c["kind"] == "voice"], [s["id"] for s in self.segs])
        self.assertLessEqual(max(abs(s) for s in samples), 0.951)
        r = mix.RATE

        def db(t0, t1):
            x = samples[int(t0 * r):int(t1 * r)]
            return 20 * math.log10(math.sqrt(sum(v * v for v in x) / len(x)))
        theme_alone, under_voice = db(0.5, 5.5), db(cues[1]["t0"] + 2, cues[1]["t1"] - 1)
        self.assertGreater(theme_alone, -24)
        self.assertGreater(under_voice, theme_alone - 6)  # the voice carries over the ducked theme

    def test_without_theme_uses_chimes(self):
        voices = mix.split_read(fake_read(self.segs), self.segs)
        _, cues = mix.build(self.segs, voices, None)
        self.assertEqual([c["kind"] for c in cues].count("chime"), 3)

    def test_mix_is_deterministic(self):
        voices = mix.split_read(fake_read(self.segs), self.segs)
        a, _ = mix.build(self.segs, voices, self.theme[:mix.RATE * 12])
        b, _ = mix.build(self.segs, voices, self.theme[:mix.RATE * 12])
        self.assertEqual(a, b)

    def test_load_wav_resamples_stereo(self):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(struct.pack("<8820h", *([1000, -1000] * 4410)))
        p = Path(tempfile.mkdtemp()) / "x.wav"
        p.write_bytes(buf.getvalue())
        x = mix.load_wav(p)
        self.assertAlmostEqual(len(x), 2205, delta=2)
        self.assertTrue(all(abs(v) < 1e-9 for v in x))
        shutil.rmtree(p.parent)


class EndToEnd(unittest.TestCase):
    def test_demo_without_voice(self):
        out = Path(tempfile.mkdtemp())
        try:
            radio.main(["demo", "--out", str(out)])
            page = (out / "player.html").read_text()
            self.assertIn('<audio id="t"', page)
            self.assertNotIn('<audio id="b"', page)
            self.assertIn("speechSynthesis", page)
            self.assertEqual(page.count('class="cue"'), 8)
            self.assertEqual(page.count('class="day'), 14)
            self.assertNotRegex(page, r"(src|href)=\"https?://")
            self.assertFalse((out / "broadcast.wav").exists())
            self.assertIn("INC-07 opened (checkout)", (out / "the_record.md").read_text())
        finally:
            shutil.rmtree(out)

    def test_demo_with_one_recorded_read(self):
        out = Path(tempfile.mkdtemp())
        try:
            segs = broadcast.script(radio.compose(DEMO))
            mix.write_wav(fake_read(segs), out / "read.wav")
            radio.main(["demo", "--out", str(out), "--voice-file", str(out / "read.wav")])
            self.assertTrue((out / "broadcast.wav").exists())
            cues = json.loads((out / "cues.json").read_text())
            self.assertEqual(sum(c["kind"] == "voice" for c in cues), 8)
            page = (out / "player.html").read_text()
            self.assertIn('<audio id="b"', page)
            self.assertIn("Announcer voice by ElevenLabs", page)
        finally:
            shutil.rmtree(out)


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ElevenLabsAPI(unittest.TestCase):
    """The API path with a stand-in for ElevenLabs, so tests never touch the network."""

    def setUp(self):
        import voice
        self.voice = voice
        self.tmp = Path(tempfile.mkdtemp())
        self.calls = []
        self.segs = broadcast.script(radio.compose(DEMO))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def fake(self, req, timeout=0):
        body = json.loads(req.data)
        self.calls.append((req.full_url, dict(req.headers), body))
        n = int(len(body["text"].split()) * 0.1 * mix.RATE)
        return _Resp(struct.pack(f"<{n}h", *[int(8000 * math.sin(i / 20)) for i in range(n)]))

    def test_request_shape_and_cache(self):
        self.voice.render(self.segs, self.tmp, "VID", "MODEL", "KEY", opener=self.fake)
        self.assertEqual(len(self.calls), len(self.segs))
        url, headers, body = self.calls[0]
        self.assertEqual(url, "https://api.elevenlabs.io/v1/text-to-speech/VID?output_format=pcm_22050")
        self.assertEqual(headers["Xi-api-key"], "KEY")
        self.assertEqual((body["model_id"], body["text"]), ("MODEL", self.segs[0]["text"]))
        self.voice.render(self.segs, self.tmp, "VID", "MODEL", "KEY", opener=self.fake)
        self.assertEqual(len(self.calls), len(self.segs), "second run must come from the cache")

    def test_missing_key_stops_cleanly(self):
        with self.assertRaises(SystemExit):
            self.voice.render(self.segs, self.tmp, "VID", "MODEL", None, opener=self.fake)
        self.assertEqual(self.calls, [])


class Contract(unittest.TestCase):
    def test_demo_passes(self):
        for name in check_data.CONTRACT:
            self.assertEqual(check_data.check(name, json.loads((DEMO / f"{name}.json").read_text())), [], name)

    def test_catches_bad_records(self):
        self.assertTrue(check_data.check("deployments", {"deployments": [{"id": "x", "at": "yesterday"}]}))
        self.assertTrue(check_data.check("slo_daily", {"days": [{"date": "2026-11-01", "burn_rate": "high"}]}))
        self.assertTrue(check_data.check("ci_runs", {"runs": "nope"}))


class Hygiene(unittest.TestCase):
    def test_no_people_in_demo(self):
        text = "".join(f.read_text() for f in DEMO.glob("*.json")).lower()
        for field in ("author", "assignee", "reporter", "email", "user\""):
            self.assertNotIn(field, text)

    def test_only_voice_uses_network(self):
        pat = re.compile(r"^\s*(import|from)\s+(socket|urllib|http|requests)\b", re.M)
        for f in SCRIPTS.glob("*.py"):
            if f.name != "voice.py":
                self.assertIsNone(pat.search(f.read_text()), f.name)

    def test_voice_only_imported_on_request(self):
        text = (SCRIPTS / "radio.py").read_text()
        self.assertLess(text.index('elif args.voice == "elevenlabs":'), text.index("import voice"))

    def test_no_homemade_music_left(self):
        self.assertFalse((SCRIPTS / "synth.py").exists())


if __name__ == "__main__":
    unittest.main()
