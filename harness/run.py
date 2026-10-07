"""Run the scenarios and write the run files the app and slides read.

    python -m harness.run --lane bare   --stage 1 2 3 4 --out runs/2026-10-09-qwen-r1
    python -m harness.run --lane guarded --policy scoped --stage 1 2 3 4 --out runs/...

Each scenario runs `--repeat` times at `--temperature` and once at 0. One file per run:
    <out>/<lane>-<policy>/stage<N>/<scenario>_t<temp>_r<k>.json
Set VLLM_ENDPOINT, VLLM_MODEL (and VLLM_API_KEY) for the real model; with none set it uses the
bundled fake server fixture so the harness can be exercised without a GPU.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from harness import scenarios
from harness.agent import run_agent
from harness.gate import BLUNT, make_gate, scoped_for
from harness.sandbox_fs import FILES, INJECTION_MARKER, Sandbox, make_runner
from harness.tools import tools_for_stage
from harness.tracing import export_mlflow, to_spans
from harness.verdict import outcomes, summarize, verdict

SCHEMA = 1


def gate_for(lane: str, policy: str, stage: int, forensic: bool):
    if lane == "bare":
        return None, "none"
    if policy == "blunt":
        return make_gate(BLUNT), "blunt"
    return make_gate(scoped_for(stage, forensic=forensic)), "scoped"


async def one_run(args, stage, kind, scenario, prompt, injected, temperature, repeat_k):
    sandbox = Sandbox()
    # A poisoned file is set up in the sandbox before the run, so the injection arrives through a
    # tool result, not the prompt.
    if injected:
        FILES[injected["where"]] = FILES.get(injected["where"], "") + "\n<!-- " + injected["text"] + " -->\n"

    gate, policy_name = gate_for(args.lane, args.policy, stage, forensic=(kind == "defender"))
    start = time.perf_counter()
    result = await run_agent(
        endpoint=os.environ.get("VLLM_ENDPOINT", args.endpoint),
        model=os.environ.get("VLLM_MODEL", args.model),
        prompt=prompt,
        tools=tools_for_stage(stage),
        run_tool=make_runner(sandbox),
        gate=gate,
        temperature=temperature,
        max_tool_rounds=args.max_tool_rounds,
        api_key=os.environ.get("VLLM_API_KEY", ""),
    )
    total_ms = round((time.perf_counter() - start) * 1000)
    assistant_text = " ".join(
        m.get("content") or "" for m in result.messages if m["role"] == "assistant"
    )
    effects = outcomes(sandbox)
    v = verdict(kind, scenario, effects, result.events, assistant_text, result.messages)
    run_meta = {
        "date": args.date, "tag": args.tag, "model": os.environ.get("VLLM_MODEL", args.model),
        "served_name": args.served_name, "runtime": args.runtime, "platform": args.platform,
        "device": args.device, "temperature": temperature, "repeat": repeat_k,
        "max_tool_rounds": args.max_tool_rounds,
    }
    mlflow_id = export_mlflow(run_meta, args.lane, scenario, result.events)
    return {
        "schema": SCHEMA,
        "run": run_meta,
        "lane": args.lane,
        "policy": policy_name,
        "stage": stage,
        "scenario": scenario,
        "kind": kind,
        "prompt": prompt,
        "injected": injected,
        "injection_marker_in_result": INJECTION_MARKER if injected else None,
        "events": result.events,
        "spans": to_spans(result.events),
        "messages": result.messages,
        "outcomes": effects,
        "verdict": v,
        "mlflow_run_id": mlflow_id,
        "summary": summarize(result.events, total_ms),
    }


async def main_async(args):
    out_root = Path(args.out)
    lane_dir = out_root / f"{args.lane}-{args.policy if args.lane == 'guarded' else 'none'}"
    for stage, kind, scenario, prompt, injected in scenarios.iter_runs(args.stage):
        temps = [0.0] if kind == "task" else [0.0] + [args.temperature] * args.repeat
        for k, temp in enumerate(temps):
            record = await one_run(args, stage, kind, scenario, prompt, injected, temp, k)
            d = lane_dir / f"stage{stage}"
            d.mkdir(parents=True, exist_ok=True)
            tlabel = str(temp).replace(".", "")
            path = d / f"{scenario}_t{tlabel}_r{k}.json"
            path.write_text(json.dumps(record, indent=2) + "\n")
            print(f"{args.lane:8s} {args.policy:7s} stage{stage} {scenario:16s} "
                  f"t{temp} r{k} -> {record['verdict']:9s} {record['outcomes']}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lane", choices=["bare", "guarded"], required=True)
    p.add_argument("--policy", choices=["none", "blunt", "scoped"], default="none")
    p.add_argument("--stage", type=int, nargs="+", default=[1, 2, 3, 4])
    p.add_argument("--out", required=True)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--max-tool-rounds", type=int, default=8)
    p.add_argument("--endpoint", default="http://localhost:8080/v1/chat/completions")
    p.add_argument("--model", default="qwen-agent")
    p.add_argument("--served-name", default="qwen-agent")
    p.add_argument("--runtime", default="vLLM 0.24.0+rhaiv.13")
    p.add_argument("--platform", default="OpenShift AI")
    p.add_argument("--device", default="1 x 71 GB MIG slice (3g.71gb) of an H200")
    p.add_argument("--date", default=time.strftime("%Y-%m-%d"))
    p.add_argument("--tag", default="qwen-r2")
    return p


if __name__ == "__main__":
    asyncio.run(main_async(build_parser().parse_args()))
