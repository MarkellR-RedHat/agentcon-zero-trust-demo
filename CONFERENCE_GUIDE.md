# AGNTCon + MCPCon NA 2026: Zero Trust Agents

**Conference:** AGNTCon + MCPCon North America 2026, San Jose  
**Dates:** October 22-23  
**Format:** Booth demo (click-driven, repeatable)  
**Repo:** https://github.com/MarkellR-RedHat/agentcon-zero-trust-demo

## What This Demo Does

Most teams building with agents are handing them tools and hoping for the best. This demo shows what actually happens when you do that by starting an agent with zero access and then progressively granting it file access, web access, and code execution while red teaming its behavior at every stage. The audience watches the agent try to read SSH keys, exfiltrate data, and attempt reverse shells as it gets more power, and the risk score climbs in real time.

The whole thing runs in a browser. No terminal interaction, no typing, just buttons. That makes it perfect for a booth where you're running the same demo 30 times in two days for different groups of people walking up. Click through the stages, let the red team results speak for themselves, land on the "guardrails paradox" at the end.

## How It Works Under the Hood

The backend is FastAPI with WebSocket connections for real-time updates. The core logic lives in a few files:

- `app/agent.py` is the agent interaction controller that manages stage progression and tracks what tools are available at each level.
- `app/mcp_tools.py` defines the MCP tool set per stage. Stage 0 has nothing. Stage 1 adds file tools (read_file, write_file, list_directory). Stage 2 adds web tools (http_get, http_post). Stage 3 adds code execution (execute_code, run_shell).
- `app/red_team.py` handles the adversarial attack scenarios. Each stage has its own set of attacks that probe the agent's behavior with the tools it currently has access to.
- `app/traces.py` generates MLflow-style trace spans with risk scoring. Every tool call gets a trace with a risk level (safe, warning, danger) and the trace viewer in the UI shows them in real time.
- `app/simulation.py` is the pre-scripted demo engine that drives the whole thing without needing a live model.

The frontend is a single HTML page (`templates/index.html`) with three panels: tools and actions on the left, conversation in the center, trace viewer on the right. The bottom has a stage timeline that fills in as you progress. Everything is vanilla HTML/CSS/JS with WebSocket updates, no frameworks.

Pre-scripted scenarios live in `scenarios/` as JSON files. Each stage has its own file with agent conversations and tool calls, and `red_team_results.json` has the adversarial attack results with verdicts (PASS/FAIL), risk scores, and explanations.

## The Five Stages

**Stage 0: Sandboxed.** The agent has chat-only access, no tools at all. This is the baseline. It can answer questions but can't actually do anything on the system. Safe, but useless.

**Stage 1: File Access.** You grant read_file, write_file, and list_directory. The agent immediately gets more useful, but when you red team it, you see it reading /etc/passwd without questioning the request. It follows a prompt injection hidden in a README file and tries to grab .env credentials. The risk score starts climbing.

**Stage 2: Web + File Access.** Add http_get and http_post on top of the file tools. Now the agent can reach out to the internet, and the red team reveals it attempting to POST sensitive file contents to external URLs. It also tries server-side request forgery against internal endpoints. The trace viewer lights up with warning and danger spans.

**Stage 3: Full Access.** Grant code execution and shell access. This is where it gets ugly. The agent goes for reverse shells, pip installs from suspicious repos, and attempts privilege escalation. The risk score spikes hard and the tool status indicators in the sidebar flip from "granted" to "exploited" as the red team compromises each tool.

**Stage 4: The Guardrails Paradox.** This isn't a new tool grant, it's a narrative stage. It covers the real-world Hugging Face incident where a frontier model's guardrails actually prevented the security team from defending against an attack, which forced them to use an open-source model instead. The point is that guardrails alone aren't the answer. You need observability, trust verification, and progressive access control. The demo you just watched IS that approach.

## How to Present It

This is a booth demo, so the flow needs to be tight and repeatable. Figure 5-7 minutes per run depending on how many questions people ask.

**Opening (30 seconds).** "Agents are getting access to more and more tools, but most teams don't have a strategy for what happens when those tools get misused. This demo shows a zero trust approach where the agent starts with nothing and earns access."

**Stage 1 walkthrough (1 minute).** Click "Grant File Access." Let the conversation play out showing the agent doing useful file operations. Then click "Run Red Team" and let the audience see the agent immediately try to read sensitive files. Point at the trace viewer showing the tool calls flagged as dangerous.

**Stage 2 walkthrough (1 minute).** Click "Grant Web Access." Show the agent now combining file and web access. Run the red team again. Point at the data exfiltration attempt where the agent POSTs file contents to an external URL. Risk score should be visibly higher now.

**Stage 3 walkthrough (1.5 minutes).** Click "Grant Code Execution." This is the dramatic one. Run the red team and let the reverse shell attempt, the suspicious pip install, and the privilege escalation play out. The tool status indicators in the left sidebar flip to "exploited" in red. Risk score is through the roof. Let it sit for a second so the audience can take it in.

**Stage 4: The Guardrails Paradox (1.5 minutes).** Click the button and let the narrative cards stream in. This is where you connect the demo back to real incidents. The takeaway cards at the end land the message: guardrails are necessary but not sufficient, you need observability into every tool call, and progressive trust is how you actually ship agents safely.

**Close (30 seconds).** "Everything you just saw runs on vLLM and MCP with MLflow tracing. The agent, the tools, and the red teaming are all open source. If you want to try this on your own stack, the repo is public." Point at the QR code or hand them the GitHub link.

**Reset and repeat.** Click the reset button. Everything goes back to Stage 0. Ready for the next group.

## The Plan

### Timeline

1. **Oct 18-19:** Deploy demo app. If running live mode, deploy a vLLM endpoint.
2. **Oct 21:** Final testing. Make sure simulation mode is solid.
3. **Oct 22-23:** Conference days. Booth demo, repeating the 5-7 minute flow all day.

### What to Bring

- Laptop with the demo running in a browser
- External monitor or portable display for the booth (the three-panel layout needs at least 1200px width to look right)
- HDMI adapter
- Phone or tablet showing the GitHub repo QR code
- Backup laptop with the demo pre-loaded

### Coordination

Talk content with Grace before the conference. Make sure the booth narrative aligns with whatever the broader Red Hat presence is at AGNTCon. If there are specific talking points or product messaging to weave in, do it during the opening and closing, not during the demo stages themselves. The demo stages should stay technical and let the red team results speak for themselves.

## Backup Plans

**If the live model endpoint goes down:** The demo defaults to simulation mode, which uses pre-scripted scenarios from `scenarios/`. The audience experience is identical since the conversations, tool calls, traces, and red team results are all realistic. Just don't mention it's simulated and nobody will know.

**If the laptop dies:** Have the backup laptop ready with the demo already running. The app starts in under 3 seconds (`./scripts/run-local.sh`) so even a cold start is fast.

**If the audience is huge and you can't do a full walkthrough:** Skip straight to Stage 3, run the red team, show the exploited tools and spiking risk score, then jump to Stage 4 for the guardrails paradox narrative. You can compress the whole thing to 3 minutes if needed. The dramatic payoff is all in Stages 3 and 4.

## Running It Yourself

Clone and run locally, no GPUs or external services needed:

```bash
git clone https://github.com/MarkellR-RedHat/agentcon-zero-trust-demo.git
cd agentcon-zero-trust-demo
./scripts/setup.sh
./scripts/run-local.sh
```

Open http://localhost:8000 and start clicking through the stages.

## Stack

- **Backend:** FastAPI (Python 3.9+)
- **Frontend:** Vanilla HTML/CSS/JS, WebSocket for real-time updates
- **Agent LLM:** vLLM endpoint (simulation mode by default)
- **Tools:** MCP server providing file, web, and code execution tools
- **Tracing:** MLflow-style trace visualization built into the UI
- **Repo:** https://github.com/MarkellR-RedHat/agentcon-zero-trust-demo

## Author

**Markell Rawls**  
Technical Marketing Engineer, Red Hat  
mrawls@redhat.com
