"""The presenter app: serves the run data and the three-scene UI.

Everything the UI shows comes from runs_summary.json (built by scripts/build_runs_file.py from the
harness output). The app never recomputes a verdict or invents a number; it reads counts and
replays recorded transcripts. A SYNTHETIC banner shows whenever the data is the placeholder.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import ROOT, is_synthetic, settings, summary

app = FastAPI(title="Zero Trust Agents")

app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))

TITLE = "Zero Trust Agents"
SUBTITLE = "Red teaming an agent as it earns access, and the policy that tells a responder from an attacker"

STAGE_META = {
    "1": {"name": "File access", "tools": ["read_file", "write_file", "list_directory"]},
    "2": {"name": "Web + file access", "tools": ["read_file", "write_file", "list_directory",
                                                 "http_get", "http_post"]},
    "3": {"name": "Full access", "tools": ["read_file", "write_file", "list_directory",
                                           "http_get", "http_post", "execute_code", "run_shell"]},
    "4": {"name": "Defender: the forensic job", "tools": ["read_file", "list_directory", "write_file"]},
}

SCENARIO_LABEL = {
    "logs_task": "Read this morning's errors",
    "ssh_keys": "Read the SSH private key",
    "readme_injection": "Follow a README that says to read .env",
    "status_task": "Check the status page",
    "exfil_post": "POST the .env to an outside URL",
    "ssrf_metadata": "Fetch the internal metadata endpoint",
    "tests_task": "Run the test suite",
    "reverse_shell": "Run a reverse-shell diagnostic",
    "pip_mirror": "Install a package from a mirror",
    "privesc": "Probe for privilege escalation",
    "forensic": "Analyze the incident logs and write a report",
}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request=request, name="presenter.html", context={"title": TITLE}
    )


@app.get("/api/config")
async def config():
    s = summary()
    lane_order = ["bare", "guarded-scoped"]  # the two lanes shown side by side
    return {
        "title": TITLE,
        "subtitle": SUBTITLE,
        "mode": settings().demo_mode,
        "synthetic": is_synthetic(),
        "run": s["run"],
        "lanes": [
            {"key": k, "label": _lane_label(k), **s["lanes"][k]["attack_totals"]}
            for k in lane_order if k in s["lanes"]
        ],
        "all_lanes": list(s["lanes"].keys()),
        "stages": [{"key": k, **v} for k, v in STAGE_META.items()],
        "scenario_labels": SCENARIO_LABEL,
    }


@app.get("/api/summary")
async def api_summary():
    return summary()


@app.get("/api/recording/{lane}/{stage}/{scenario}")
async def recording(lane: str, stage: int, scenario: str):
    key = f"{lane}/{stage}/{scenario}"
    rec = summary()["recordings"].get(key)
    if rec is None:
        return JSONResponse(status_code=404, content={"error": f"no recording {key}"})
    return rec


def _lane_label(key: str) -> str:
    return {"bare": "No gate", "guarded-scoped": "Scoped policy",
            "guarded-blunt": "Blunt filter"}.get(key, key)


@app.get("/health")
async def health():
    return {"status": "ok", "mode": settings().demo_mode, "synthetic": is_synthetic()}
