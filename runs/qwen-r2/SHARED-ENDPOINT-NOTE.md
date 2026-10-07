# Shared endpoint during the scoped lane

Written on the Mac on October 7, 2026 from `timing.txt`, the run files' `summary.total_ms` and
`summary.ttft_ms`, and a note from the Asago work-laptop session.

Between about 00:45 and 01:40 ET on October 7 another session was sending diagnostic load (several
rounds of eight concurrent requests of about 4,000 tokens) to the same `qwen-agent` pod this round
was running on. The scoped lane ran from 00:33:23 to 01:33:31, so its last 47 run files (the end of
stage 2, all of stage 3, all of stage 4; the first 36 ran before 00:45) shared the pod with that load.

What that did and did not change, from the files:

- Every one of the 47 requests completed with a normal finish reason (`stop` or `tool_calls`) and a
  non-zero completion token count. No request failed, truncated or returned empty.
- Verdicts are read from sandbox state (which files were read, what reached the sink, what ran), not
  from timing, so the counts in `runs_summary.json` are unaffected.
- Timings in those 47 files are not comparable with the rest of the round: median request time 41 s
  against 16 s before 00:45, median first-token time 3.7 s against 2.6 s, one first-token wait of
  128 s (`guarded-scoped/stage4/forensic_t07_r7.json`). The demo makes no speed claim and never did,
  because the pod ran in eager mode; any pacing taken from these files should be read as "under
  someone else's load".
- The three scoped runs that ended at the 8-tool-round cap are privilege-probe runs and fall in this
  window; the cap is a count of tool rounds, not a timeout, so the load did not cause it.

The pod was deleted by this round's own last step (`oc delete isvc qwen-agent`) after the package was
built. Nothing in this folder was edited because of this note.
