let profiles = {};
let chatSessions = {
    "learner_1": [],
    "learner_2": [],
    "learner_3": []
};
let selectedProfileId = "learner_1";

// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const goalInput = document.getElementById('goal-topic');
const runBtn = document.getElementById('btn-run-pipeline');
const profileGrid = document.getElementById('profile-grid');
const traceViewer = document.getElementById('trace-viewer');
const xaiCard = document.getElementById('xai-card');
const xaiBody = document.getElementById('xai-body');
const refreshTrace = document.getElementById('refresh-trace');

// Modal Elements
const profileModal = document.getElementById('profile-modal');
const editBtn = document.getElementById('btn-edit-profile');
const closeModal = document.getElementById('close-modal');
const profileForm = document.getElementById('profile-form');

// --- Initialization ---

async function init() {
    await fetchProfiles();
    renderProfiles();
    loadSession();
}

function loadSession() {
    chatMessages.innerHTML = '';
    const session = chatSessions[selectedProfileId] || [];
    if (session.length === 0) {
        addMessage(`Hello! I am your AI Knowledge Assistant. Tell me what topic you'd like to explore today.`, 'instructor', false);
    } else {
        session.forEach(msg => {
            const div = document.createElement('div');
            div.className = `message ${msg.sender}`;
            div.innerHTML = msg.html;
            chatMessages.appendChild(div);
        });
    }
    scrollToBottom();
}

async function fetchProfiles() {
    const res = await fetch('/profiles');
    profiles = await res.json();
}

function renderProfiles() {
    profileGrid.innerHTML = '';
    Object.values(profiles).forEach(p => {
        const div = document.createElement('div');
        div.className = `p-card ${p.learner_id === selectedProfileId ? 'active' : ''}`;
        div.innerHTML = `
            <h4>${p.name}</h4>
            <p>${p.level} • ${p.engagement} Engagement</p>
        `;
        div.onclick = () => {
            selectedProfileId = p.learner_id;
            renderProfiles();
            loadSession();
        };
        profileGrid.appendChild(div);
    });
}

// --- Chat Actions ---

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addMessage(text, sender = 'instructor', save = true) {
    const html = typeof text === 'string' ? `<p>${text.replace(/\n/g, '<br>')}</p>` : text;
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    div.innerHTML = html;
    chatMessages.appendChild(div);

    if (save) {
        if (!chatSessions[selectedProfileId]) chatSessions[selectedProfileId] = [];
        chatSessions[selectedProfileId].push({ sender, html });
    }

    scrollToBottom();
}

runBtn.onclick = async () => {
    const goal = goalInput.value.trim();
    if (!goal) return;

    addMessage(goal, 'user');
    goalInput.value = '';

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message instructor loading';
    loadingDiv.innerHTML = '<p>Orchestrating agents... Evaluating your request and building your path.</p>';
    chatMessages.appendChild(loadingDiv);
    scrollToBottom();

    try {
        const res = await fetch('/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ learner_id: selectedProfileId, goal })
        });
        const data = await res.json();

        chatMessages.removeChild(loadingDiv);
        handlePipelineResult(data);
        await loadTrace();
    } catch (err) {
        if (loadingDiv.parentNode) chatMessages.removeChild(loadingDiv);
        addMessage(`Error: ${err.message}`, 'instructor');
    }
};

function handlePipelineResult(data) {
    if (data.error) {
        addMessage(`Error: ${data.error}`, 'instructor');
        return;
    }

    const { content, xai, feedback } = data;
    let htmlContent = `<div class="ai-response">`;

    if (feedback) {
        const isFail = feedback.toUpperCase().includes('FAIL') || feedback.toUpperCase().includes('NOT QUITE');
        htmlContent += `<div class="${isFail ? 'fail-tag' : 'praise-tag'}">✨ ${feedback}</div>`;
    }

    if (data.is_progression && !content) {
        htmlContent += `</div>`;
        addMessage(htmlContent, 'instructor');
        return;
    }

    const safeFormat = (val) => {
        if (!val) return "";
        const str = typeof val === 'string' ? val : JSON.stringify(val);
        return str.replace(/\n/g, '<br>');
    };

    if (content?.explanation) {
        htmlContent += `<h3>Concept: ${data.next_step}</h3><p>${safeFormat(content.explanation)}</p>`;
    }
    if (content?.example) {
        htmlContent += `<h4>Example</h4><blockquote>${safeFormat(content.example)}</blockquote>`;
    }
    if (content?.quiz) {
        htmlContent += `<div class="quiz-box"><h4>Check your knowledge:</h4>`;
        content.quiz.forEach((q, i) => {
            htmlContent += `<div class="mcq-q">
                <p><strong>Q${i + 1}:</strong> ${q.question}</p>
                <ul class="mcq-list">
                    ${(q.options || []).map(opt => `<li>${opt}</li>`).join('')}
                </ul>
            </div>`;
        });
        htmlContent += `<p class="info-tag">Reply with your answers to proceed!</p></div>`;
    }

    if (content?.raw_content) {
        let raw = content.raw_content;
        if (raw.includes('```')) {
            raw = raw.replace(/```(json)?/g, '').replace(/```/g, '').trim();
        }

        const tryFixJson = (str) => {
            if (!str) return null;

            // Find JSON block boundaries
            const start = str.indexOf('{');
            const end = str.lastIndexOf('}') + 1;
            if (start === -1 || end === 0) return null;

            let jsonStr = str.substring(start, end);

            try { return JSON.parse(jsonStr); }
            catch (e) {
                try {
                    // Fix common single quote issues for keys and strings
                    const fixed = jsonStr
                        .replace(/'(\w+)':/g, '"$1":')       // Keys: 'key': -> "key":
                        .replace(/:\s*'([^']*)'/g, ': "$1"'); // Simple Values: : 'val' -> : "val"
                    return JSON.parse(fixed);
                } catch (e2) {
                    // Final fallback: try a broad replacement (riskier but sometimes works for simple cases)
                    try {
                        return JSON.parse(jsonStr.replace(/'/g, '"'));
                    } catch (e3) { return null; }
                }
            }
        };

        const parsed = tryFixJson(content?.raw_content || "");
        const displayDetails = parsed || content;

        if (displayDetails?.explanation) {
            htmlContent += `<h3>Concept: ${data.next_step}</h3><p>${safeFormat(displayDetails.explanation)}</p>`;
        }
        if (displayDetails?.example) {
            htmlContent += `<h4>Example</h4><blockquote>${safeFormat(displayDetails.example)}</blockquote>`;
        }
        if (displayDetails?.quiz) {
            htmlContent += `<div class="quiz-box"><h4>Check your knowledge:</h4>`;
            (displayDetails.quiz || []).forEach((q, i) => {
                htmlContent += `<div class="mcq-q">
                <p><strong>Q${i + 1}:</strong> ${q.question}</p>
                <ul class="mcq-list">
                    ${(q.options || []).map(opt => `<li>${opt}</li>`).join('')}
                </ul>
            </div>`;
            });
            htmlContent += `<p class="info-tag">Reply with your answers to proceed!</p></div>`;
        }

        if (!displayDetails?.explanation && content?.raw_content) {
            const isTechnical = content.raw_content.includes('{"') || content.raw_content.includes('":');
            const hasQuiz = !!(displayDetails?.quiz || content?.quiz);

            // RELAXED: If we have a quiz, allow the text through even if it's "technical"
            if (!isTechnical || hasQuiz) {
                // Also ensure the raw-text isn't added if it's identical to the explanation.
                if (content.raw_content.length > 5 && content.raw_content !== content.explanation) {
                    htmlContent += `<div class="raw-text">${content.raw_content.replace(/\n/g, '<br>')}</div>`;
                }
            } else {
                htmlContent += `<p class="info-tag">Preparing lesson details...</p>`;
            }
        }
    }

    htmlContent += `</div>`;
    addMessage(htmlContent, 'instructor');

    if (xai) {
        xaiCard.classList.remove('hidden');
        const firstRecKey = Object.keys(xai.recommendation_reasoning || {})[0];
        const reason = xai.recommendation_reasoning?.[firstRecKey]?.reason_text || 'Profile match detected.';
        const qa_passed = xai.qa_summary?.passed;

        xaiBody.innerHTML = `
            <div class="xai-summary">
                <div class="xai-section">
                    <label>Planned Learning Path</label>
                    <div class="path-visual">${(xai.path_planned || []).join(' ➔ ')}</div>
                </div>
                <div class="xai-section">
                    <label>Recommendation Reasoning</label>
                    <p>${reason}</p>
                </div>
                <div class="xai-section">
                    <label>QA Quality Gate</label>
                    <div class="qa-status ${qa_passed ? 'passed' : 'failed'}">
                        ${qa_passed === true ? 'Verified Content ✅' : qa_passed === false ? 'Corrected by Judge Agent ⚠️' : 'Skipped'}
                    </div>
                </div>
                <div class="xai-section">
                    <label>Explainable Insight</label>
                    <p class="xai-insight">${xai.counterfactual || 'Dynamic calibration active.'}</p>
                </div>
                <div class="xai-section">
                    <label>Agent System Contributions</label>
                    <div class="agent-contributions">
                        ${Object.entries(xai.agent_contributions || {}).map(([agent, contribution]) => `
                            <div class="agent-contrib-tag"><strong>${agent}:</strong> ${contribution}</div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }
}

async function loadTrace() {
    const res = await fetch('/trace');
    const { trace } = await res.json();

    const lines = trace.split('\n');
    let html = '<div class="trace-list">';
    lines.forEach((line, index) => {
        if (!line.trim()) return;
        const match = line.match(/\[(.*?)\] (.*?): (.*)/);
        if (match) {
            const [full, agent, action, details] = match;
            html += `
                <div class="trace-step expandable" onclick="this.classList.toggle('is-expanded')">
                    <div class="step-header">
                        <span class="step-agent">${agent}</span>
                        <span class="step-action">${action}</span>
                    </div>
                    <div class="step-details">
                        <pre>${details}</pre>
                    </div>
                </div>
            `;
        } else if (line.includes('---')) {
            html += `<div class="trace-meta">${line}</div>`;
        }
    });
    html += '</div>';
    traceViewer.innerHTML = html;
    traceViewer.scrollTop = traceViewer.scrollHeight;
}

refreshTrace.onclick = loadTrace;

// --- Modal Logic ---

editBtn.onclick = () => {
    const p = profiles[selectedProfileId];
    if (!p) return;
    document.getElementById('edit-id').value = p.learner_id;
    document.getElementById('edit-name').value = p.name;
    document.getElementById('edit-level').value = p.level;
    document.getElementById('edit-strengths').value = (p.strengths || []).join(', ');
    document.getElementById('edit-weaknesses').value = (p.weaknesses || []).join(', ');
    profileModal.classList.add('is-visible');
};

const hideModal = () => profileModal.classList.remove('is-visible');
closeModal.onclick = hideModal;

profileForm.onsubmit = async (e) => {
    e.preventDefault();
    const updated = {
        ...profiles[selectedProfileId],
        name: document.getElementById('edit-name').value,
        level: document.getElementById('edit-level').value,
        strengths: document.getElementById('edit-strengths').value.split(',').map(s => s.trim()).filter(s => s),
        weaknesses: document.getElementById('edit-weaknesses').value.split(',').map(s => s.trim()).filter(s => s)
    };
    await fetch('/profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
    });
    hideModal();
    await fetchProfiles();
    renderProfiles();
};

init();
