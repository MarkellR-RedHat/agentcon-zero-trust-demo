# RUN-AGNTCON.md: the work-laptop run list

What this produces: the `runs/<date>-<tag>/` tree the app and slides read. Three lanes
(`bare`, `guarded blunt`, `guarded scoped`), four stages each, every attack three times at
temperature 0.7 and once at 0. Model: Qwen3.8-27B on one H200 via the cluster vLLM 0.24 image,
tool calling on. Nothing here touches a real system: the agent's tools act only on the sandbox
container, which holds fake data and cannot reach the network.

Fill in `NS=` with the project. Every command block is copy-paste and passes `bash -n`.

## What you need: one 71 GB MIG slice, nothing else

The whole run needs ONE `mig-3g.71gb` slice for the Qwen3.8-27B pod. The harness runs on the
laptop and carries its own in-process sandbox (fake files, fake sink, no network), so no sandbox
pod, no Job and no NetworkPolicy are needed for the run. The 35 GB slice fits only the INT4 build
(and ran eager in the PyTorch tests); the 18 GB slice fits nothing useful. `kubernetes/sandbox.yaml`
and `kubernetes/harness-job.yaml` are the optional in-cluster variant (Path B) and can be ignored.

## Phase 0: deploy the model

```bash
NS=markell-agentcon
oc project "$NS"

# the agent model (Qwen3.8-27B BF16 on one 71 GB slice, tool calling on)
oc apply -f kubernetes/isvc-qwen-agent.yaml
oc wait --for=condition=Ready "isvc/qwen-agent" --timeout=20m
```

Smoke-test that the model does tool calls and the sandbox answers:

```bash
oc port-forward "svc/qwen-agent-predictor" 18080:8080 >/tmp/pf-model.log 2>&1 &
sleep 5
curl -sS http://localhost:18080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen-agent","messages":[{"role":"user","content":"List the files in /opt/app"}],
       "tools":[{"type":"function","function":{"name":"list_directory","description":"list a dir",
       "parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}}],
       "tool_choice":"auto","max_tokens":128}' | python3 -m json.tool | head -40
```

A `tool_calls` entry naming `list_directory` means the parser works. If it answers in prose with
no tool call, re-check `--enable-auto-tool-choice --tool-call-parser qwen3_xml` on the ISVC (the
Oct 6 run showed Qwen3.8 needs `qwen3_xml`; `hermes` does not fire).

## Phase 1: run the three lanes

Three lanes: `bare` (no gate), `guarded blunt`, `guarded scoped`. Path A is the plan; Path B exists only if you would rather run inside the cluster.

### Path A (the one to use): run the harness on the laptop over a port-forward

The sandbox is in-process, so the only thing the laptop needs from the cluster is the model. The
`--device` flag labels every run record truthfully; the scoreboard and slides print it.

```bash
cd agentcon-zero-trust-demo
python3 -m venv .venv && .venv/bin/pip install -r requirements-harness.txt
oc port-forward svc/qwen-agent-predictor 18080:8080 >/tmp/pf-model.log 2>&1 &
sleep 5
export VLLM_ENDPOINT=http://localhost:18080/v1/chat/completions
export VLLM_MODEL=qwen-agent
OUT=runs/2026-10-09-qwen-r2
DEV="1 x 71 GB MIG slice (3g.71gb) of an H200"
REP=9   # 1 run at temperature 0 plus 9 at 0.7 = 10 per attack, so a rate on a slide has an honest n
PYTHONPATH=. .venv/bin/python -m harness.run --lane bare                   --out "$OUT" --tag qwen-r2 --device "$DEV" --repeat $REP
PYTHONPATH=. .venv/bin/python -m harness.run --lane guarded --policy blunt  --out "$OUT" --tag qwen-r2 --device "$DEV" --repeat $REP
PYTHONPATH=. .venv/bin/python -m harness.run --lane guarded --policy scoped --out "$OUT" --tag qwen-r2 --device "$DEV" --repeat $REP
```

Round 2 (this pass): about 280 conversations, 2 to 3 hours on the slice in eager mode. Round 1
(Oct 6, 106 runs at 4 per attack) is already imported; this round replaces it as the headline data
and round 1 stays in the repo as the first pass. Each line prints the verdict and the sandbox
effects as it goes, so a lane that looks wrong shows up immediately.

### Path B (optional): in-cluster Job with the sandbox pod

Needs `kubernetes/sandbox.yaml` applied first (the sandbox pod + NetworkPolicy) and the harness image published. One Job per lane:

```bash
# bare: no gate
oc apply -f kubernetes/harness-job.yaml
oc wait --for=condition=complete job/agent-harness-bare --timeout=30m
oc logs job/agent-harness-bare | tail -40

# guarded blunt and guarded scoped: same Job with the lane/policy args changed
for spec in "blunt guarded-blunt" "scoped guarded-scoped"; do
  set -- $spec
  oc get job "agent-harness-$2" >/dev/null 2>&1 && oc delete job "agent-harness-$2"
  oc create -f kubernetes/harness-job.yaml --dry-run=client -o json \
    | python3 - "$1" "$2" <<'PY' | oc apply -f -
import json, sys
policy, name = sys.argv[1], sys.argv[2]
job = json.load(sys.stdin)
job["metadata"]["name"] = f"agent-harness-{name}"
c = job["spec"]["template"]["spec"]["containers"][0]
c["args"] = ["python","-m","harness.run",f"--lane=guarded",f"--policy={policy}",
             "--stage=1","--stage=2","--stage=3","--stage=4",
             "--out=/runs/2026-10-09-qwen-r2",f"--tag=qwen-r2","--repeat=9"]
json.dump(job, sys.stdout)
PY
  oc wait --for=condition=complete "job/agent-harness-$2" --timeout=30m
done
```

Copy the run tree out of each Job's pod:

```bash
for name in bare guarded-blunt guarded-scoped; do
  pod=$(oc get pod -l "job-name=agent-harness-$name" -o name | head -1)
  oc cp "${pod#pod/}:/runs" "./runs" 2>/dev/null || true
done
ls -R runs/2026-10-09-qwen-r2 | head -40
```

## Phase 2: MLflow traces (for the screenshots in the guide)

If `MLFLOW_TRACKING_URI` was set, each run logged its spans. Grab a couple of trace screenshots
(one bare stage-3 attack, one scoped stage-4 forensic) for CONFERENCE_GUIDE.md. These are the only
screenshots; they must be real captures, never mock-ups.

## Phase 3: hand back

```bash
cd runs && zip -r ../results-agntcon-r2.zip 2026-10-09-qwen-r2 && cd ..
# plus: the two MLflow screenshots, and the model startup log:
oc logs "$(oc get pod -l serving.kserve.io/inferenceservice=qwen-agent -o name | head -1)" \
  > runs/2026-10-09-qwen-r2/qwen-agent-startup.txt
```

Send `results-agntcon-r2.zip` back. The app side folds it into `runs_summary.json`
(`python scripts/rescore_runs.py` then `build_runs_file.py` on runs/2026-10-09-qwen-r2) and the slides fill from the counts.

## If a lane looks wrong

- Every attack PASS in `guarded scoped`: the gate is not attached. Check the Job used
  `--lane=guarded --policy=scoped`, not `bare`.
- `forensic` BLOCKED in `guarded scoped`: the report write was denied. Confirm the scoped forensic
  policy allows writes under `/var/log/incident/` (it should PASS; only `blunt` should block it).
- The model answers in prose with no tool call: the tool parser flag is missing or the model is
  declining. Record that as a REFUSED verdict; it is a real and interesting result, not a failure
  of the harness.
