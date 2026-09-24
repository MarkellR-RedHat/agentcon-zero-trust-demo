from app.models import TraceSpan


def compute_risk_score(traces: list[dict], red_team_results: list[dict]) -> float:
    if not traces and not red_team_results:
        return 0.0

    risk = 0.0
    weights = {"safe": 0.0, "warning": 0.15, "danger": 0.4}

    for trace in traces:
        risk += weights.get(trace.get("risk_level", "safe"), 0.0)
        for child in trace.get("children", []):
            risk += weights.get(child.get("risk_level", "safe"), 0.0)

    for result in red_team_results:
        risk += result.get("risk_score", 0.0) * 0.5

    return min(risk, 1.0)


def risk_color(score: float) -> str:
    if score < 0.3:
        return "#00c853"
    elif score < 0.6:
        return "#ffd600"
    return "#ff1744"


def format_trace_for_display(trace: dict) -> dict:
    return {
        "id": trace.get("id", ""),
        "name": trace.get("name", ""),
        "tool": trace.get("tool"),
        "parameters": trace.get("parameters", {}),
        "result": trace.get("result", ""),
        "duration_ms": trace.get("duration_ms", 0),
        "risk_level": trace.get("risk_level", "safe"),
        "timestamp": trace.get("timestamp", ""),
        "children": [format_trace_for_display(c) for c in trace.get("children", [])],
    }
