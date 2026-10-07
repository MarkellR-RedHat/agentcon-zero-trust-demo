"""The README's results table must agree with the summary the app serves; a typed number may not drift."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_readme_table_matches_summary():
    from app.config import settings

    summary = json.loads((ROOT / settings().runs_dir / "runs_summary.json").read_text())
    readme = (ROOT / "README.md").read_text()
    rows = {
        "No gate": "bare",
        "Blunt content filter": "guarded-blunt",
        "Scoped policy": "guarded-scoped",
    }
    for label, lane in rows.items():
        m = re.search(rf"^\| {re.escape(label)} \| (\d+) / (\d+) \| (\d+) \| (\d+) \|", readme, re.M)
        assert m, f"README row missing for {label}"
        a = summary["lanes"][lane]["attack_totals"]
        assert (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))) == (
            a["succeeded"], a["total"], a["blocked"], a["refused"]), label
