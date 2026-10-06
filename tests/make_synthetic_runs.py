"""Generate a synthetic runs/ tree so the app and slides can be built before the real run lands.

It runs the harness against the bundled fake model server (tests/fake_openai_server.py), which is
deterministic, and tags every run SYNTHETIC. The output is NOT real measurement: the app shows a
"SYNTHETIC DATA" banner whenever runs_summary.json carries this tag, so a placeholder is never
mistaken for the Qwen run. Replaced wholesale by results-agntcon.zip on Oct 9.

    python tests/make_synthetic_runs.py <out-dir>
"""

from __future__ import annotations

import asyncio
import sys
import typing
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness import agent as agent_mod
from harness import run as runner
from tests.fake_openai_server import app as fake_app


def _patch_agent_to_fake():
    real = agent_mod.httpx.AsyncClient

    def fake(*a, **kw):
        return real(transport=httpx.ASGITransport(app=fake_app), base_url="http://fake")

    agent_mod.httpx.AsyncClient = fake


class Args:
    endpoint = "http://fake/v1/chat/completions"
    model = "synthetic-fake"
    served_name = "synthetic"
    runtime = "fake server (SYNTHETIC)"
    platform = "local"
    device = "none"
    date = "2026-10-06"
    tag = "SYNTHETIC"
    temperature = 0.7
    repeat = 2
    max_tool_rounds = 8
    stage: typing.ClassVar = [1, 2, 3, 4]


async def generate(out: str):
    _patch_agent_to_fake()
    for lane, policy in (("bare", "none"), ("guarded", "blunt"), ("guarded", "scoped")):
        args = Args()
        args.lane, args.policy, args.out = lane, policy, out
        await runner.main_async(args)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "runs" / "2026-10-06-SYNTHETIC")
    asyncio.run(generate(out))
    print(f"synthetic runs under {out}")
