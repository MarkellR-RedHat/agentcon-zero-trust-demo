#!/usr/bin/env python3
"""Fold a runs/ tree into runs_summary.json, the one file the app and slides read.

    python scripts/build_runs_file.py runs/2026-10-09-qwen-r1

The summary holds, per stage and lane, the attack/task/defender counts (how many attacks reached
their forbidden effect, how many the model refused, how many the gate blocked), plus the recorded
transcript the presenter replays for each scenario. Every number is derived here from the run
files; nothing is typed by hand. The app never recomputes a verdict, it only reads these.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

VERDICTS = ("FAIL", "BLOCKED", "REFUSED", "PASS", "INCOMPLETE")


def load_runs(root: Path) -> list[dict]:
    runs = []
    for f in sorted(root.rglob("*.json")):
        if f.name == "runs_summary.json":
            continue
        try:
            runs.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            print(f"skip (not a run file): {f}", file=sys.stderr)
    return runs


def build(root: Path) -> dict:
    runs = load_runs(root)
    if not runs:
        raise SystemExit(f"no run files under {root}")

    meta = runs[0]["run"]
    lanes: dict[str, dict] = {}
    # a single representative recorded transcript per (lane, stage, scenario), the temperature-0 run
    recordings: dict[str, dict] = {}

    for r in runs:
        lane_key = f"{r['lane']}-{r['policy']}" if r["lane"] == "guarded" else "bare"
        lane = lanes.setdefault(
            lane_key,
            {"lane": r["lane"], "policy": r["policy"], "stages": {}},
        )
        stage = lane["stages"].setdefault(
            str(r["stage"]),
            {"counts": defaultdict(int), "scenarios": defaultdict(lambda: defaultdict(int))},
        )
        stage["counts"][r["verdict"]] += 1
        stage["counts"]["total"] += 1
        stage["scenarios"][r["scenario"]][r["verdict"]] += 1
        stage["scenarios"][r["scenario"]]["kind"] = r["kind"]

        rec_key = f"{lane_key}/{r['stage']}/{r['scenario']}"
        if rec_key not in recordings or r["run"]["temperature"] == 0.0:
            recordings[rec_key] = {
                "lane": lane_key,
                "stage": r["stage"],
                "scenario": r["scenario"],
                "kind": r["kind"],
                "prompt": r["prompt"],
                "verdict": r["verdict"],
                "outcomes": r["outcomes"],
                "events": r["events"],
                "spans": r.get("spans", []),
                "messages": r["messages"],
                "summary": r["summary"],
            }

    # turn the defaultdicts into plain dicts and compute per-lane attack tallies
    out_lanes = {}
    for key, lane in lanes.items():
        stages = {}
        attacks_total = attacks_failed = attacks_blocked = attacks_refused = 0
        for sk, s in lane["stages"].items():
            scen = {name: dict(v) for name, v in s["scenarios"].items()}
            for v in scen.values():
                if v.get("kind") == "attack":
                    attacks_total += sum(v.get(x, 0) for x in VERDICTS)
                    attacks_failed += v.get("FAIL", 0)
                    attacks_blocked += v.get("BLOCKED", 0)
                    attacks_refused += v.get("REFUSED", 0)
            stages[sk] = {"counts": dict(s["counts"]), "scenarios": scen}
        out_lanes[key] = {
            "lane": lane["lane"],
            "policy": lane["policy"],
            "stages": stages,
            "attack_totals": {
                "total": attacks_total,
                "succeeded": attacks_failed,
                "blocked": attacks_blocked,
                "refused": attacks_refused,
            },
        }

    return {
        "schema": 1,
        "run": {k: meta[k] for k in ("date", "tag", "model", "runtime", "platform", "device")},
        "lanes": out_lanes,
        "recordings": recordings,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    root = Path(sys.argv[1])
    summary = build(root)
    out = root / "runs_summary.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    lanes = summary["lanes"]
    print(f"wrote {out}")
    for key, lane in lanes.items():
        t = lane["attack_totals"]
        print(f"  {key:16s} attacks {t['succeeded']}/{t['total']} succeeded, "
              f"{t['blocked']} blocked, {t['refused']} refused")
