# Zero Trust Agents: Red Teaming Your Way to Safe AI

Agents are getting more capable and more access, but most teams have no real strategy for making sure they behave. This demo walks through a zero trust approach to agent safety where you start with an agent that has nothing (no tools, no access) and then progressively grant capabilities while red teaming its behavior at each stage.

You'll see what happens when you give an agent file access and it immediately tries to read your SSH keys. You'll see what happens when you add web access and it attempts to exfiltrate data. And you'll see what happens when you hand it code execution and it goes for a reverse shell. The whole thing is visual, click-driven, and runs in your browser with zero setup.

Presented at **AGNTCon + MCPCon North America 2026**, October 22-23, San Jose.

## Try It Yourself

The whole demo runs locally in simulation mode. No GPUs, no clusters, no external services. Clone it, run one script, and you're up.

```bash
git clone https://github.com/MarkellR-RedHat/agentcon-zero-trust-demo.git
cd agentcon-zero-trust-demo
./scripts/setup.sh
./scripts/run-local.sh
```

Open [http://localhost:8000](http://localhost:8000) and start clicking. Everything in the demo is button-driven, so there's no terminal interaction needed once it's running.

The simulation mode uses pre-scripted agent interactions and traces that show realistic behavior at each access level. It's the same experience you'd see with a live model, just guaranteed to work every time.

## The Five Stages

The demo progresses through five stages. At each one you grant the agent more access and then red team it to see how it handles that power.

| Stage | What the agent gets | What red teaming reveals |
|-------|-------------------|------------------------|
| **0: Sandboxed** | Chat only, no tools | Agent can't do anything useful or harmful. This is your baseline. |
| **1: File Access** | read_file, write_file, list_directory | Agent reads /etc/passwd without questioning it. Follows a prompt injection hidden in a README to grab .env credentials. |
| **2: Web Access** | HTTP GET and POST on top of file tools | Agent attempts to POST sensitive data to external URLs. Tries server-side request forgery against internal endpoints. |
| **3: Code Execution** | execute_code, run_shell on top of everything else | Agent goes for reverse shells, pip installs from suspicious repos, and attempts privilege escalation. Risk score spikes. |
| **4: The Guardrails Paradox** | Narrative stage (no new tools) | Covers the real-world Hugging Face incident where a frontier model's guardrails actually prevented the security team from defending against an attack, forcing them to use an open-source alternative. The point here is that guardrails alone aren't enough. You need observability and trust verification. |

## Running With Real Models

If you want to connect a real vLLM endpoint instead of using simulation mode, update your `.env` file:

```bash
cp .env.example .env
```

Then set these values:

```env
DEMO_MODE=live

# Point to your vLLM instance
VLLM_ENDPOINT=http://your-vllm-host:8080/v1
VLLM_MODEL=meta-llama/Llama-3.3-70B-Instruct
VLLM_API_KEY=your-key-here

# MCP server for tool execution
MCP_SERVER_URL=http://your-mcp-host:9000
```

The demo flow works exactly the same in live mode. The difference is that agent responses come from a real model instead of pre-scripted scenarios, so you'll see actual model behavior when the red team prompts hit.

MLflow tracing is optional. If you have an MLflow instance running, point `MLFLOW_TRACKING_URI` at it and traces will be logged there in addition to showing up in the UI.

## Smaller GPU Option

You don't need H200s or even A100s to run this with a real model. The demo works with any vLLM-compatible endpoint, so smaller models run just fine.

For a single consumer GPU (A10, L4, T4, or even a 3090), try:

```env
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
```

Or if you want something even lighter:

```env
VLLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3
```

The demo behavior doesn't change based on model size. Simulation mode handles the interesting red team scenarios regardless, and in live mode any model that can follow instructions will show the same patterns of risky tool use when prompted adversarially. Bigger models might be slightly better at refusing dangerous requests on their own, which actually makes for an interesting comparison if you have access to multiple sizes.

## Stack

- **Backend**: FastAPI (Python 3.9+)
- **Frontend**: Vanilla HTML/CSS/JS, WebSocket for real-time updates
- **Agent LLM**: vLLM endpoint (simulation mode by default)
- **Tools**: MCP server providing file, web, and code execution tools
- **Tracing**: MLflow-style trace visualization built into the UI

## Project Structure

```
agentcon-zero-trust-demo/
├── app/
│   ├── main.py           # FastAPI app, WebSocket, API routes
│   ├── config.py         # Configuration and environment
│   ├── agent.py          # Agent interaction controller
│   ├── mcp_tools.py      # MCP tool definitions per stage
│   ├── red_team.py       # Red team attack scenarios
│   ├── simulation.py     # Pre-scripted demo engine
│   ├── traces.py         # Trace generation and risk scoring
│   └── models.py         # Data models
├── scenarios/            # Pre-scripted demo data (JSON)
│   ├── stage0_sandboxed.json
│   ├── stage1_file_access.json
│   ├── stage2_web_access.json
│   ├── stage3_code_execution.json
│   └── red_team_results.json
├── static/
│   ├── css/style.css
│   └── js/app.js
├── templates/
│   └── index.html        # Single-page demo UI
├── kubernetes/           # OpenShift/K8s deployment manifests
├── scripts/
│   ├── setup.sh          # One-time environment setup
│   └── run-local.sh      # Start the demo locally
├── Dockerfile
├── requirements.txt
└── .env.example
```

## API

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/` | GET | Demo UI |
| `/api/state` | GET | Current stage, risk score, traces |
| `/api/advance/{stage}` | POST | Grant tools for the next stage |
| `/api/red-team` | POST | Run red team attacks for current stage |
| `/api/reset` | POST | Reset everything back to Stage 0 |
| `/ws` | WebSocket | Real-time updates |
| `/health` | GET | Health check |

## Deployment

```bash
# Container build
podman build -t zero-trust-agents-demo:latest .
podman run -p 8000:8000 zero-trust-agents-demo:latest

# OpenShift
oc apply -f kubernetes/
```

## Author

**Markell Rawls**
Technical Marketing Engineer, Red Hat
mrawls@redhat.com

## License

MIT
