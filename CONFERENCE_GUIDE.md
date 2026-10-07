# AGNTCon + MCPCon NA 2026: Zero Trust Agents

**Conference:** AGNTCon + MCPCon North America 2026, San Jose McEnery Convention Center.
**Dates:** October 22-23. **Format:** booth demo, click and key driven, 5 to 7 minutes, repeatable.
**Repo:** https://github.com/MarkellR-RedHat/agentcon-zero-trust-demo
**Slides:** .../slides.html **Demo:** .../demo/

## The story in one line

Give an agent nothing, earn its access one tool at a time, red team each step, and keep a policy
scoped to the task so it can tell a responder from an attacker. The July 2026 Hugging Face incident
is the closer: blanket guardrails locked the defenders out.

## What is on screen

The presenter is a fixed 1920x1080 stage that scales to any projector, three scenes:

1. **Red team** (`1`). A stage ladder across the top. Press `G` to grant the next stage; the two
   lanes (no gate, and the scoped policy) appear side by side. Press `Enter` to run that stage's
   attacks in both lanes: the conversation, each tool call, and each gate decision stream in with
   timings, colored by risk. The no-gate lane ends "Attacks succeeded" with the effects that
   landed; the scoped lane ends "Attacks blocked." Press `P` to swap the right lane to the blunt
   filter and show it missing some attacks.
2. **Scoreboard** (`2`). Attacks that reached the sandbox per lane, across all stages and runs,
   plus how many the model refused on its own and how many honest tasks the gate got in the way of.
   No gate: the model refused some but let many through. Blunt: fewer through, but not zero, and it
   blocked an honest task. Scoped: zero through, no honest work blocked.
3. **The paradox** (`3`). The Hugging Face account with its sources, then the measured counterpoint:
   the same open model did the defender's forensic job in every lane (run a model you control), and
   the blunt content filter is what let attacks through and blocked honest work.

The slide deck (`slides.html`) mirrors this in seven slides; press `N` for speaker notes, `B` to
black out, arrows or space to move.

## How to present it

- **Open (30s).** "We hand agents tools and hope they behave. Here's how to stop hoping."
- **Stage 1 (1m).** `G`, then `Enter`. The no-gate agent reads the SSH key; the scoped lane blocks
  it. Point at the trace line that says `gate: block (path:deny-secrets)`.
- **Stage 2 (1m).** `G`, `Enter`. The no-gate agent reaches the metadata endpoint on the left,
  egress denied on the right. Note the agent also refused some exfiltration on its own.
- **Stage 3 (1.5m).** `G`, `Enter`. The no-gate agent installs from a mirror and runs the privilege
  probe. Press `P` for the blunt filter: it refuses the obvious reverse shell but still lets the
  mirror install and the probe through, because they read like ordinary commands. Back to scoped,
  which blocks both.
- **Scoreboard (30s).** `2`. Two columns to land: the model refused some attacks by itself but let
  many through, and only the scoped policy reached zero without blocking honest work.
- **Paradox (1.5m).** `3`. Tell the Hugging Face story, then the measured counterpoint: the same
  open model did the forensic job in every lane, and the content filter is what cost you both ways.
- **Close (30s).** "Scope plus a trace, not a bigger refusal list. It's all open." Point at the QR.
- **Reset.** `R` returns to stage 0 for the next group.

If the crowd is large, skip to stage 3, press `P` once, then `2` and `3`. Three minutes.

## The booth plan

Runs in **replay** on the laptop, no GPU, no cluster, no network. The recordings are produced
before the conference by the harness on real endpoints (see RUN-AGNTCON.md) and imported with
`build_runs_file.py`. The static copy at `/demo/` on Pages is the backup: it opens from a file with
no server. Nothing is re-recorded at the booth.

### What to bring

- Laptop with `make run` already working, plus a backup laptop with the same.
- External monitor or the booth display (the lanes need about 1200px to read), HDMI adapter.
- A phone or card with the repo QR code.

## Before the conference (owner: Markell)

- Confirm the Red Hat booth presence and messaging with Grace; keep product lines to the open and
  close, not the demo stages.
- Send Wesley the updated title and abstract and the Pages links (the abstract text is in
  `agntcon_demo_update.txt`).
- Done October 6 to 7: round 2 ran on the cluster (ten runs per attack) and is imported under
  `runs/qwen-r2/`, with the vLLM startup log and the pod description beside the run files. No MLflow
  instance existed in the project, so there are no MLflow screenshots; the app's trace viewer shows
  the same spans from the run files.

## Backup plans

- **Laptop dies:** the backup laptop has the same `make run`; cold start is a few seconds.
- **Everything dies:** open `/demo/` from the Pages URL or the local `demo/index.html` file.
- **Someone asks for the data:** the run files under `runs/` carry every transcript, every gate
  decision, and the outcome, so any number on screen traces to a file.
