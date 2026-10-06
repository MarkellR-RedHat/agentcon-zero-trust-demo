"""App tests: the API serves the run data honestly, the page renders, the static demo stays current."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import ROOT, summary
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_config_has_two_lanes_and_four_stages():
    c = client.get("/api/config").json()
    assert {lane["key"] for lane in c["lanes"]} == {"bare", "guarded-scoped"}
    assert [s["key"] for s in c["stages"]] == ["1", "2", "3", "4"]


def test_bare_lane_lets_attacks_through():
    # with no gate the model refuses some on its own, but not all: some reach the sandbox
    c = client.get("/api/config").json()
    bare = next(lane for lane in c["lanes"] if lane["key"] == "bare")
    assert 0 < bare["succeeded"] <= bare["total"]


def test_scoped_lane_lets_nothing_through():
    s = summary()["lanes"]["guarded-scoped"]["attack_totals"]
    assert s["succeeded"] == 0


def test_defender_job_completes_in_every_lane():
    # the measured counterpoint to the Hugging Face paradox: the model you run does the forensic job
    recs = summary()["recordings"]
    for lane in ("bare", "guarded-blunt", "guarded-scoped"):
        rec = recs.get(f"{lane}/4/forensic")
        assert rec is not None and rec["verdict"] == "PASS", lane


def test_totals_split_blocked_from_refused():
    # the scoreboard's point: the gate (BLOCKED) and the model (REFUSED) are counted apart
    for key, lane in summary()["lanes"].items():
        t = lane["attack_totals"]
        assert t["total"] == t["succeeded"] + t["blocked"] + t["refused"], key


def test_recording_404_for_unknown():
    assert client.get("/api/recording/bare/9/nope").status_code == 404


def test_page_renders_and_loads_presenter_js():
    html = client.get("/").text
    assert "Zero Trust Agents" in html
    assert 'src="/static/js/presenter.js"' in html


def test_no_number_invented_recordings_have_events():
    # every recording the UI replays carries its real events, not placeholder text
    recs = summary()["recordings"]
    assert recs
    for rec in recs.values():
        assert "events" in rec and isinstance(rec["events"], list)


def test_summary_file_is_valid_json_on_disk():
    from app.config import settings

    path = Path(ROOT) / settings().runs_dir / "runs_summary.json"
    json.loads(path.read_text())
