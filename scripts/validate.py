"""Repository checks for Release Radio. Run before every commit and in CI.

Checks: SKILL.md frontmatter, JSON parses, demo data passes the contract, no network
imports in skill scripts, no em dashes in text files.

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "release-radio"
TEXT = {".md", ".py", ".json", ".yml", ".yaml", ".html"}
NETWORK = re.compile(r"^\s*(import|from)\s+(socket|urllib|http|requests|httpx|aiohttp|ftplib|smtplib)\b", re.M)
errors = []

front = re.match(r"^---\n(.*?)\n---\n", (SKILL / "SKILL.md").read_text(), re.S)
fields = dict(l.split(":", 1) for l in front.group(1).splitlines() if ":" in l) if front else {}
if fields.get("name", "").strip() != "release-radio":
    errors.append("SKILL.md: name must be release-radio")
if len(fields.get("description", "").strip()) < 40:
    errors.append("SKILL.md: description too short")

if not (SKILL / "assets" / "theme" / "wrel_theme.wav").exists():
    errors.append("assets/theme/wrel_theme.wav: the WREL theme is missing")

sys.path.insert(0, str(SKILL / "scripts"))
import check_data  # noqa: E402

for name in check_data.CONTRACT:
    problems = check_data.check(name, json.loads((SKILL / "assets" / "demo" / f"{name}.json").read_text()))
    if problems:
        errors.append(f"demo {name}.json: {problems}")

for path in ROOT.rglob("*"):
    if not path.is_file() or ".git" in path.parts or "dist" in path.parts or path.suffix not in TEXT:
        continue
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)
    if chr(0x2014) in text:
        errors.append(f"{rel}: contains an em dash")
    if path.suffix == ".json":
        try:
            json.loads(text)
        except ValueError as e:
            errors.append(f"{rel}: invalid JSON ({e})")

for path in (SKILL / "scripts").glob("*.py"):
    if path.name == "voice.py":  # the one opt-in network step: ElevenLabs, only with --voice elevenlabs and your key
        continue
    if NETWORK.search(path.read_text()):
        errors.append(f"{path.relative_to(ROOT)}: network import")

if errors:
    print("FAILED\n" + "\n".join(f"  - {e}" for e in errors))
    sys.exit(1)
print("OK: skill metadata, demo data contract, JSON, no network imports, no em dashes")
