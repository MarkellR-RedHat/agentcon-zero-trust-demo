#!/usr/bin/env python3
"""Re-score every run file in a runs/ tree with the current verdict rules, in place.

    python scripts/rescore_runs.py runs/2026-10-09-qwen-r1

A run record carries its sandbox outcomes, its events and its transcript, which is everything
the verdict reads, so a rule change never needs the model again. The verdict the harness wrote at
run time is kept as `verdict_at_run`; `verdict` becomes the current rule's answer and `summary`
gains the `capped` flag. Prints every file whose verdict changed. Follow with build_runs_file.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.verdict import summarize, verdict  # noqa: E402


def rescore(root: Path) -> list[tuple[str, str, str]]:
    changed = []
    for f in sorted(root.rglob("*.json")):
        if f.name == "runs_summary.json":
            continue
        d = json.loads(f.read_text())
        if "events" not in d:
            continue
        text = " ".join((m.get("content") or "") for m in d["messages"] if m["role"] == "assistant")
        new = verdict(d["kind"], d["scenario"], d["outcomes"], d["events"], text, d["messages"])
        d.setdefault("verdict_at_run", d["verdict"])
        if new != d["verdict"]:
            changed.append((str(f.relative_to(root)), d["verdict"], new))
        d["verdict"] = new
        d["summary"] = {**d["summary"], **summarize(d["events"], d["summary"]["total_ms"])}
        f.write_text(json.dumps(d, indent=2) + "\n")
    return changed


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    out = rescore(Path(sys.argv[1]))
    for rel, old, new in out:
        print(f"{rel:60s} {old:10s} -> {new}")
    print(f"{len(out)} verdict(s) changed")
