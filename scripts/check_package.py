#!/usr/bin/env python3
"""Check a results package against the definition of done. Every check opens a file; none needs judgment.

    python scripts/check_package.py runs/qwen-r2 --repeat 9
    python scripts/check_package.py runs/2026-10-09-qwen-r1 --repeat 3 --served-name qwen-bf16

Prints one PASS or FAIL line per check and exits 1 if any check failed. The work laptop runs it before
zipping; the Mac runs it on arrival. A FAIL on the laptop means stop and write BLOCKED.md, not fix.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

LANES = ("bare-none", "guarded-blunt", "guarded-scoped")
# scenario -> (stage, kind). The task scenarios run once (temperature 0); attacks and the defender
# job run once at 0 plus --repeat times at 0.7.
SCENARIOS = {
    "logs_task": (1, "task"), "ssh_keys": (1, "attack"), "readme_injection": (1, "attack"),
    "status_task": (2, "task"), "exfil_post": (2, "attack"), "ssrf_metadata": (2, "attack"),
    "tests_task": (3, "task"), "reverse_shell": (3, "attack"), "pip_mirror": (3, "attack"), "privesc": (3, "attack"),
    "forensic": (4, "defender"),
}
VERDICTS = {"FAIL", "BLOCKED", "REFUSED", "PASS", "INCOMPLETE"}
LEAK_PATTERNS = [
    (r"sha256~", "an OpenShift token"),
    (r"[a-z0-9.-]+\.openshiftapps\.com", "a cluster hostname"),
    (r"api\.[a-z0-9.-]+\.redhat\.com", "a cluster API hostname"),
    (r"apps\.[a-z0-9.-]+\.[a-z]{2,}", "a cluster apps hostname"),
    (r"/Users/[A-Za-z0-9_.-]+", "a Mac home directory (a username)"),
    (r"/home/(?!deploy\b)[A-Za-z0-9_.-]+", "a Linux home directory (a username)"),
    (r"Co-Authored-By|Anthropic|Claude", "AI attribution"),
]


def expected_files(repeat: int) -> dict[str, int]:
    per_stage = Counter()
    for _name, (stage, kind) in SCENARIOS.items():
        per_stage[stage] += 1 if kind == "task" else 1 + repeat
    return {f"stage{s}": n for s, n in sorted(per_stage.items())}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("runs_dir")
    p.add_argument("--repeat", type=int, default=9, help="runs at 0.7 per attack; 9 means 10 per attack")
    p.add_argument("--served-name", default="qwen-agent")
    p.add_argument("--runtime", default="vLLM 0.24.0+rhaiv.13")
    p.add_argument("--device", default="1 x 71 GB MIG slice (3g.71gb) of an H200")
    p.add_argument("--startup-log", default="qwen-agent-startup.txt")
    p.add_argument("--max-tool-rounds", type=int, default=8)
    args = p.parse_args()

    root = Path(args.runs_dir)
    results: list[tuple[bool, str]] = []

    def check(ok: bool, text: str) -> None:
        results.append((bool(ok), text))

    check(root.is_dir(), f"run folder exists: {root}")
    if not root.is_dir():
        return report(results)

    # 1. file counts, exactly
    want = expected_files(args.repeat)
    total_want = sum(want.values()) * len(LANES)
    files = [f for f in root.rglob("*.json") if f.name != "runs_summary.json"]
    check(len(files) == total_want, f"{len(files)} run files (expected exactly {total_want})")
    for lane in LANES:
        for stage, n in want.items():
            have = len(list((root / lane / stage).glob("*.json"))) if (root / lane / stage).is_dir() else 0
            check(have == n, f"{lane}/{stage}: {have} files (expected {n})")

    # 2. file names follow <scenario>_t<temp>_r<k>.json, with r0 at temperature 0 and the rest at 0.7
    name_re = re.compile(r"^([a-z_]+)_t(00|07)_r(\d+)\.json$")
    bad_names = [str(f.relative_to(root)) for f in files if not name_re.match(f.name)]
    check(not bad_names, f"every file name matches <scenario>_t00|t07_r<k>.json (bad: {bad_names[:3]})")

    # 3. every record's metadata says the same thing, and it is the thing we asked for
    records = []
    broken = []
    for f in files:
        try:
            records.append((f, json.loads(f.read_text())))
        except json.JSONDecodeError:
            broken.append(str(f.relative_to(root)))
    check(not broken, f"every run file parses as JSON (broken: {broken[:3]})")

    def field_set(path: tuple[str, ...]) -> set:
        out = set()
        for _f, d in records:
            v = d
            for k in path:
                v = v.get(k, {}) if isinstance(v, dict) else {}
            out.add(json.dumps(v, sort_keys=True) if isinstance(v, dict | list) else v)
        return out

    served = field_set(("run", "served_name"))
    model = field_set(("run", "model"))
    check(served == {args.served_name}, f"run.served_name is exactly {args.served_name!r} in every file (saw {sorted(map(str, served))})")
    check(model == {args.served_name}, f"run.model is exactly {args.served_name!r} in every file (saw {sorted(map(str, model))})")
    check(field_set(("run", "runtime")) == {args.runtime}, f"run.runtime is {args.runtime!r} in every file")
    check(field_set(("run", "platform")) == {"OpenShift AI"}, "run.platform is 'OpenShift AI' in every file")
    check(field_set(("run", "device")) == {args.device}, f"run.device is {args.device!r} in every file")
    dates = field_set(("run", "date"))
    check(len(dates) == 1 and all(re.match(r"^\d{4}-\d{2}-\d{2}$", str(d)) for d in dates), f"run.date is one real date in every file (saw {sorted(map(str, dates))})")
    check(field_set(("run", "max_tool_rounds")) == {args.max_tool_rounds}, f"run.max_tool_rounds is {args.max_tool_rounds} everywhere")
    check(field_set(("schema",)) == {1}, "schema is 1 in every file")

    # 4. temperature and repeat match the file name; lane and policy match the folder
    mismatch = []
    for f, d in records:
        m = name_re.match(f.name)
        if not m:
            continue
        scenario, tlabel, k = m.group(1), m.group(2), int(m.group(3))
        temp = d.get("run", {}).get("temperature")
        want_t = 0.0 if tlabel == "00" else 0.7
        lane_dir = f.parent.parent.name
        want_lane, want_policy = lane_dir.split("-", 1)
        stage_dir = f.parent.name
        ok = (
            temp == want_t and d.get("run", {}).get("repeat") == k and d.get("scenario") == scenario
            and d.get("lane") == want_lane and d.get("policy") == want_policy
            and f"stage{d.get('stage')}" == stage_dir and SCENARIOS.get(scenario, (None, None))[1] == d.get("kind")
        )
        if not ok:
            mismatch.append(str(f.relative_to(root)))
    check(not mismatch, f"name, folder and record agree on scenario, lane, policy, stage, kind, temperature, repeat (bad: {mismatch[:3]})")

    # 5. every record is complete: events, messages, outcomes, verdict, summary
    incomplete = []
    for f, d in records:
        if not (d.get("events") and d.get("messages") and isinstance(d.get("outcomes"), list)
                and d.get("verdict") in VERDICTS and isinstance(d.get("summary"), dict)
                and "total_ms" in d["summary"]):
            incomplete.append(str(f.relative_to(root)))
    check(not incomplete, f"every record has events, messages, outcomes, a known verdict and a summary (bad: {incomplete[:3]})")
    no_model_call = [str(f.relative_to(root)) for f, d in records if not any(e.get("type") == "model.done" for e in d.get("events", []))]
    check(not no_model_call, f"every record shows a completed model call (bad: {no_model_call[:3]})")

    # 6. the startup log is there and agrees with the records
    log = root / args.startup_log
    check(log.is_file(), f"startup log present: {log.name}")
    if log.is_file():
        text = log.read_text(errors="replace")
        ver = re.search(r"version (\S+)", text)
        check(bool(ver) and f"vLLM {ver.group(1)}" == args.runtime, f"startup log vLLM version matches run.runtime ({ver.group(1) if ver else 'none found'})")
        check("'tool_call_parser': 'qwen3_xml'" in text, "startup log shows tool_call_parser qwen3_xml")
        check("'enable_auto_tool_choice': True" in text, "startup log shows enable_auto_tool_choice True")
        check("'enforce_eager': True" in text, "startup log shows enforce_eager True (timings are eager-mode)")
        check("'max_model_len': 16384" in text, "startup log shows max_model_len 16384")
        check(f"'served_model_name': ['{args.served_name}']" in text, f"startup log shows served_model_name {args.served_name}")
        check("'model': 'Qwen/Qwen3.8-27B'" in text, "startup log shows model Qwen/Qwen3.8-27B")
        check(bool(re.search(r"Model loading took [\d.]+ GiB", text)), "startup log shows the loaded weight size")
        check(bool(re.search(r"Available KV cache memory", text)), "startup log shows the KV cache size")

    # 7. the pod description proves the MIG slice
    pod = root / "qwen-agent-pod.yaml"
    check(pod.is_file(), "pod description present: qwen-agent-pod.yaml")
    if pod.is_file():
        check("nvidia.com/mig-3g.71gb" in pod.read_text(), "pod description requests nvidia.com/mig-3g.71gb")

    # 8. nothing private in any text file, and no attribution
    leaks = []
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.lower() in {".json", ".txt", ".md", ".yaml", ".yml", ".log", ".csv"}:
            body = f.read_text(errors="replace")
            for pat, what in LEAK_PATTERNS:
                if re.search(pat, body):
                    leaks.append(f"{f.relative_to(root)}: {what}")
                    break
    check(not leaks, f"no text file contains a token, hostname, username or attribution (hits: {leaks[:3]})")

    # 9. captures are real PNGs, named as the table says
    caps = root / "captures"
    pngs = sorted(caps.glob("*.png")) if caps.is_dir() else []
    check(caps.is_dir() and len(pngs) >= 1, f"captures/ folder present with PNG files ({len(pngs)} found)")
    not_png = [p.name for p in pngs if p.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n"]
    check(not not_png, f"every .png in captures/ is a real PNG file (bad: {not_png[:3]})")
    tiny = [p.name for p in pngs if p.stat().st_size < 20_000]
    check(not tiny, f"no capture is under 20 KB, which would mean a cropped-to-nothing or placeholder image (bad: {tiny[:3]})")

    # 10. RUN-FACTS.md is present and was generated (it carries the generator's marker line)
    facts = root / "RUN-FACTS.md"
    check(facts.is_file(), "RUN-FACTS.md present")
    if facts.is_file():
        check("generated by scripts/run_facts.py" in facts.read_text(), "RUN-FACTS.md was generated by scripts/run_facts.py, not typed")

    return report(results)


def report(results: list[tuple[bool, str]]) -> int:
    failed = 0
    for ok, text in results:
        print(("PASS  " if ok else "FAIL  ") + text)
        failed += 0 if ok else 1
    print(f"\n{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
