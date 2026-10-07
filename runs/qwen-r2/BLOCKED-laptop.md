# BLOCKED

## Step 2: port-forward command uses wrong service port (resolved)

### Command that failed

```bash
oc port-forward "svc/qwen-agent-predictor" 18080:8080 > runs/qwen-r2/port-forward.log 2>&1 &
```

### Exact error text

```
error: Service qwen-agent-predictor does not have a service port 8080
```

### What happened

The KServe-created service `qwen-agent-predictor` is headless (ClusterIP: None) with port 80 and targetPort 8080. The command in step 2 asks for service port 8080, which does not exist. Port-forwarding to service port 80 (`18080:80`) connects but hits the kube-rbac-proxy sidecar, not vLLM.

### Resolution

Port-forwarded directly to the pod on port 8080, which is where vLLM listens:

```bash
POD="$(oc get pod -l serving.kserve.io/inferenceservice=qwen-agent -o name | head -1)"
oc port-forward "$POD" 18080:8080 > runs/qwen-r2/port-forward.log 2>&1 &
```

The smoke test passed: `tool_calls` with `list_directory` returned. All subsequent steps use this pod port-forward in place of the service port-forward.

## Step 8: check_package.py reports run.date has two values

### Check that failed

```
FAIL  run.date is one real date in every file (saw ['2026-10-06', '2026-10-07'])
```

### What happened

The three lanes ran from 22:54 EDT on Oct 6 to 01:33 EDT on Oct 7. The harness defaults `--date` to `time.strftime("%Y-%m-%d")` (the system date when each lane starts). Steps 5-7 do not pass `--date`, so lane 1 files have `2026-10-06` and lanes 2-3 have files with both dates as runs crossed midnight. No run file was edited. The data is real; the checker expects a single date.

## Step 10: grep scrub hits /Users/[user] in PRIOR-STATE.txt

### Pattern that hit

```
grep -rIlE "/Users/|/home/[a-ce-z]|/home/d[a-df-z]" runs/
```

Printed: `runs/qwen-r2/PRIOR-STATE.txt`

### What happened

PRIOR-STATE.txt line 5 contains `/Users/[user]/.claude/shell-snapshots/…` from the `pgrep -fl` output captured at run start. The actual username was already replaced with `[user]` during sanitization; no real username appears. The grep pattern `/Users/` matches the sanitized form. The file was not edited further per the rule "do not edit the file yourself".
