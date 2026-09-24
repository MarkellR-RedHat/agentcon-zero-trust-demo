# Zero Trust Agents: Red Teaming Your Way to Safe AI

Interactive demo for AGNTCon + MCPCon North America 2026. Walk through a zero trust approach to agent safety — start with an agent that has no tools and no access, then progressively grant capabilities while red teaming its behavior at each stage.

## Quick Start

```bash
./scripts/setup.sh
./scripts/run-local.sh
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## How It Works

The demo progresses through five stages:

| Stage | Access Level | What Happens |
|-------|-------------|--------------|
| 0 | Sandboxed | Chat only, no tools — agent can't do anything useful or harmful |
| 1 | File Access | Agent gets read/write/list tools — red team tests for credential theft |
| 2 | Web + File | Agent gets HTTP tools — red team tests for data exfiltration and SSRF |
| 3 | Full Access | Agent gets code execution — red team tests for reverse shells and backdoors |
| 4 | Guardrails Paradox | The Hugging Face incident — when safety mechanisms become the vulnerability |

Click buttons to grant access. Click "Run Red Team" to attack. Watch the risk score climb and traces light up.

## Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla HTML/CSS/JS
- **Agent**: vLLM + MCP (simulation mode by default)
- **Tracing**: MLflow-style trace visualization

## Demo Mode

The default mode is `simulation` — all agent interactions are pre-scripted for reliable demo execution. No GPU or external services needed.

For live mode with real vLLM + MCP endpoints, set `DEMO_MODE=live` in `.env`.

## Deployment

```bash
# Container
podman build -t zero-trust-agents-demo:latest .
podman run -p 8000:8000 zero-trust-agents-demo:latest

# OpenShift
oc apply -f kubernetes/
```

## Conference

**AGNTCon + MCPCon North America 2026**
October 22-23, San Jose McEnery Convention Center
