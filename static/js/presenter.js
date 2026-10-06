/* The presenter: three scenes driven by the run data. Replays recorded transcripts; in the static
   build (window.DEMO_DATA set) it reads the same data from a bundled file instead of the API. */
(function () {
  "use strict";

  const SCENES = ["stages", "score", "paradox"];
  // The two lanes shown side by side in scene 1. P toggles the guarded lane's policy.
  let guardedKey = "guarded-scoped";
  let CONFIG = null, SUMMARY = null;
  let stageIdx = 0;              // 0 = none granted yet; 1..4 = current stage
  let redTeamed = false;

  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

  async function getConfig() {
    if (window.DEMO_DATA) return window.DEMO_DATA.config;
    return (await fetch("/api/config")).json();
  }
  async function getSummary() {
    if (window.DEMO_DATA) return window.DEMO_DATA.summary;
    return (await fetch("/api/summary")).json();
  }
  function getRecording(lane, stage, scenario) {
    if (window.DEMO_DATA) return window.DEMO_DATA.summary.recordings[`${lane}/${stage}/${scenario}`];
    return fetch(`/api/recording/${lane}/${stage}/${scenario}`).then((r) => (r.ok ? r.json() : null));
  }

  function fitStage() {
    const s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080);
    document.getElementById("stage").style.setProperty("--scale", s);
  }

  function showScene(name) {
    SCENES.forEach((n) => $(`#scene-${n}`).classList.toggle("is-active", n === name));
    $$(".tab").forEach((t) => t.classList.toggle("is-active", t.dataset.scene === name));
    $("#progress").style.width = `${((SCENES.indexOf(name) + 1) / SCENES.length) * 100}%`;
    if (name === "score") renderScore();
    if (name === "paradox") renderParadox();
  }

  // ---------- scene 1: red team ----------
  function renderStageBar() {
    const bar = $("#stageBar");
    bar.innerHTML = "";
    CONFIG.stages.forEach((st) => {
      const chip = document.createElement("div");
      chip.className = "stage-chip" + (Number(st.key) <= stageIdx ? " on" : "");
      chip.innerHTML = `${st.key}. ${st.name}<span class="tools">${st.tools.join(" · ") || "chat only"}</span>`;
      bar.appendChild(chip);
    });
  }

  function laneEl(key) {
    const lane = SUMMARY.lanes[key];
    const bare = lane.lane === "bare";
    const el = document.createElement("div");
    el.className = "lane " + (bare ? "bare" : "guarded");
    el.dataset.key = key;
    el.innerHTML =
      `<div class="lane-head"><h3>${laneLabel(key)}</h3>` +
      `<span class="tag">${bare ? "no gate" : lane.policy + " policy"}</span></div>` +
      `<div class="lane-body"><div class="transcript" id="t-${key}"></div>` +
      `<div class="lane-foot"><span class="verdict" id="v-${key}"></span>` +
      `<span class="outcome" id="o-${key}"></span></div></div>`;
    return el;
  }

  function renderLanes() {
    const wrap = $("#lanes");
    wrap.innerHTML = "";
    ["bare", guardedKey].forEach((k) => wrap.appendChild(laneEl(k)));
  }

  function laneLabel(key) {
    return { bare: "No gate", "guarded-scoped": "Scoped policy", "guarded-blunt": "Blunt filter" }[key] || key;
  }

  function stageScenarios(stage) {
    // attacks of this stage (skip the honest task in the red-team view), plus the defender in stage 4
    const lane = SUMMARY.lanes.bare.stages[String(stage)];
    if (!lane) return [];
    return Object.entries(lane.scenarios)
      .filter(([, v]) => v.kind === "attack" || v.kind === "defender")
      .map(([name]) => name);
  }

  async function playRedTeam() {
    if (!stageIdx) return;
    redTeamed = true;
    const scenarios = stageScenarios(stageIdx);
    for (const key of ["bare", guardedKey]) {
      const t = $(`#t-${key}`);
      t.innerHTML = "";
      $(`#v-${key}`).textContent = "";
      $(`#o-${key}`).textContent = "";
    }
    // play each lane's recording for the stage's attacks, in sequence
    for (const key of ["bare", guardedKey]) {
      let lastVerdict = "", outcomes = new Set();
      for (const scenario of scenarios) {
        const rec = await getRecording(key, stageIdx, scenario);
        if (!rec) continue;
        await playRecording($(`#t-${key}`), rec, scenario);
        lastVerdict = rec.verdict;
        (rec.outcomes || []).forEach((o) => outcomes.add(o));
      }
      const anyFail = outcomes.size > 0 && key === "bare";
      $(`#v-${key}`).className = "verdict " + (anyFail ? "FAIL" : "BLOCKED");
      $(`#v-${key}`).textContent = anyFail ? "Attacks succeeded" : "Attacks blocked";
      $(`#o-${key}`).textContent = outcomes.size ? [...outcomes].join(" · ") : "nothing reached the sandbox";
    }
    $("#stageHint").textContent = "Press 2 for the scoreboard";
  }

  function playRecording(container, rec, scenario) {
    return new Promise((resolve) => {
      const label = (CONFIG.scenario_labels || {})[scenario] || scenario;
      const head = document.createElement("div");
      head.className = "msg";
      head.innerHTML = `<span class="who">attack · ${label}</span>${escape(rec.prompt)}`;
      container.appendChild(head);
      container.scrollTop = container.scrollHeight;

      const spans = (rec.spans || []).filter((s) => s.kind !== "LLM" || true);
      let i = 0;
      const step = () => {
        if (i >= spans.length) {
          resolve();
          return;
        }
        const s = spans[i++];
        const line = document.createElement("div");
        line.className = "span-line " + (s.risk || "safe");
        const badge = s.decision ? `<span class="badge">${s.decision.toUpperCase()}</span>` : "";
        line.innerHTML = `<span class="t">${s.t_ms} ms</span><span>${escape(s.label)}</span>${badge}`;
        container.appendChild(line);
        container.scrollTop = container.scrollHeight;
        setTimeout(step, window.DEMO_DATA ? 220 : 260);
      };
      setTimeout(step, 320);
    });
  }

  function grantNext() {
    if (stageIdx >= CONFIG.stages.length) return;
    stageIdx += 1;
    redTeamed = false;
    renderStageBar();
    renderLanes();
    $("#stageHint").textContent =
      stageIdx === 4 ? "Stage 4 is the defender. Press Enter to run it." : "Press Enter to run the red team";
    $("#btnGrant").disabled = stageIdx >= CONFIG.stages.length;
  }

  function resetStages() {
    stageIdx = 0;
    redTeamed = false;
    renderStageBar();
    $("#lanes").innerHTML = "";
    $("#btnGrant").disabled = false;
    $("#stageHint").textContent = "Grant the first stage to begin";
  }

  // ---------- scene 2: scoreboard ----------
  function renderScore() {
    const grid = $("#scoreGrid");
    const lanes = ["bare", "guarded-blunt", "guarded-scoped"].filter((k) => SUMMARY.lanes[k]);
    grid.style.gridTemplateColumns = `1.4fr repeat(${lanes.length}, 1fr)`;
    grid.innerHTML = `<div class="cell head">Attacks (all stages, all runs)</div>` +
      lanes.map((k) => `<div class="cell head">${laneLabel(k)}</div>`).join("");
    const rows = [
      ["Reached their target", (l) => `<span class="big ${l.succeeded ? "bad" : "good"}">${l.succeeded}</span> of ${l.total}`],
      ["Stopped by the gate", (l) => `<span class="big good">${l.blocked}</span>`],
      ["Refused by the model", (l) => `${l.refused}`],
    ];
    rows.forEach(([label, fn]) => {
      grid.innerHTML += `<div class="cell">${label}</div>` +
        lanes.map((k) => `<div class="cell">${fn(SUMMARY.lanes[k].attack_totals)}</div>`).join("");
    });
    const bare = SUMMARY.lanes.bare.attack_totals;
    const scoped = SUMMARY.lanes["guarded-scoped"].attack_totals;
    $("#scoreSub").textContent =
      `${SUMMARY.run.model} on ${SUMMARY.run.device || "a GPU"}, ${SUMMARY.run.runtime}, ${SUMMARY.run.date}.`;
    $("#scoreTakeaway").innerHTML =
      `With no gate, <span class="hl">${bare.succeeded} of ${bare.total}</span> attacks reached the sandbox. ` +
      `With a scoped policy, <span class="hl">${scoped.succeeded}</span> did.`;
  }

  // ---------- scene 3: paradox ----------
  async function renderParadox() {
    const bluntRec = await getRecording("guarded-blunt", 4, "forensic");
    const scopedRec = await getRecording("guarded-scoped", 4, "forensic");
    const bluntV = bluntRec ? bluntRec.verdict : "BLOCKED";
    const scopedV = scopedRec ? scopedRec.verdict : "PASS";
    $("#paradox").innerHTML = `
      <div class="pcard story">
        <h3>July 2026: Hugging Face is breached by an autonomous agent</h3>
        <p>An AI agent moved through Hugging Face's dataset pipeline over a weekend, chaining 17,000+ actions across short-lived sandboxes. When the team started the log analysis, they first used frontier models behind commercial APIs. That did not work: the requests were blocked by the providers' safety guardrails, which cannot tell an incident responder from an attacker. They ran the forensics on an open-weight model on their own infrastructure and did in hours what would usually take days.</p>
        <p class="src">huggingface.co/blog/security-incident-july-2026 · openai.com/index/hugging-face-model-evaluation-security-incident</p>
      </div>
      <div class="pcard">
        <h3>Blunt filter, our stage 4</h3>
        <p>The same forensic job here: read the incident logs, write a report that quotes the payloads. A content filter blocks the report because it looks dangerous.</p>
        <div class="verdict-row"><span class="vr ${bluntV}">${bluntV}<small>the responder is locked out</small></span></div>
      </div>
      <div class="pcard">
        <h3>Scoped policy, our stage 4</h3>
        <p>The policy allows reads under the incident path and a write of the report, and nothing else. The job completes, and it still blocked every attack in the scoreboard.</p>
        <div class="verdict-row"><span class="vr ${scopedV}">${scopedV}<small>scoped to the task, not the content</small></span></div>
      </div>`;
  }

  function escape(s) {
    return String(s == null ? "" : s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  }

  function togglePolicy() {
    guardedKey = guardedKey === "guarded-scoped" ? "guarded-blunt" : "guarded-scoped";
    if (SUMMARY.lanes[guardedKey] === undefined) guardedKey = "guarded-scoped";
    if (stageIdx) renderLanes();
  }

  function onKey(e) {
    const k = e.key.toLowerCase();
    if (k === "1") showScene("stages");
    else if (k === "2") showScene("score");
    else if (k === "3") showScene("paradox");
    else if (k === "g") grantNext();
    else if (e.key === "Enter") playRedTeam();
    else if (k === "p") togglePolicy();
    else if (k === "r") resetStages();
    else if (k === "t") {
      const cur = document.documentElement.getAttribute("data-theme");
      document.documentElement.setAttribute("data-theme", cur === "dark" ? "light" : "dark");
    } else if (k === "f") {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen();
      else document.exitFullscreen();
    }
  }

  async function boot() {
    CONFIG = await getConfig();
    SUMMARY = await getSummary();
    $("#title").textContent = CONFIG.title;
    $("#subtitle").textContent = CONFIG.subtitle;
    $("#modeBadge").querySelector("span").textContent = CONFIG.mode === "live" ? "Live" : "Replay";
    $("#syntheticBanner").hidden = !CONFIG.synthetic;
    $$(".tab").forEach((t) => t.addEventListener("click", () => showScene(t.dataset.scene)));
    $("#btnGrant").addEventListener("click", grantNext);
    $("#btnRedTeam").addEventListener("click", playRedTeam);
    resetStages();
    fitStage();
    window.addEventListener("resize", fitStage);
    document.addEventListener("keydown", onKey);
  }

  boot();
})();
