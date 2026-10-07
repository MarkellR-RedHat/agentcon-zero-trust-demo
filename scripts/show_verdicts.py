#!/usr/bin/env python3
"""Print one line per run file: lane, stage, scenario, temperature, repeat, verdict, outcomes.

    python scripts/show_verdicts.py runs/qwen-r2 guarded-scoped
    python scripts/show_verdicts.py runs/qwen-r2            # every lane

Read from the run files, so it works whether or not a lane's console log survived.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(runs_dir: str, lane: str | None = None) -> int:
    root = Path(runs_dir)
    lanes = [lane] if lane else sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "stage1").is_dir())
    n = 0
    for ln in lanes:
        for f in sorted((root / ln).glob("stage*/*.json")):
            d = json.loads(f.read_text())
            n += 1
            print(f"{ln:15s} stage{d['stage']} {d['scenario']:17s} t{d['run']['temperature']} r{d['run']['repeat']:<2d} "
                  f"-> {d['verdict']:9s} {d.get('outcomes')}")
    print(f"{n} run files")
    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
