/**
 * Intelligent Knowledge Hub - Frontline CSR Conversational Client Engine
 * Orchestrates multi-turn chat stream interactions, real-time telemetry,
 * active diagnostic probes, and the active LLMOps Feedback & DPO Data Flywheel.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Conversational State Management
  const state = {
    conversationHistory: [],
    isSubmitting: false,
    sessionPromptCount: 0,
    sessionLatencies: []
  };

  // DOM Elements - Chat & Form
  const chatStream = document.getElementById("chat-stream");
  const ragForm = document.getElementById("rag-query-form");
  const queryInput = document.getElementById("query-input");
  const topKSelect = document.getElementById("top-k-select");
  const submitBtn = document.getElementById("submit-btn");
  const clearChatBtn = document.getElementById("clear-chat-btn");
  const sampleChips = document.querySelectorAll(".sample-chip");

  // DOM Elements - Probes & Status
  const systemStatusBadge = document.getElementById("system-status-badge");
  const systemStatusText = document.getElementById("system-status-text");
  const credentialStatusText = document.getElementById("credential-status-text");
  const activeModelName = document.getElementById("active-model-name");

  // DOM Elements - FinOps & Telemetry
  const metricRetrievalTime = document.getElementById("metric-retrieval-time");
  const metricLlmTime = document.getElementById("metric-llm-time");
  const metricTotalTime = document.getElementById("metric-total-time");
  const metricTokens = document.getElementById("metric-tokens");
  const metricTokensSub = document.getElementById("metric-tokens-sub");
  const metricQueryCost = document.getElementById("metric-query-cost");
  const costProgressBar = document.getElementById("cost-progress-bar");

  // DOM Elements - Flywheel
  const statGoldenCount = document.getElementById("stat-golden-count");
  const statDpoCount = document.getElementById("stat-dpo-count");
  const statTotalFeedback = document.getElementById("stat-total-feedback");
  const statSatisfactionRate = document.getElementById("stat-satisfaction-rate");
  const refreshStatsBtn = document.getElementById("refresh-stats-btn");

  // DOM Elements - Live KPIs
  const kpiFcrVal = document.getElementById("kpi-fcr-val");
  const kpiFcrBar = document.getElementById("kpi-fcr-bar");
  const kpiSearchVal = document.getElementById("kpi-search-val");
  const kpiSearchBar = document.getElementById("kpi-search-bar");
  const kpiZtVal = document.getElementById("kpi-zt-val");
  const kpiPromptsVal = document.getElementById("kpi-prompts-val");

  // Initial Data Load
  checkSystemReadiness();
  fetchFeedbackStats();
  fetchKpiMetrics();

  // Periodically check live probe to ensure status communicates reality
  setInterval(checkSystemReadiness, 60000);

  // -------------------------------------------------------------------------
  // Event Listeners
  // -------------------------------------------------------------------------

  // 1. Submit Prompt Form
  ragForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const promptText = queryInput.value.trim();
    if (!promptText || state.isSubmitting) return;

    const topK = parseInt(topKSelect.value, 10) || 3;
    await handleSendPrompt(promptText, topK);
  });

  // 2. Allow Shift+Enter for newline, Enter to submit
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ragForm.dispatchEvent(new Event("submit"));
    }
  });

  // 3. Conversational Suggestion Chips
  sampleChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (prompt) {
        queryInput.value = prompt;
        queryInput.focus();
        handleSendPrompt(prompt, parseInt(topKSelect.value, 10) || 3);
      }
    });
  });

  // 4. Clear Chat (New Caller Session)
  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
      state.conversationHistory = [];
      resetChatToWelcome();
      queryInput.value = "";
      queryInput.focus();
    });
  }

  // 5. Refresh Flywheel Stats Button
  if (refreshStatsBtn) {
    refreshStatsBtn.addEventListener("click", () => {
      fetchFeedbackStats();
      fetchKpiMetrics();
    });
  }

  // -------------------------------------------------------------------------
  // Conversational Core Handlers
  // -------------------------------------------------------------------------

  /**
   * Orchestrates multi-turn prompt sending and UI stream rendering.
   */
  async function handleSendPrompt(promptText, topK) {
    state.isSubmitting = true;
    submitBtn.disabled = true;
    submitBtn.querySelector(".btn-text").textContent = "Synthesizing...";

    // 1. Append User Bubble to Chat Stream
    appendUserMessage(promptText);

    // 2. Clear Input and Auto-scroll
    queryInput.value = "";
    scrollToBottom();

    // 3. Append Typing Indicator
    const typingIndicator = appendTypingIndicator();
    scrollToBottom();

    const startTime = performance.now();

    try {
      const response = await fetch("/prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: promptText,
          top_k: topK,
          history: state.conversationHistory
        })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Prompt failed." }));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();

      // Remove typing indicator
      typingIndicator.remove();

      // Append Assistant Response Bubble
      appendAssistantMessage(promptText, data);

      // Record in conversation history for multi-turn context
      state.conversationHistory.push({ role: "user", content: promptText });
      state.conversationHistory.push({ role: "assistant", content: data.answer });

      // Update session metrics
      state.sessionPromptCount += 1;
      state.sessionLatencies.push(data.metrics.total_latency_ms);

      // Update Sidebar Telemetry & Live KPIs
      updateTelemetrySidebar(data.metrics);
      fetchKpiMetrics();

      scrollToBottom();
    } catch (err) {
      console.error("Prompt Error:", err);
      typingIndicator.remove();

      appendErrorMessage(err.message || "Failed to retrieve knowledge response.");
      scrollToBottom();

      const elapsed = Math.round(performance.now() - startTime);
      metricTotalTime.textContent = `${elapsed} ms`;
    } finally {
      state.isSubmitting = false;
      submitBtn.disabled = false;
      submitBtn.querySelector(".btn-text").textContent = "Execute Prompt";
    }
  }

  /**
   * Appends user message bubble to chat stream.
   */
  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user-row";

    const nowStr = formatTime(new Date());

    row.innerHTML = `
      <div class="message-bubble user-bubble">
        <div class="bubble-header">
          <span>You</span> &bull; <span>${nowStr}</span>
        </div>
        <div class="bubble-body">${escapeHtml(text)}</div>
      </div>
    `;

    chatStream.appendChild(row);
  }

  /**
   * Appends animated typing indicator to chat stream.
   */
  function appendTypingIndicator() {
    const row = document.createElement("div");
    row.className = "message-row assistant-row typing-row";

    row.innerHTML = `
      <div class="message-avatar">⚡</div>
      <div class="typing-bubble">
        <div class="typing-dots">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
        <span>Searching knowledge base & synthesizing prompt response...</span>
      </div>
    `;

    chatStream.appendChild(row);
    return row;
  }

  /**
   * Appends assistant message bubble with collapsible citations, context drawer, and feedback flywheel.
   */
  function appendAssistantMessage(promptText, data) {
    const row = document.createElement("div");
    row.className = "message-row assistant-row";

    const nowStr = formatTime(new Date());
    const citations = data.citations || [];
    const context = data.context || [];
    const metrics = data.metrics || {};

    const formattedAnswer = renderMarkdown(data.answer);

    // Citations Accordion
    let citationsHtml = "";
    if (citations.length > 0) {
      const badges = citations
        .map(
          (c) => `
            <span class="citation-badge" title="Chunk: ${escapeHtml(c.chunk_id)}">
              📄 ${escapeHtml(c.title)}
              <span class="citation-chunk-id">[${escapeHtml(c.chunk_id)}]</span>
            </span>`
        )
        .join("");

      citationsHtml = `
        <details class="message-citations">
          <summary>
            <span>📎 Verified SOP Documents (${citations.length})</span>
          </summary>
          <div class="message-citations-list">${badges}</div>
        </details>
      `;
    }

    // Context Inspector Accordion
    let contextHtml = "";
    if (context.length > 0) {
      const cards = context
        .map(
          (doc, i) => `
            <div class="passage-card">
              <div class="passage-meta">
                <span>#${i + 1} &bull; ${escapeHtml(doc.title)}</span>
                <span>${doc.score ? "Score: " + parseFloat(doc.score).toFixed(4) : "RRF Match"}</span>
              </div>
              <div class="passage-content">${escapeHtml(doc.content)}</div>
            </div>`
        )
        .join("");

      contextHtml = `
        <details class="message-context">
          <summary>
            <span>🔍 View Retrieved Context Passages (${context.length})</span>
          </summary>
          <div class="message-context-list">${cards}</div>
        </details>
      `;
    }

    // Micro telemetry summary
    const microLatency = metrics.total_latency_ms ? `${metrics.total_latency_ms} ms` : "--";
    const microTokens = metrics.total_tokens ? `${metrics.total_tokens} tokens` : "--";
    const microCost = metrics.formatted_cost || "$0.000000";

    row.innerHTML = `
      <div class="message-avatar">⚡</div>
      <div class="message-bubble assistant-bubble">
        <div class="bubble-header">
          <span class="bubble-author">Knowledge Assistant</span>
          <span class="bubble-time">${nowStr}</span>
        </div>
        <div class="bubble-body">${formattedAnswer}</div>

        ${citationsHtml}
        ${contextHtml}

        <div class="message-footer-bar">
          <div class="message-micro-metrics">
            <span>⚡ ${microLatency}</span>
            <span>&bull;</span>
            <span>${microTokens}</span>
            <span>&bull;</span>
            <span>${microCost}</span>
          </div>

          <div class="message-feedback-actions">
            <button type="button" class="btn-thumb-small btn-msg-like" title="Mark as accurate (adds to Golden Benchmark Suite)">
              <span>👍</span> <span>Accurate</span>
            </button>
            <button type="button" class="btn-thumb-small btn-msg-dislike" title="Suggest correction (adds to DPO Alignment Set)">
              <span>👎</span> <span>Suggest Correction</span>
            </button>
          </div>
        </div>

        <div class="message-dpo-drawer hidden">
          <div class="drawer-header">
            <h4>Human-in-the-Loop Correction (DPO/SFT Dataset)</h4>
            <p>Tell us what was off so our active learning flywheel can improve future prompt responses:</p>
          </div>
          <div class="feedback-reasons-grid">
            <label class="reason-chip">
              <input type="radio" name="fb-reason-${nowStr}" value="Inaccurate Fact" checked>
              <span>Inaccurate Fact</span>
            </label>
            <label class="reason-chip">
              <input type="radio" name="fb-reason-${nowStr}" value="Missing Critical Context">
              <span>Missing Critical Context</span>
            </label>
            <label class="reason-chip">
              <input type="radio" name="fb-reason-${nowStr}" value="Wrong Document Cited">
              <span>Wrong Document Cited</span>
            </label>
            <label class="reason-chip">
              <input type="radio" name="fb-reason-${nowStr}" value="Confusing Tone / Other">
              <span>Confusing Tone / Other</span>
            </label>
          </div>
          <div class="correction-field">
            <label>Human Ground Truth / What should have been said:</label>
            <textarea class="msg-correction-input" rows="2" placeholder="Write the preferred exact plain-language answer..."></textarea>
          </div>
          <div class="drawer-actions">
            <button type="button" class="btn-secondary btn-cancel-dpo">Cancel</button>
            <button type="button" class="btn-accent btn-submit-dpo">Submit to DPO Dataset</button>
          </div>
        </div>
      </div>
    `;

    // Attach interactive feedback event listeners for this specific message bubble
    wireMessageFeedbackEvents(row, promptText, data);

    chatStream.appendChild(row);
  }

  /**
   * Attaches feedback flywheel listeners to a specific message bubble.
   */
  function wireMessageFeedbackEvents(row, promptText, data) {
    const btnLike = row.querySelector(".btn-msg-like");
    const btnDislike = row.querySelector(".btn-msg-dislike");
    const dpoDrawer = row.querySelector(".message-dpo-drawer");
    const btnCancel = row.querySelector(".btn-cancel-dpo");
    const btnSubmitDpo = row.querySelector(".btn-submit-dpo");
    const correctionInput = row.querySelector(".msg-correction-input");
    const footerBar = row.querySelector(".message-footer-bar");

    // Positive Feedback (Accurate)
    btnLike.addEventListener("click", async () => {
      btnLike.classList.add("active-like");
      btnDislike.classList.remove("active-dislike");
      btnLike.disabled = true;
      btnDislike.disabled = true;
      dpoDrawer.classList.add("hidden");

      await sendFeedbackRecord({
        prompt: promptText,
        response: data.answer,
        citations: data.citations || [],
        retrieved_context: data.context || [],
        rating: "like",
        reason: null,
        user_correction: null
      });

      const notice = document.createElement("div");
      notice.className = "feedback-saved-notice";
      notice.innerHTML = `<span>✓</span> <span>Recorded to Golden Evaluation benchmark suite (<code>golden_eval_set.jsonl</code>)</span>`;
      footerBar.after(notice);

      fetchFeedbackStats();
      fetchKpiMetrics();
    });

    // Negative Feedback (Suggest Correction)
    btnDislike.addEventListener("click", () => {
      btnDislike.classList.add("active-dislike");
      btnLike.classList.remove("active-like");
      dpoDrawer.classList.remove("hidden");
      correctionInput.focus();
      scrollToBottom();
    });

    // Cancel DPO Drawer
    btnCancel.addEventListener("click", () => {
      dpoDrawer.classList.add("hidden");
      btnDislike.classList.remove("active-dislike");
    });

    // Submit DPO Correction
    btnSubmitDpo.addEventListener("click", async () => {
      const selectedReasonEl = row.querySelector('input[type="radio"]:checked');
      const reasonVal = selectedReasonEl ? selectedReasonEl.value : "Issue Reported";
      const correctionVal = correctionInput.value.trim();

      btnSubmitDpo.disabled = true;
      btnSubmitDpo.textContent = "Submitting...";

      await sendFeedbackRecord({
        prompt: promptText,
        response: data.answer,
        citations: data.citations || [],
        retrieved_context: data.context || [],
        rating: "dislike",
        reason: reasonVal,
        user_correction: correctionVal || null
      });

      dpoDrawer.classList.add("hidden");
      btnLike.disabled = true;
      btnDislike.disabled = true;

      const notice = document.createElement("div");
      notice.className = "feedback-saved-notice";
      notice.innerHTML = `<span>✓</span> <span>Correction saved to DPO alignment dataset (<code>dpo_tuning_set.jsonl</code>)</span>`;
      footerBar.after(notice);

      fetchFeedbackStats();
      fetchKpiMetrics();
    });
  }

  /**
   * Appends error message bubble to chat stream.
   */
  function appendErrorMessage(msg) {
    const row = document.createElement("div");
    row.className = "message-row assistant-row";

    row.innerHTML = `
      <div class="message-avatar" style="background: linear-gradient(135deg, #ef4444, #b91c1c);">⚠️</div>
      <div class="message-bubble assistant-bubble" style="border-color: #fecaca; background: #fff5f5;">
        <div class="bubble-header">
          <span class="bubble-author" style="color: #dc2626;">System Notice</span>
          <span class="bubble-time">Live</span>
        </div>
        <div class="bubble-body" style="color: #b91c1c;">
          <p><strong>I had trouble retrieving information for that prompt:</strong></p>
          <p style="margin-top: 0.25rem;">${escapeHtml(msg)}</p>
          <p style="margin-top: 0.5rem; font-size: 0.8125rem; color: #7f1d1d;">Please check downstream connection to Azure AI Search or Azure OpenAI, or ask a supervisor for the standard operating procedure.</p>
        </div>
      </div>
    `;

    chatStream.appendChild(row);
  }

  /**
   * Resets chat stream to initial welcome message.
   */
  function resetChatToWelcome() {
    chatStream.innerHTML = `
      <div class="message-row assistant-row welcome-message">
        <div class="message-avatar">⚡</div>
        <div class="message-bubble assistant-bubble">
          <div class="bubble-header">
            <span class="bubble-author">Knowledge Assistant</span>
            <span class="bubble-time">New Session</span>
          </div>
          <div class="bubble-body">
            <p>Hello! 👋 I'm your frontline Knowledge Assistant. I'm here to help you quickly find the exact policy rules, caller verification steps, and verbatim scripts you need while on a call with a member.</p>
            <p style="margin-top: 0.5rem; color: var(--text-secondary);">Ask a question below in plain English, or tap one of the common caller prompts to get started:</p>
          </div>
        </div>
      </div>
    `;
    scrollToBottom();
  }

  /**
   * Smoothly scrolls chat stream container to the latest message.
   */
  function scrollToBottom() {
    requestAnimationFrame(() => {
      chatStream.scrollTop = chatStream.scrollHeight;
    });
  }

  // -------------------------------------------------------------------------
  // Probes, Telemetry & KPI Functions
  // -------------------------------------------------------------------------

  /**
   * Deep readiness probe against /health/ready communicating live status.
   */
  async function checkSystemReadiness() {
    try {
      const res = await fetch("/health/ready");
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        systemStatusBadge.className = "status-pill status-ready";
        systemStatusText.textContent = `Live & Ready (${data.index_name || "kb-index"})`;
        systemStatusBadge.title = `Azure AI Search (${data.index_name}) and Azure OpenAI (${data.chat_deployment}) are operational.`;
        if (data.chat_deployment) {
          activeModelName.textContent = data.chat_deployment;
        }
        if (data.auth_mode && credentialStatusText) {
          credentialStatusText.textContent = data.auth_mode;
        }
      } else {
        // Downstream unhealthy: Check if App Service process itself is live
        const liveRes = await fetch("/health/live");
        if (liveRes.ok) {
          systemStatusBadge.className = "status-pill status-error";
          systemStatusText.textContent = "Downstream Degraded";
          systemStatusBadge.title = "App Service process is running, but downstream Azure Search or OpenAI is unavailable or unauthenticated in current environment.";
          if (data.auth_mode && credentialStatusText) {
            credentialStatusText.textContent = data.auth_mode;
          }
        } else {
          systemStatusBadge.className = "status-pill status-error";
          systemStatusText.textContent = "Server Offline";
          systemStatusBadge.title = "App Service backend is unreachable.";
        }
      }
    } catch {
      systemStatusBadge.className = "status-pill status-loading";
      systemStatusText.textContent = "Connecting...";
      systemStatusBadge.title = "Attempting to reach backend probes.";
    }
  }

  /**
   * Fetches latest live operational KPIs from /metrics/kpis.
   */
  async function fetchKpiMetrics() {
    try {
      const res = await fetch("/metrics/kpis");
      if (res.ok) {
        const data = await res.json();
        if (kpiFcrVal) kpiFcrVal.textContent = `${data.first_contact_resolution_pct}% (Target: 85%)`;
        if (kpiFcrBar) kpiFcrBar.style.width = `${Math.min(100, data.first_contact_resolution_pct)}%`;

        if (kpiSearchVal) kpiSearchVal.textContent = `-${data.search_time_reduction_pct}% (Avg ${data.avg_latency_ms}ms)`;
        if (kpiSearchBar) kpiSearchBar.style.width = `${Math.min(100, data.search_time_reduction_pct)}%`;

        if (kpiZtVal) kpiZtVal.textContent = `${data.zero_trust_violations} (100% Secure)`;
        if (kpiPromptsVal) kpiPromptsVal.textContent = `${data.total_prompts_session} Prompts Executed`;

        if (data.auth_mode && credentialStatusText) {
          credentialStatusText.textContent = data.auth_mode;
        }
      }
    } catch (err) {
      console.warn("Could not load KPI metrics:", err);
    }
  }

  /**
   * Updates real-time FinOps & Telemetry sidebar cards.
   */
  function updateTelemetrySidebar(metrics) {
    if (!metrics) return;

    metricRetrievalTime.textContent = `${metrics.retrieval_latency_ms} ms`;
    metricLlmTime.textContent = `${metrics.llm_latency_ms} ms`;
    metricTotalTime.textContent = `${metrics.total_latency_ms} ms`;

    metricTokens.textContent = `${metrics.total_tokens} tokens`;
    metricTokensSub.textContent = `Prompt: ${metrics.prompt_tokens} | Comp: ${metrics.completion_tokens}`;

    metricQueryCost.textContent = metrics.formatted_cost || `$${metrics.estimated_cost_usd.toFixed(6)}`;

    const pct = Math.min(100, Math.max(8, (metrics.estimated_cost_usd / 0.0005) * 100));
    costProgressBar.style.width = `${pct}%`;
  }

  /**
   * Dispatches user feedback to /feedback endpoint.
   */
  async function sendFeedbackRecord(payload) {
    try {
      await fetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    }
  }

  /**
   * Fetches latest LLMOps data flywheel counters from /feedback/stats.
   */
  async function fetchFeedbackStats() {
    try {
      const res = await fetch("/feedback/stats");
      if (res.ok) {
        const data = await res.json();
        statGoldenCount.textContent = data.golden_eval_count;
        statDpoCount.textContent = data.dpo_pairs_count;
        statTotalFeedback.textContent = data.total_feedback;
        statSatisfactionRate.textContent = `${data.satisfaction_rate_pct}%`;
      }
    } catch (err) {
      console.warn("Could not load feedback stats:", err);
    }
  }

  // -------------------------------------------------------------------------
  // Helper Utilities
  // -------------------------------------------------------------------------

  /**
   * Formats a raw date to HH:MM AM/PM.
   */
  function formatTime(date) {
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;
    const minutesStr = minutes < 10 ? "0" + minutes : minutes;
    return `${hours}:${minutesStr} ${ampm}`;
  }

  /**
   * Lightweight markdown parser for bold, bullets, numbered lists, blockquotes, code.
   */
  function renderMarkdown(raw) {
    if (!raw) return "<p>No answer text returned.</p>";

    let text = escapeHtml(raw);

    // Code blocks
    text = text.replace(/```([\s\S]*?)```/g, (match, p1) => {
      return `<pre><code>${p1.trim()}</code></pre>`;
    });

    // Inline code
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold **text**
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Italic *text* or _text_
    text = text.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    text = text.replace(/_([^_]+)_/g, "<em>$1</em>");

    // Markdown Links [text](url)
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // Line-by-line parsing for headings, lists, horizontal rules, and blockquotes
    const lines = text.split("\n");
    let inUl = false;
    let inOl = false;
    const processed = [];

    for (const line of lines) {
      const trimmed = line.trim();

      if (!trimmed) {
        if (inUl) { processed.push("</ul>"); inUl = false; }
        if (inOl) { processed.push("</ol>"); inOl = false; }
        continue;
      }

      // Horizontal rules (---, ***, ___)
      if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
        if (inUl) { processed.push("</ul>"); inUl = false; }
        if (inOl) { processed.push("</ol>"); inOl = false; }
        processed.push("<hr class='chat-divider'>");
        continue;
      }

      // Headings: # through ###### (strip hashes and render as bold styled headings)
      const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
      if (headingMatch) {
        if (inUl) { processed.push("</ul>"); inUl = false; }
        if (inOl) { processed.push("</ol>"); inOl = false; }
        const level = headingMatch[1].length;
        const headingText = headingMatch[2].trim();
        const tag = level <= 2 ? "h3" : "h4";
        processed.push(`<${tag} class="chat-heading">${headingText}</${tag}>`);
        continue;
      }

      // Blockquotes
      if (trimmed.startsWith("&gt; ") || trimmed.startsWith("> ")) {
        if (inUl) { processed.push("</ul>"); inUl = false; }
        if (inOl) { processed.push("</ol>"); inOl = false; }
        const quoteContent = trimmed.replace(/^(&gt;|>)\s?/, "");
        processed.push(`<blockquote>${quoteContent}</blockquote>`);
        continue;
      }

      // Unordered lists (- or *)
      if (/^[-*]\s+/.test(trimmed)) {
        if (inOl) { processed.push("</ol>"); inOl = false; }
        if (!inUl) { processed.push("<ul>"); inUl = true; }
        processed.push(`<li>${trimmed.replace(/^[-*]\s+/, "")}</li>`);
        continue;
      }

      // Ordered lists (1. or 1))
      if (/^\d+[\.\)]\s+/.test(trimmed)) {
        if (inUl) { processed.push("</ul>"); inUl = false; }
        if (!inOl) { processed.push("<ol>"); inOl = true; }
        const itemContent = trimmed.replace(/^\d+[\.\)]\s+/, "");
        processed.push(`<li>${itemContent}</li>`);
        continue;
      }

      // Regular paragraph
      if (inUl) { processed.push("</ul>"); inUl = false; }
      if (inOl) { processed.push("</ol>"); inOl = false; }
      processed.push(`<p>${trimmed}</p>`);
    }

    if (inUl) processed.push("</ul>");
    if (inOl) processed.push("</ol>");

    return processed.join("\n");
  }

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }
});
