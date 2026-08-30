/**
 * Intelligent Knowledge Hub - Frontend Client Engine
 * Orchestrates Hybrid RAG queries, real-time observability telemetry,
 * and the active LLMOps Feedback & DPO Data Flywheel.
 */

document.addEventListener("DOMContentLoaded", () => {
  // State Management
  const state = {
    currentQuery: "",
    currentResponse: "",
    currentCitations: [],
    currentContext: [],
    lastQueryData: null,
    isSubmitting: false
  };

  // DOM Elements
  const systemStatusBadge = document.getElementById("system-status-badge");
  const systemStatusText = document.getElementById("system-status-text");
  const ragForm = document.getElementById("rag-query-form");
  const queryInput = document.getElementById("query-input");
  const topKSelect = document.getElementById("top-k-select");
  const submitBtn = document.getElementById("submit-btn");

  const responseCard = document.getElementById("response-card");
  const responseLoading = document.getElementById("response-loading");
  const answerContainer = document.getElementById("answer-container");
  const answerText = document.getElementById("answer-text");
  const citationsList = document.getElementById("citations-list");
  const activeModelName = document.getElementById("active-model-name");

  const btnLike = document.getElementById("btn-feedback-like");
  const btnDislike = document.getElementById("btn-feedback-dislike");
  const feedbackSuccessBanner = document.getElementById("feedback-success-banner");
  const feedbackDrawer = document.getElementById("feedback-drawer");
  const userCorrectionInput = document.getElementById("user-correction-input");
  const submitCorrectionBtn = document.getElementById("submit-correction-btn");
  const cancelCorrectionBtn = document.getElementById("cancel-correction-btn");

  const contextPassagesList = document.getElementById("context-passages-list");
  const retrievedCount = document.getElementById("retrieved-count");

  // Metrics Elements
  const metricRetrievalTime = document.getElementById("metric-retrieval-time");
  const metricLlmTime = document.getElementById("metric-llm-time");
  const metricTotalTime = document.getElementById("metric-total-time");
  const metricTokens = document.getElementById("metric-tokens");
  const metricTokensSub = document.getElementById("metric-tokens-sub");
  const metricQueryCost = document.getElementById("metric-query-cost");
  const costProgressBar = document.getElementById("cost-progress-bar");

  // Flywheel Elements
  const statGoldenCount = document.getElementById("stat-golden-count");
  const statDpoCount = document.getElementById("stat-dpo-count");
  const statTotalFeedback = document.getElementById("stat-total-feedback");
  const statSatisfactionRate = document.getElementById("stat-satisfaction-rate");
  const refreshStatsBtn = document.getElementById("refresh-stats-btn");

  // Sample Query Chips
  const sampleChips = document.querySelectorAll(".sample-chip");

  // Initialize
  checkSystemReadiness();
  fetchFeedbackStats();

  // -------------------------------------------------------------------------
  // Event Handlers
  // -------------------------------------------------------------------------

  // 1. Submit Query
  ragForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = queryInput.value.trim();
    if (!question || state.isSubmitting) return;

    const topK = parseInt(topKSelect.value, 10) || 3;
    await executeQuery(question, topK);
  });

  // 2. Sample Prompt Clicks
  sampleChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (prompt) {
        queryInput.value = prompt;
        queryInput.focus();
        executeQuery(prompt, parseInt(topKSelect.value, 10) || 3);
      }
    });
  });

  // 3. Positive Feedback (Like)
  btnLike.addEventListener("click", async () => {
    if (!state.currentResponse) return;
    btnLike.classList.add("active");
    btnDislike.classList.remove("active");
    btnLike.disabled = true;
    btnDislike.disabled = true;
    feedbackDrawer.classList.add("hidden");

    await sendFeedback({
      rating: "like",
      reason: null,
      user_correction: null
    });

    feedbackSuccessBanner.classList.remove("hidden");
  });

  // 4. Negative Feedback (Dislike / Suggest Correction)
  btnDislike.addEventListener("click", () => {
    if (!state.currentResponse) return;
    btnDislike.classList.add("active");
    btnLike.classList.remove("active");
    feedbackSuccessBanner.classList.add("hidden");
    feedbackDrawer.classList.remove("hidden");
    userCorrectionInput.focus();
  });

  // 5. Cancel Correction
  cancelCorrectionBtn.addEventListener("click", () => {
    feedbackDrawer.classList.add("hidden");
    btnDislike.classList.remove("active");
  });

  // 6. Submit Human Correction to DPO Dataset
  submitCorrectionBtn.addEventListener("click", async () => {
    const selectedReason = document.querySelector('input[name="feedback-reason"]:checked');
    const reasonText = selectedReason ? selectedReason.value : "Issue Reported";
    const correctionText = userCorrectionInput.value.trim();

    submitCorrectionBtn.disabled = true;
    submitCorrectionBtn.textContent = "Submitting DPO Pair...";

    await sendFeedback({
      rating: "dislike",
      reason: reasonText,
      user_correction: correctionText || null
    });

    feedbackDrawer.classList.add("hidden");
    btnLike.disabled = true;
    btnDislike.disabled = true;
    submitCorrectionBtn.disabled = false;
    submitCorrectionBtn.textContent = "Submit to DPO Dataset";

    // Show temporary confirmation
    feedbackSuccessBanner.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
      </svg>
      <div>
        <strong>Correction Saved!</strong> Added to DPO / SFT tuning set (<code>data/dpo_tuning_set.jsonl</code>) for alignment retraining.
      </div>
    `;
    feedbackSuccessBanner.classList.remove("hidden");
  });

  // 7. Refresh Stats
  refreshStatsBtn.addEventListener("click", () => {
    fetchFeedbackStats();
  });

  // -------------------------------------------------------------------------
  // Core Functions
  // -------------------------------------------------------------------------

  /**
   * Probes /health/ready to display real-time cluster readiness.
   */
  async function checkSystemReadiness() {
    try {
      const res = await fetch("/health/ready");
      if (res.ok) {
        const data = await res.json();
        systemStatusBadge.className = "status-pill status-ready";
        systemStatusText.textContent = `Live & Ready (${data.index_name || "kb-index"})`;
        if (data.chat_deployment) {
          activeModelName.textContent = data.chat_deployment;
        }
      } else {
        // Fallback probe to /health/live
        const liveRes = await fetch("/health/live");
        if (liveRes.ok) {
          systemStatusBadge.className = "status-pill status-ready";
          systemStatusText.textContent = "Online (App Service Live)";
        } else {
          systemStatusBadge.className = "status-pill status-error";
          systemStatusText.textContent = "Downstream Degraded";
        }
      }
    } catch {
      systemStatusBadge.className = "status-pill status-loading";
      systemStatusText.textContent = "Connecting to Azure...";
    }
  }

  /**
   * Executes RAG Query against /query endpoint.
   */
  async function executeQuery(question, topK) {
    state.isSubmitting = true;
    submitBtn.disabled = true;
    submitBtn.querySelector(".btn-text").textContent = "Synthesizing...";

    // Reset UI states
    responseCard.classList.remove("hidden");
    responseLoading.classList.remove("hidden");
    answerContainer.classList.add("hidden");
    feedbackSuccessBanner.classList.add("hidden");
    feedbackDrawer.classList.add("hidden");
    btnLike.classList.remove("active");
    btnDislike.classList.remove("active");
    btnLike.disabled = false;
    btnDislike.disabled = false;
    userCorrectionInput.value = "";

    const startTime = performance.now();

    try {
      const response = await fetch("/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: topK })
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Query failed." }));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      state.lastQueryData = data;
      state.currentQuery = question;
      state.currentResponse = data.answer;
      state.currentCitations = data.citations || [];
      state.currentContext = data.context || [];

      // Render Answer
      renderAnswer(data.answer);

      // Render Citations
      renderCitations(data.citations || []);

      // Render Context Passages
      renderContextPassages(data.context || []);

      // Update FinOps & Telemetry Metrics
      updateMetrics(data.metrics);

      responseLoading.classList.add("hidden");
      answerContainer.classList.remove("hidden");
    } catch (err) {
      console.error("Query Error:", err);
      responseLoading.classList.add("hidden");
      answerContainer.classList.remove("hidden");
      answerText.innerHTML = `
        <div style="color: #f87171; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); padding: 1rem; border-radius: 8px;">
          <strong>Error executing knowledge retrieval:</strong> ${escapeHtml(err.message)}
          <br><small style="color: #94a3b8; margin-top: 4px; display: inline-block;">Please verify Azure AI Search and Azure OpenAI endpoints or Entra ID credentials.</small>
        </div>
      `;
      citationsList.innerHTML = `<span style="color: #64748b; font-size: 0.75rem;">No citations available.</span>`;
      contextPassagesList.innerHTML = "";
      retrievedCount.textContent = "0";

      const elapsed = Math.round(performance.now() - startTime);
      metricTotalTime.textContent = `${elapsed} ms`;
    } finally {
      state.isSubmitting = false;
      submitBtn.disabled = false;
      submitBtn.querySelector(".btn-text").textContent = "Execute Query";
    }
  }

  /**
   * Formats and renders markdown answer.
   */
  function renderAnswer(rawAnswer) {
    if (!rawAnswer) {
      answerText.innerHTML = "<p>No answer text returned.</p>";
      return;
    }

    // Lightweight markdown parser for headers, bold, bullets, code, and linebreaks
    let formatted = escapeHtml(rawAnswer);

    // Code blocks ```code```
    formatted = formatted.replace(/```([\s\S]*?)```/g, (match, p1) => {
      return `<pre><code>${p1.trim()}</code></pre>`;
    });

    // Inline `code`
    formatted = formatted.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold **text**
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Italic *text*
    formatted = formatted.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Unordered lists
    const lines = formatted.split("\n");
    let inList = false;
    const processedLines = [];

    for (let line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        if (!inList) {
          processedLines.push("<ul>");
          inList = true;
        }
        processedLines.push(`<li>${trimmed.substring(2)}</li>`);
      } else if (/^\d+\.\s/.test(trimmed)) {
        if (!inList) {
          processedLines.push("<ol>");
          inList = true;
        }
        const itemContent = trimmed.replace(/^\d+\.\s/, "");
        processedLines.push(`<li>${itemContent}</li>`);
      } else {
        if (inList) {
          processedLines.push("</ul>");
          inList = false;
        }
        if (trimmed.length > 0) {
          processedLines.push(`<p>${trimmed}</p>`);
        }
      }
    }
    if (inList) processedLines.push("</ul>");

    answerText.innerHTML = processedLines.join("\n");
  }

  /**
   * Renders citation badges.
   */
  function renderCitations(citations) {
    citationsList.innerHTML = "";
    if (!citations || citations.length === 0) {
      citationsList.innerHTML = `<span style="color: #64748b; font-size: 0.75rem;">No direct citations returned.</span>`;
      return;
    }

    citations.forEach((cit) => {
      const badge = document.createElement("div");
      badge.className = "citation-badge";
      badge.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
        </svg>
        <span>${escapeHtml(cit.title)}</span>
        <span class="citation-chunk-id">[${escapeHtml(cit.chunk_id)}]</span>
      `;
      citationsList.appendChild(badge);
    });
  }

  /**
   * Renders collapsible context passages with search scores.
   */
  function renderContextPassages(context) {
    contextPassagesList.innerHTML = "";
    retrievedCount.textContent = context.length;

    if (!context || context.length === 0) {
      contextPassagesList.innerHTML = `<div style="color: #64748b; font-size: 0.75rem;">No context passages.</div>`;
      return;
    }

    context.forEach((doc, idx) => {
      const card = document.createElement("div");
      card.className = "passage-card";
      const scoreDisplay = doc.score !== null ? `Score: ${parseFloat(doc.score).toFixed(4)}` : "RRF Rank";
      card.innerHTML = `
        <div class="passage-meta">
          <span>#${idx + 1} &bull; ${escapeHtml(doc.title)}</span>
          <span>${scoreDisplay} &bull; ID: ${escapeHtml(doc.id)}</span>
        </div>
        <div class="passage-content">${escapeHtml(doc.content)}</div>
      `;
      contextPassagesList.appendChild(card);
    });
  }

  /**
   * Updates FinOps and Telemetry cards.
   */
  function updateMetrics(metrics) {
    if (!metrics) return;

    metricRetrievalTime.textContent = `${metrics.retrieval_latency_ms} ms`;
    metricLlmTime.textContent = `${metrics.llm_latency_ms} ms`;
    metricTotalTime.textContent = `${metrics.total_latency_ms} ms`;

    metricTokens.textContent = `${metrics.total_tokens} tokens`;
    metricTokensSub.textContent = `Prompt: ${metrics.prompt_tokens} | Comp: ${metrics.completion_tokens}`;

    metricQueryCost.textContent = metrics.formatted_cost || `$${metrics.estimated_cost_usd.toFixed(6)}`;

    // Scale cost bar relative to $0.001 benchmark
    const pct = Math.min(100, Math.max(8, (metrics.estimated_cost_usd / 0.0005) * 100));
    costProgressBar.style.width = `${pct}%`;
  }

  /**
   * Dispatches user feedback to /feedback endpoint.
   */
  async function sendFeedback(payload) {
    try {
      const body = {
        query: state.currentQuery,
        response: state.currentResponse,
        citations: state.currentCitations,
        retrieved_context: state.currentContext,
        rating: payload.rating,
        reason: payload.reason,
        user_correction: payload.user_correction
      };

      const res = await fetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      if (res.ok) {
        await fetchFeedbackStats();
      }
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    }
  }

  /**
   * Fetches latest LLMOps data flywheel counters.
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

  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
});
