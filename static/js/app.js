(function () {
    const STAGE_NAMES = ['Sandboxed', 'File Access', 'Web + File Access', 'Full Access', 'The Guardrails Paradox'];
    const STAGE_TOOLS = {
        0: [],
        1: ['read_file', 'write_file', 'list_directory'],
        2: ['read_file', 'write_file', 'list_directory', 'http_get', 'http_post'],
        3: ['read_file', 'write_file', 'list_directory', 'http_get', 'http_post', 'execute_code', 'run_shell'],
        4: [],
    };

    let currentStage = 0;
    let ws = null;

    function initWebSocket() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${proto}//${location.host}/ws`);
        ws.onmessage = function (e) {
            const msg = JSON.parse(e.data);
            if (msg.type === 'stage_advance') handleStageAdvance(msg.data);
            else if (msg.type === 'red_team') handleRedTeam(msg.data);
            else if (msg.type === 'reset') handleReset(msg.data);
        };
        ws.onclose = function () {
            setTimeout(initWebSocket, 2000);
        };
    }

    function $(id) { return document.getElementById(id); }

    async function api(method, path, body) {
        const opts = { method, headers: { 'Content-Type': 'application/json' } };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(`/api${path}`, opts);
        return res.json();
    }

    // -- UI Updates --

    function updateRiskGauge(score, color) {
        const pct = Math.round(score * 100);
        const bar = $('risk-bar');
        const val = $('risk-value');
        bar.style.width = pct + '%';
        bar.style.backgroundColor = color;
        val.textContent = pct + '%';
        val.style.color = color;
    }

    function updateRiskBreakdown(breakdown) {
        ['file', 'web', 'code'].forEach(function (cat) {
            const score = breakdown[cat] || 0;
            const pct = Math.round(score * 100);
            const bar = $('risk-' + cat);
            const val = $('risk-' + cat + '-val');
            const color = score < 0.3 ? '#00c853' : score < 0.6 ? '#ffd600' : '#ff1744';
            bar.style.width = pct + '%';
            bar.style.backgroundColor = color;
            val.textContent = pct + '%';
            val.style.color = color;
        });
    }

    function updateStageIndicator(stage) {
        $('stage-number').textContent = stage;
        $('stage-name').textContent = STAGE_NAMES[stage] || '';

        document.querySelectorAll('.timeline-step').forEach(function (el) {
            const s = parseInt(el.dataset.stage);
            el.classList.remove('active', 'completed');
            if (s === stage) el.classList.add('active');
            else if (s < stage) el.classList.add('completed');
        });
    }

    function updateTools(stage) {
        const granted = STAGE_TOOLS[stage] || [];
        document.querySelectorAll('.tool-item').forEach(function (el) {
            const tool = el.dataset.tool;
            if (granted.includes(tool)) {
                el.classList.remove('locked');
                el.classList.add('granted');
                el.querySelector('.tool-status').textContent = 'granted';
            }
        });
    }

    function markToolsCompromised(traces) {
        var compromised = new Set();
        traces.forEach(function (t) {
            if (t.risk_level === 'danger' && t.tool) compromised.add(t.tool);
        });
        compromised.forEach(function (tool) {
            var el = document.querySelector('.tool-item[data-tool="' + tool + '"]');
            if (el) {
                el.classList.remove('granted');
                el.classList.add('compromised');
                el.querySelector('.tool-status').textContent = 'exploited';
            }
        });
    }

    function updateButtons(stage) {
        for (var i = 1; i <= 3; i++) {
            var btn = $('btn-stage' + i);
            if (i <= stage) {
                btn.disabled = true;
                btn.classList.add('used');
            } else if (i === stage + 1) {
                btn.disabled = false;
            }
        }
        $('btn-redteam').disabled = stage < 1 || stage > 3;
        $('btn-stage4').disabled = stage < 3;
    }

    // -- Conversation rendering --

    function clearConversation() {
        $('conversation').innerHTML = '';
    }

    function addTypingIndicator() {
        var div = document.createElement('div');
        div.className = 'typing-indicator';
        div.id = 'typing';
        div.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
        $('conversation').appendChild(div);
        scrollConversation();
    }

    function removeTypingIndicator() {
        var el = $('typing');
        if (el) el.remove();
    }

    function scrollConversation() {
        var conv = $('conversation');
        conv.scrollTop = conv.scrollHeight;
    }

    function addMessage(msg) {
        var div = document.createElement('div');

        if (msg.role === 'presenter') {
            div.className = 'msg msg-presenter';
            div.innerHTML = '<div class="msg-label">Presenter</div>' + escapeHtml(msg.content);
        } else if (msg.role === 'agent') {
            div.className = 'msg msg-agent';
            var html = '<div class="msg-label">Agent</div>' + escapeHtml(msg.content);
            if (msg.tool_call) {
                html += '<div class="msg-tool-call">' + escapeHtml(msg.tool_call) + '</div>';
            }
            div.innerHTML = html;
        } else if (msg.role === 'system') {
            div.className = 'msg msg-system';
            if (msg.content.startsWith('⚠')) div.classList.add('warning');
            div.textContent = msg.content;
        } else if (msg.role === 'tool_result') {
            div.className = 'msg msg-tool-result';
            div.textContent = msg.content;
        }

        $('conversation').appendChild(div);
        scrollConversation();
    }

    async function streamMessages(messages, delay) {
        delay = delay || 600;
        for (var i = 0; i < messages.length; i++) {
            addTypingIndicator();
            await sleep(delay);
            removeTypingIndicator();
            addMessage(messages[i]);
            await sleep(200);
        }
    }

    // -- Trace rendering --

    function clearTraces() {
        $('trace-viewer').innerHTML = '';
    }

    function addTraceSpan(trace, container) {
        container = container || $('trace-viewer');
        var div = document.createElement('div');
        div.className = 'trace-span';
        if (trace.risk_level === 'warning') div.classList.add('warning');
        if (trace.risk_level === 'danger') div.classList.add('danger');

        var html = '<div class="trace-header">';
        html += '<span class="trace-name">' + escapeHtml(trace.name) + '</span>';
        html += '<span class="trace-duration">' + trace.duration_ms + 'ms</span>';
        html += '</div>';
        if (trace.timestamp) {
            html += '<div class="trace-timestamp">' + formatTimestamp(trace.timestamp) + '</div>';
        }
        if (trace.tool) {
            html += '<div class="trace-tool">' + escapeHtml(trace.tool) + '</div>';
        }
        if (trace.parameters) {
            var paramStr = JSON.stringify(trace.parameters);
            if (paramStr.length > 120) paramStr = paramStr.substring(0, 117) + '...';
            html += '<div class="trace-params">' + escapeHtml(paramStr) + '</div>';
        }
        if (trace.result) {
            var resultClass = trace.risk_level === 'danger' ? 'trace-result danger' : 'trace-result';
            html += '<div class="' + resultClass + '">' + escapeHtml(trace.result) + '</div>';
        }

        div.innerHTML = html;

        if (trace.children && trace.children.length > 0) {
            var childContainer = document.createElement('div');
            childContainer.className = 'trace-children';
            trace.children.forEach(function (child) {
                addTraceSpan(child, childContainer);
            });
            div.appendChild(childContainer);
        }

        container.appendChild(div);
        $('trace-viewer').scrollTop = $('trace-viewer').scrollHeight;
    }

    async function streamTraces(traces, delay) {
        delay = delay || 400;
        for (var i = 0; i < traces.length; i++) {
            await sleep(delay);
            addTraceSpan(traces[i]);
        }
    }

    // -- Red team rendering --

    function addRedTeamCard(result) {
        var div = document.createElement('div');
        div.className = 'red-team-card';

        var verdictClass = result.verdict === 'FAIL' ? 'verdict-fail' : 'verdict-pass';
        var scorePct = Math.round(result.risk_score * 100);
        var scoreColor = result.risk_score < 0.3 ? '#00c853' : result.risk_score < 0.6 ? '#ffd600' : '#ff1744';

        var html = '<div class="red-team-header">';
        html += '<span class="red-team-type">' + escapeHtml(result.attack_type) + '</span>';
        html += '<span class="red-team-verdict ' + verdictClass + '">' + result.verdict + '</span>';
        html += '</div>';
        html += '<div class="red-team-prompt"><strong>Adversarial prompt:</strong><br>' + escapeHtml(result.prompt) + '</div>';
        html += '<div class="red-team-response"><strong>Agent response:</strong><br>' + escapeHtml(result.agent_response) + '</div>';
        html += '<div class="red-team-score">';
        html += '<span style="font-size:12px;color:' + scoreColor + '">Risk: ' + scorePct + '%</span>';
        html += '<div class="red-team-score-bar"><div class="red-team-score-fill" style="width:' + scorePct + '%;background:' + scoreColor + '"></div></div>';
        html += '</div>';
        html += '<div class="red-team-explanation">' + escapeHtml(result.explanation) + '</div>';

        div.innerHTML = html;
        $('conversation').appendChild(div);
        scrollConversation();
    }

    // -- Narrative rendering (Stage 4) --

    async function renderNarrative(data) {
        var narrative = data.narrative || [];
        var stats = data.key_stats || {};

        for (var i = 0; i < narrative.length; i++) {
            var item = narrative[i];
            addTypingIndicator();
            await sleep(1500);
            removeTypingIndicator();

            var div = document.createElement('div');
            div.className = 'narrative-card';

            if (item.role === 'takeaway') {
                div.innerHTML = '<div class="takeaway">' + escapeHtml(item.content) + '</div>';
            } else {
                div.innerHTML = '<div class="narrator">' + escapeHtml(item.content) + '</div>';
            }

            $('conversation').appendChild(div);
            scrollConversation();
        }

        await sleep(800);
        var statsDiv = document.createElement('div');
        statsDiv.className = 'narrative-card';
        statsDiv.innerHTML = '<div class="narrative-stats">' +
            '<div class="stat-card"><div class="stat-value">' + (stats.agents_with_no_safety_testing || '78%') + '</div><div class="stat-label">Agents with no safety testing</div></div>' +
            '<div class="stat-card"><div class="stat-value">' + (stats.avg_time_to_detect_agent_misuse || '12 days') + '</div><div class="stat-label">Avg time to detect misuse</div></div>' +
            '<div class="stat-card"><div class="stat-value">' + (stats.cost_of_ai_security_incident || '$4.2M') + '</div><div class="stat-label">Avg incident cost</div></div>' +
            '</div>';
        $('conversation').appendChild(statsDiv);
        scrollConversation();
    }

    // -- Event handlers --

    async function handleStageAdvance(data) {
        var stage = data.stage;
        currentStage = stage;
        updateStageIndicator(stage);
        updateTools(stage);
        updateButtons(stage);

        if (data.type === 'narrative') {
            await renderNarrative(data.data);
        } else if (data.conversation) {
            await streamMessages(data.conversation);
            if (data.traces) await streamTraces(data.traces);
        }

        updateRiskGauge(data.risk_score || 0, data.risk_color || '#00c853');
    }

    async function handleRedTeam(data) {
        var results = data.results || [];

        var sysMsg = document.createElement('div');
        sysMsg.className = 'msg msg-system warning';
        sysMsg.textContent = '🔴 Red Team Assessment — Stage ' + currentStage;
        $('conversation').appendChild(sysMsg);
        scrollConversation();

        for (var i = 0; i < results.length; i++) {
            await sleep(800);
            addRedTeamCard(results[i]);

            if (results[i].tool_calls) {
                for (var j = 0; j < results[i].tool_calls.length; j++) {
                    await sleep(300);
                    addTraceSpan(results[i].tool_calls[j]);
                }
                markToolsCompromised(results[i].tool_calls);
            }
        }

        updateRiskGauge(data.risk_score || 0, data.risk_color || '#ff1744');
        if (data.risk_breakdown) updateRiskBreakdown(data.risk_breakdown);
    }

    function handleReset(data) {
        currentStage = 0;
        updateStageIndicator(0);
        updateRiskGauge(0, '#00c853');
        updateRiskBreakdown({ file: 0, web: 0, code: 0 });
        updateButtons(0);

        document.querySelectorAll('.tool-item').forEach(function (el) {
            el.classList.remove('granted', 'compromised');
            el.classList.add('locked');
            el.querySelector('.tool-status').textContent = 'locked';
        });

        $('conversation').innerHTML =
            '<div class="welcome-message">' +
            '<h2>Zero Trust Agent Demo</h2>' +
            '<p>This agent starts with <strong>zero access</strong>. Grant tools progressively and red team its behavior at each stage.</p>' +
            '<p>Click <strong>Grant File Access</strong> to begin.</p>' +
            '</div>';

        clearTraces();
        $('trace-viewer').innerHTML = '<div class="trace-empty">No traces yet. Advance a stage to see agent activity.</div>';
    }

    // -- Button bindings --

    function bindButtons() {
        [1, 2, 3, 4].forEach(function (stage) {
            var btn = $('btn-stage' + stage);
            if (!btn) return;
            btn.addEventListener('click', async function () {
                btn.disabled = true;
                await api('POST', '/advance/' + stage);
            });
        });

        $('btn-redteam').addEventListener('click', async function () {
            this.disabled = true;
            await api('POST', '/red-team');
        });

        $('btn-reset').addEventListener('click', async function () {
            await api('POST', '/reset');
        });
    }

    // -- Helpers --

    function escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatTimestamp(ts) {
        try {
            var d = new Date(ts);
            return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 });
        } catch (e) {
            return ts;
        }
    }

    function sleep(ms) {
        return new Promise(function (resolve) { setTimeout(resolve, ms); });
    }

    // -- Init --

    document.addEventListener('DOMContentLoaded', function () {
        bindButtons();
        initWebSocket();

        api('GET', '/state').then(function (state) {
            if (state.stage > 0) {
                currentStage = state.stage;
                updateStageIndicator(state.stage);
                updateTools(state.stage);
                updateButtons(state.stage);
                updateRiskGauge(state.risk_score || 0, state.risk_color || '#00c853');
                if (state.risk_breakdown) updateRiskBreakdown(state.risk_breakdown);
            }
        });
    });
})();
