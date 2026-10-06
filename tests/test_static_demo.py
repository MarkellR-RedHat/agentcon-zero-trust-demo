"""The static demo under demo/ must match a fresh build, so Pages never drifts from the app."""

from scripts import build_static_demo


def test_demo_is_current():
    stale = build_static_demo.stale()
    assert stale == [], f"demo/ is stale, run scripts/build_static_demo.py: {stale}"
