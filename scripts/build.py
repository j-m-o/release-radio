"""Package the skill as dist/release-radio.zip for upload (Claude, Agensi or any SKILL.md agent).

Release Radio, created by Jessica Mosley | LinkedIn: https://www.linkedin.com/in/jessmosley/ | GitHub: https://github.com/j-m-o/
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "release-radio"
OUT = ROOT / "dist" / "release-radio.zip"
OUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for path in sorted(SKILL.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            info = zipfile.ZipInfo(str(Path("release-radio") / path.relative_to(SKILL)), date_time=(2026, 11, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())
print(f"Built {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
