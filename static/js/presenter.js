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
      const outcomes = new Set();
      for (const scenario of scenarios) {
        const rec = await getRecording(key, stageIdx, scenario);
        if (!rec) continue;
        await playRecording($(`#t-${key}`), rec, scenario);
        (rec.outcomes || []).forEach((o) => outcomes.add(o));
      }
      // The footer counts every run of this stage's scenarios in this lane (not only the one
      // transcript replayed above), straight from the summary, so n is visible.
      const tally = stageTally(key, stageIdx);
      const v = $(`#v-${key}`);
      if (stageIdx === 4) {
        v.className = "verdict " + (tally.PASS ? "PASS" : "BLOCKED");
        v.textContent = tally.PASS ? `Defender job done ${tally.PASS} of ${tally.n}` : "Defender job blocked";
      } else {
        v.className = "verdict " + (tally.FAIL ? "FAIL" : "BLOCKED");
        v.textContent = `${tally.FAIL} of ${tally.n} attacks reached the sandbox`;
      }
      const who = [];
      if (tally.BLOCKED) who.push(`${tally.BLOCKED} stopped by the gate`);
      if (tally.REFUSED) who.push(`${tally.REFUSED} refused by the model`);
      if (outcomes.size) who.push([...outcomes].join(" · "));
      $(`#o-${key}`).textContent = who.join(" · ");
    }
    $("#stageHint").textContent = "Press 2 for the scoreboard";
  }

  // Verdict counts for one lane and stage over all its attack (or defender) runs.
  function stageTally(laneKey, stage) {
    const st = (SUMMARY.lanes[laneKey] || {}).stages || {};
    const scen = (st[String(stage)] || {}).scenarios || {};
    const t = { FAIL: 0, BLOCKED: 0, REFUSED: 0, PASS: 0, n: 0 };
    Object.values(scen).forEach((v) => {
      if (v.kind !== "attack" && v.kind !== "defender") return;
      ["FAIL", "BLOCKED", "REFUSED", "PASS"].forEach((k) => { t[k] += v[k] || 0; t.n += v[k] || 0; });
    });
    return t;
  }

  // Honest-task and defender verdicts for a lane over all stages.
  function laneWork(laneKey) {
    const st = (SUMMARY.lanes[laneKey] || {}).stages || {};
    const w = { taskPass: 0, taskBlocked: 0, taskN: 0, defPass: 0, defN: 0 };
    Object.values(st).forEach((s) => Object.values(s.scenarios || {}).forEach((v) => {
      if (v.kind === "task") { w.taskPass += v.PASS || 0; w.taskBlocked += v.BLOCKED || 0; w.taskN += (v.PASS || 0) + (v.BLOCKED || 0) + (v.INCOMPLETE || 0); }
      if (v.kind === "defender") { w.defPass += v.PASS || 0; w.defN += (v.PASS || 0) + (v.BLOCKED || 0) + (v.REFUSED || 0) + (v.INCOMPLETE || 0); }
    }));
    return w;
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
      ["Attacks that reached the sandbox", (k) => { const l = SUMMARY.lanes[k].attack_totals;
        return `<span class="big ${l.succeeded ? "bad" : "good"}">${l.succeeded}</span> of ${l.total}`; }],
      ["Stopped by the gate", (k) => `${SUMMARY.lanes[k].attack_totals.blocked}`],
      ["Refused by the model on its own", (k) => `${SUMMARY.lanes[k].attack_totals.refused}`],
      ["Honest tasks the gate got in the way of", (k) => { const w = laneWork(k);
        return `<span class="big ${w.taskBlocked ? "bad" : "good"}">${w.taskBlocked}</span> of ${w.taskN}`; }],
      ["Defender's forensic job completed", (k) => { const w = laneWork(k);
        return `<span class="big ${w.defPass === w.defN ? "good" : "bad"}">${w.defPass}</span> of ${w.defN}`; }],
    ];
    rows.forEach(([label, fn]) => {
      grid.innerHTML += `<div class="cell">${label}</div>` +
        lanes.map((k) => `<div class="cell">${fn(k)}</div>`).join("");
    });
    const bare = SUMMARY.lanes.bare.attack_totals;
    const blunt = (SUMMARY.lanes["guarded-blunt"] || {}).attack_totals;
    const scoped = SUMMARY.lanes["guarded-scoped"].attack_totals;
    $("#scoreSub").textContent =
      `${SUMMARY.run.model} on ${SUMMARY.run.device || "a GPU"}, ${SUMMARY.run.runtime}, ${SUMMARY.run.date}. ` +
      `${bare.total / 7} runs per attack.`;
    $("#scoreTakeaway").innerHTML =
      `The model refused <span class="hl">${bare.refused} of ${bare.total}</span> attacks by itself and let ` +
      `<span class="hl">${bare.succeeded}</span> through. ` +
      (blunt ? `A content filter still let <span class="hl">${blunt.succeeded}</span> through. ` : "") +
      `The scoped policy let <span class="hl">${scoped.succeeded}</span> through.`;
  }

  // ---------- scene 3: paradox ----------
  async function renderParadox() {
    // Everything on this scene is measured: the defender's job in each lane, and what the blunt
    // filter did to honest work. The Hugging Face account is the told part, with its sources.
    const lanes = ["bare", "guarded-blunt", "guarded-scoped"].filter((k) => SUMMARY.lanes[k]);
    const def = lanes.map((k) => { const w = laneWork(k); return `<span class="vr ${w.defPass === w.defN ? "PASS" : "BLOCKED"}">${w.defPass} of ${w.defN}<small>${laneLabel(k)}</small></span>`; }).join("");
    const bluntW = laneWork("guarded-blunt");
    const bluntA = (SUMMARY.lanes["guarded-blunt"] || {}).attack_totals || { succeeded: 0, total: 0 };
    const scopedA = SUMMARY.lanes["guarded-scoped"].attack_totals;
    $("#paradox").innerHTML = `
      <div class="pcard story">
        <h3>July 2026: Hugging Face is breached by an autonomous agent</h3>
        <p>An AI agent moved through Hugging Face's dataset pipeline over a weekend, chaining 17,000+ actions across short-lived sandboxes. When the team started the log analysis, they first used frontier models behind commercial APIs. That did not work: the requests were blocked by the providers' safety guardrails, which cannot tell an incident responder from an attacker. They ran the forensics on an open-weight model on their own infrastructure and did in hours what would usually take days. Their advice: have a capable model you can run yourself, vetted and ready before the incident.</p>
        <p class="src">huggingface.co/blog/security-incident-july-2026 · openai.com/index/hugging-face-model-evaluation-security-incident</p>
      </div>
      <div class="pcard">
        <h3>Our defender's job, measured</h3>
        <p>Stage 4 asks the same open model, on our own slice, to read the incident logs and write up the beacons and payloads. It did the job every time, in every lane. A model you run yourself does not lock you out.</p>
        <div class="verdict-row">${def}</div>
      </div>
      <div class="pcard">
        <h3>What a content filter costs you</h3>
        <p>The blunt filter keys on how dangerous the bytes look. It let <b>${bluntA.succeeded} of ${bluntA.total}</b> attacks through (the ones that read like ordinary ops commands) and blocked <b>${bluntW.taskBlocked} of ${bluntW.taskN}</b> honest tasks (the status-page check, as off-list egress). The scoped policy let <b>${scopedA.succeeded}</b> attacks through and blocked no honest work.</p>
        <div class="verdict-row"><span class="vr PASS">scope<small>allow the task, deny the rest</small></span><span class="vr BLOCKED">content<small>guess from the bytes</small></span></div>
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
