#!/usr/bin/env python3
"""Build demo/, the no-setup copy of the presenter that GitHub Pages serves and opens from file://.

    python scripts/build_static_demo.py          # writes demo/
    python scripts/build_static_demo.py --check   # exits 1 if demo/ is stale

demo/index.html is the presenter template with asset paths made relative and the fonts inlined;
demo/data.js carries the app's own /api/config and /api/summary answers (which include every
recording). presenter.js reads window.DEMO_DATA when it is set and the API otherwise, so the two
never diverge. tests/test_static_demo.py rebuilds and compares.
"""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app

DEMO = ROOT / "demo"
FONTS = {"RH Display": "RedHatDisplay-VF.woff2", "RH Text": "RedHatText-VF.woff2",
         "RH Mono": "RedHatMono-VF.woff2"}


def fonts_css() -> str:
    rules = ["/* built by scripts/build_static_demo.py, SIL Open Font License */"]
    for family, name in FONTS.items():
        data = base64.b64encode((ROOT / "static" / "fonts" / name).read_bytes()).decode()
        rules.append(
            f"@font-face {{ font-family: '{family}'; font-weight: 300 900; font-display: block; "
            f"src: url('data:font/woff2;base64,{data}') format('woff2'); }}"
        )
    return "\n".join(rules) + "\n"


def build_files() -> dict[str, str]:
    with TestClient(app) as client:
        config = client.get("/api/config").json()
        summary = client.get("/api/summary").json()
        page = client.get("/").text

    data_js = (
        "// built by scripts/build_static_demo.py from the app; do not edit\n"
        "window.DEMO_DATA = " + json.dumps({"config": config, "summary": summary},
                                           ensure_ascii=True, sort_keys=True) + ";\n"
    )

    # make asset paths relative, inline the fonts, load data.js before presenter.js
    page = page.replace('href="/static/', 'href="static/').replace('src="/static/', 'src="static/')
    page = re.sub(r'\s*<link rel="preload"[^>]*as="font"[^>]*>', "", page)
    page = page.replace(
        '<link rel="stylesheet" href="static/css/presenter.css">',
        '<link rel="stylesheet" href="static/css/presenter.css">\n    <link rel="stylesheet" href="fonts.css">',
    )
    page = page.replace('<script src="static/js/presenter.js"></script>',
                        '<script src="data.js"></script>\n<script src="static/js/presenter.js"></script>')
    return {"index.html": page, "data.js": data_js, "fonts.css": fonts_css()}


def write(out: Path) -> dict[str, str]:
    files = build_files()
    for rel, content in files.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(content)
    # copy the static tree the relative page references
    import shutil

    for sub in ("css", "js", "images", "fonts"):
        src = ROOT / "static" / sub
        if src.is_dir():
            shutil.copytree(src, out / "static" / sub, dirs_exist_ok=True)
    return files


def stale() -> list[str]:
    fresh = build_files()
    out = []
    for rel, content in fresh.items():
        cur = DEMO / rel
        if not cur.is_file() or cur.read_text() != content:
            out.append(rel)
    return out


if __name__ == "__main__":
    if "--check" in sys.argv:
        diff = stale()
        if diff:
            print("demo/ is stale; run scripts/build_static_demo.py. Differs: " + ", ".join(diff))
            sys.exit(1)
        print("demo/ is current")
        sys.exit(0)
    written = write(DEMO)
    for rel in written:
        print(f"demo/{rel}  {len(written[rel]):,} bytes")
