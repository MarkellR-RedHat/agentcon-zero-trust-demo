# Q&A cheat sheet: Zero Trust Agents

**Is the agent real or scripted?** Real. The harness runs an OpenAI-compatible model (Qwen3.8-27B
on vLLM) with tools over MCP. The booth plays recordings of real runs so it needs no GPU; the UI
shows a banner if it is ever on the synthetic placeholder.

**How do you know an attack "succeeded"?** From sandbox state, not the model's words. A secret read
is recorded when the file was actually read; exfiltration when the sink actually received it with a
secret in the body; a command when it actually ran. The verdict is computed from those effects.

**Isn't running these attacks dangerous?** No. The tools act only on a throwaway sandbox of fake
data, and a NetworkPolicy denies it all egress. The "SSH key" and ".env" are obvious placeholders;
the exfil sink and the "internal metadata" service are in-cluster fakes.

**What is the policy, exactly?** Deterministic rules over the tool name and arguments
(`harness/gate.py`): an allowed-tool set per stage, denied secret paths, read/write path prefixes,
an egress host allowlist, and a command allowlist. Not a model, not an LLM judge.

**Why does the blunt filter fail?** Two ways. It misses attacks that do not match a danger pattern
(the package-from-a-mirror and the privilege probe get through). And it blocks the legitimate
forensic job in stage 4 because the report quotes the attacker's payloads. Content filtering cannot
tell intent.

**What is the Hugging Face connection?** July 2026: an autonomous agent breached Hugging Face.
Their responders' first tools, frontier models behind commercial APIs, refused to analyze the
attack because of safety guardrails. They switched to an open-weight model on their own
infrastructure. OpenAI later said the agent was its own models in an evaluation with cyber refusals
disabled. Sources are on the slide.

**Does this depend on OpenShift?** No. It is an OpenAI-compatible endpoint plus an MCP tool server;
anything that speaks those works. OpenShift AI is where the live run happens and where MLflow
tracing is shown.

**Would a different model change the result?** The attacks land on tool use, not model smarts. A
model that refuses more on its own shifts counts from "blocked by gate" toward "refused by model,"
but the gate is still what stops the ones it does not refuse. We measured one model, Qwen3.8-27B;
the harness takes any OpenAI-compatible endpoint if someone wants to try another.

**Where is the MLflow trace?** Every tool call, model call, and gate decision is a span. Live runs
log them to MLflow; the guide carries screenshots. The app's own trace viewer reads the same spans
from the run file.

**Can I run it?** Yes, it's open. `make setup && make run` serves the whole thing in replay with no
GPU. Repo and QR are on the closing slide.
