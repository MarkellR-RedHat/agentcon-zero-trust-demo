"""Turn the agent's event list into spans, and export to MLflow when it is configured.

The run file always carries the raw events. When MLFLOW_TRACKING_URI is set, the same spans
are logged to MLflow so the demo can show the trace in the platform the abstract names. MLflow
is optional: with no server, nothing here raises, and the UI's own trace viewer reads the events
directly.
"""

from __future__ import annotations

import os

SPAN_KIND = {
    "model.call": "LLM",
    "tool.request": "TOOL",
    "gate.decision": "POLICY",
}


def to_spans(events: list[dict]) -> list[dict]:
    """A flat span list the UI trace viewer renders: one entry per model call, tool call and gate
    decision, with its parent and risk."""
    spans = []
    for e in events:
        if e["type"] in SPAN_KIND:
            spans.append(
                {
                    "span": e["span"],
                    "parent": e.get("parent"),
                    "kind": SPAN_KIND[e["type"]],
                    "t_ms": e["t_ms"],
                    "label": _label(e),
                    "risk": e.get("risk", "safe"),
                    "decision": e.get("decision"),
                }
            )
    return spans


def _label(e: dict) -> str:
    if e["type"] == "model.call":
        return "model call"
    if e["type"] == "tool.request":
        return f"{e['tool']}({_short_args(e.get('args', {}))})"
    if e["type"] == "gate.decision":
        return f"gate: {e['decision']} ({e['rule']})"
    return e["type"]


def _short_args(args: dict) -> str:
    for k in ("path", "url", "command", "code"):
        if k in args:
            v = str(args[k])
            return v if len(v) <= 48 else v[:45] + "..."
    return ""


def export_mlflow(run_meta: dict, lane: str, scenario: str, events: list[dict]) -> str | None:
    """Log the spans to MLflow if a tracking URI is set. Returns the run id, or None when MLflow
    is not configured or not installed."""
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not uri:
        return None
    try:
        import mlflow
    except ImportError:
        return None

    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "zero-trust-agents"))
    with mlflow.start_run(run_name=f"{lane}:{scenario}") as run:
        mlflow.set_tags(
            {"lane": lane, "scenario": scenario, "model": run_meta.get("model", ""),
             "runtime": run_meta.get("runtime", "")}
        )
        for span in to_spans(events):
            mlflow.log_metric(f"{span['kind'].lower()}_t_ms", span["t_ms"])
        return run.info.run_id
