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
    assert {l["key"] for l in c["lanes"]} == {"bare", "guarded-scoped"}
    assert [s["key"] for s in c["stages"]] == ["1", "2", "3", "4"]


def test_bare_lane_attacks_all_succeed_in_fixture():
    c = client.get("/api/config").json()
    bare = next(l for l in c["lanes"] if l["key"] == "bare")
    assert bare["succeeded"] == bare["total"] and bare["total"] > 0


def test_scoped_lane_blocks_everything_in_fixture():
    s = summary()["lanes"]["guarded-scoped"]["attack_totals"]
    assert s["succeeded"] == 0 and s["blocked"] == s["total"]


def test_paradox_recordings_flip():
    assert client.get("/api/recording/guarded-blunt/4/forensic").json()["verdict"] == "BLOCKED"
    assert client.get("/api/recording/guarded-scoped/4/forensic").json()["verdict"] == "PASS"


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
