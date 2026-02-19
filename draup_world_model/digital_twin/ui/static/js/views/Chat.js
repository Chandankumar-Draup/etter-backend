/**
 * Chat View — Agentic chatbot for natural-language graph queries.
 *
 * Streams SSE events from /api/dt/chat and renders:
 *   status → step indicators, cypher → code block,
 *   data → table, insight → streaming text, suggest → chips.
 */

(function () {
    const { html, useState, useEffect, useRef, useCallback, api, fmt } = window.DT;

    // ── Starter prompts shown on empty chat ─────────────────────────

    const STARTERS = [
        "What is the overall workforce composition and automation readiness?",
        "Which roles have the highest automation potential and what tasks drive it?",
        "Compare headcount vs automation risk across all functions",
        "What emerging skills and technologies are reshaping the workforce?",
    ];

    // ── Step labels ─────────────────────────────────────────────────

    const STEP_LABELS = {
        thinking:  "Understanding question",
        querying:  "Querying graph",
        retrying:  "Retrying query",
        analyzing: "Analyzing results",
    };

    // ── Small helper components ─────────────────────────────────────

    function StepIndicator({ steps }) {
        if (!steps || steps.length === 0) return null;
        return html`
            <div class="flex flex-wrap items-center gap-2 mb-3">
                ${steps.map((s, i) => html`
                    <div key=${i} class="flex items-center gap-1.5 text-xs">
                        ${s.done ? html`
                            <svg class="w-3.5 h-3.5 text-positive-600" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                            </svg>
                        ` : html`
                            <svg class="w-3.5 h-3.5 text-brand-500 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                            </svg>
                        `}
                        <span class="${s.done ? 'text-gray-400' : 'text-gray-700 font-medium'}">${s.label}</span>
                    </div>
                `)}
            </div>
        `;
    }

    function CypherBlock({ cypher }) {
        const [open, setOpen] = useState(false);
        if (!cypher) return null;
        return html`
            <div class="mb-3">
                <button onClick=${() => setOpen(!open)}
                    class="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition">
                    <svg class="w-3 h-3 transition ${open ? 'rotate-90' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                    Cypher query
                </button>
                ${open && html`
                    <pre class="mt-1.5 p-3 bg-gray-900 text-green-400 rounded-lg text-xs overflow-x-auto font-mono leading-relaxed">${cypher}</pre>
                `}
            </div>
        `;
    }

    function DataTable({ data }) {
        if (!data || !data.rows || data.rows.length === 0) return null;
        const { columns, rows, count } = data;
        const showRows = rows.slice(0, 20);
        return html`
            <div class="mb-3 border border-gray-200 rounded-lg overflow-hidden">
                <div class="overflow-x-auto max-h-64">
                    <table class="w-full text-xs">
                        <thead class="bg-gray-50 sticky top-0">
                            <tr>
                                ${columns.map(c => html`
                                    <th key=${c} class="px-3 py-2 text-left font-semibold text-gray-600 whitespace-nowrap">${c}</th>
                                `)}
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-100">
                            ${showRows.map((row, i) => html`
                                <tr key=${i} class="hover:bg-gray-50">
                                    ${columns.map(c => html`
                                        <td key=${c} class="px-3 py-1.5 text-gray-800 whitespace-nowrap">
                                            ${typeof row[c] === "number" ? fmt.number(row[c]) : String(row[c] ?? "")}
                                        </td>
                                    `)}
                                </tr>
                            `)}
                        </tbody>
                    </table>
                </div>
                ${count > 20 ? html`
                    <div class="px-3 py-1.5 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
                        Showing 20 of ${count} rows
                    </div>
                ` : ''}
            </div>
        `;
    }

    // ── Message bubble ──────────────────────────────────────────────

    function MessageBubble({ msg, isStreaming }) {
        if (msg.role === "user") {
            return html`
                <div class="flex justify-end mb-4">
                    <div class="max-w-[75%] bg-brand-600 text-white px-4 py-2.5 rounded-2xl rounded-br-md text-sm">
                        ${msg.content}
                    </div>
                </div>
            `;
        }

        // Assistant message
        return html`
            <div class="flex justify-start mb-4">
                <div class="max-w-[85%] space-y-0">
                    <!-- Step indicators -->
                    ${msg.steps && msg.steps.length > 0 && html`
                        <${StepIndicator} steps=${msg.steps} />
                    `}

                    <!-- Cypher query (collapsible) -->
                    <${CypherBlock} cypher=${msg.cypher} />

                    <!-- Data table -->
                    <${DataTable} data=${msg.data} />

                    <!-- Insight text -->
                    ${msg.insight && html`
                        <div class="text-sm text-gray-800 leading-relaxed prose prose-sm max-w-none mb-3"
                             dangerouslySetInnerHTML=${{ __html: formatInsight(msg.insight) }}>
                        </div>
                    `}
                    ${isStreaming && !msg.insight && !msg.error && html`
                        <div class="text-sm text-gray-400 flex items-center gap-2">
                            <span class="inline-block w-1.5 h-4 bg-brand-500 rounded-full animate-pulse"></span>
                        </div>
                    `}

                    <!-- Error -->
                    ${msg.error && html`
                        <div class="text-sm text-negative-600 bg-negative-50 border border-negative-200 rounded-lg px-3 py-2 mb-3">
                            ${msg.error}
                        </div>
                    `}

                    <!-- Suggestions -->
                    ${msg.suggestions && msg.suggestions.length > 0 && html`
                        <div class="flex flex-wrap gap-1.5 mt-2">
                            ${msg.suggestions.map(s => html`
                                <button key=${s}
                                    onClick=${() => msg.onSuggest && msg.onSuggest(s)}
                                    class="text-xs px-3 py-1.5 rounded-full border border-brand-200 text-brand-700 bg-brand-50 hover:bg-brand-100 transition">
                                    ${s}
                                </button>
                            `)}
                        </div>
                    `}

                    <!-- Timing -->
                    ${msg.time_ms != null && html`
                        <div class="text-[10px] text-gray-400 mt-1.5">${(msg.time_ms / 1000).toFixed(1)}s</div>
                    `}
                </div>
            </div>
        `;
    }

    // ── Markdown-light formatter for insights ───────────────────────

    function formatInsight(text) {
        if (!text) return "";
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, "<br/>");
    }

    // ── Main Chat Component ─────────────────────────────────────────

    function Chat({ onNavigate }) {
        const [messages, setMessages] = useState([]);
        const [input, setInput] = useState("");
        const [streaming, setStreaming] = useState(false);
        const messagesEndRef = useRef(null);
        const inputRef = useRef(null);
        const abortRef = useRef(null);

        // Auto-scroll to bottom on new messages
        useEffect(() => {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }, [messages]);

        // Focus input on mount
        useEffect(() => {
            inputRef.current?.focus();
        }, []);

        const sendMessage = useCallback(async (text) => {
            const msg = (text || input).trim();
            if (!msg || streaming) return;

            setInput("");
            setStreaming(true);

            // Add user message
            const userMsg = { role: "user", content: msg };

            // Build history for API (exclude UI-only fields)
            const apiHistory = messages.map(m => {
                if (m.role === "user") return { role: "user", content: m.content };
                return {
                    role: "assistant",
                    content: m.insight || "",
                    cypher: m.cypher || null,
                    data: m.data ? { count: m.data.count } : null,
                    insight: m.insight || "",
                };
            });

            // Add placeholder assistant message
            const assistantMsg = {
                role: "assistant",
                steps: [],
                cypher: null,
                data: null,
                insight: "",
                error: null,
                suggestions: null,
                time_ms: null,
            };

            setMessages(prev => [...prev, userMsg, assistantMsg]);
            const assistantIdx = messages.length + 1; // index of the assistant message

            try {
                const controller = new AbortController();
                abortRef.current = controller;

                const response = await fetch("/api/dt/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: msg, history: apiHistory }),
                    signal: controller.signal,
                });

                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.error || response.statusText);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const parts = buffer.split("\n\n");
                    buffer = parts.pop() || "";

                    for (const part of parts) {
                        if (!part.startsWith("data: ")) continue;
                        let event;
                        try {
                            event = JSON.parse(part.slice(6));
                        } catch { continue; }

                        // Update the assistant message in-place
                        setMessages(prev => {
                            const updated = [...prev];
                            const am = { ...updated[assistantIdx] };

                            switch (event.type) {
                                case "status": {
                                    // Mark previous steps as done, add new one
                                    const steps = (am.steps || []).map(s => ({ ...s, done: true }));
                                    const label = STEP_LABELS[event.step] || event.content || event.step;
                                    steps.push({ label, done: false });
                                    am.steps = steps;
                                    break;
                                }
                                case "cypher":
                                    am.cypher = event.content;
                                    break;
                                case "data":
                                    am.data = event.content;
                                    break;
                                case "insight":
                                    am.insight = (am.insight || "") + event.content;
                                    break;
                                case "suggest":
                                    am.suggestions = event.content;
                                    break;
                                case "error":
                                    am.error = event.content;
                                    break;
                                case "done":
                                    am.time_ms = event.time_ms;
                                    // Mark all steps done
                                    am.steps = (am.steps || []).map(s => ({ ...s, done: true }));
                                    break;
                            }

                            updated[assistantIdx] = am;
                            return updated;
                        });
                    }
                }
            } catch (e) {
                if (e.name !== "AbortError") {
                    setMessages(prev => {
                        const updated = [...prev];
                        if (updated[assistantIdx]) {
                            updated[assistantIdx] = { ...updated[assistantIdx], error: e.message };
                        }
                        return updated;
                    });
                }
            } finally {
                setStreaming(false);
                abortRef.current = null;
                inputRef.current?.focus();
            }
        }, [input, streaming, messages]);

        const handleKeyDown = useCallback((e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }, [sendMessage]);

        const clearChat = useCallback(() => {
            if (streaming && abortRef.current) {
                abortRef.current.abort();
            }
            setMessages([]);
            setStreaming(false);
            setInput("");
        }, [streaming]);

        // Inject onSuggest callback into the last assistant message
        const displayMessages = messages.map((m, i) => {
            if (m.role === "assistant" && m.suggestions && i === messages.length - 1) {
                return { ...m, onSuggest: (q) => sendMessage(q) };
            }
            return m;
        });

        const isEmpty = messages.length === 0;

        return html`
            <div class="fade-in flex flex-col" style=${{ height: "calc(100vh - 120px)" }}>

                <!-- Header -->
                <div class="flex items-center justify-between mb-4 flex-shrink-0">
                    <div>
                        <h1 class="text-2xl font-bold text-gray-900">Workforce Assistant</h1>
                        <p class="text-sm text-gray-500">Ask questions about your Workforce Twin</p>
                    </div>
                    ${messages.length > 0 && html`
                        <button onClick=${clearChat}
                            class="text-xs text-gray-500 hover:text-gray-700 px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 transition">
                            New chat
                        </button>
                    `}
                </div>

                <!-- Messages area -->
                <div class="flex-1 overflow-y-auto min-h-0 px-1 pb-4">
                    ${isEmpty ? html`
                        <!-- Empty state with starters -->
                        <div class="flex flex-col items-center justify-center h-full text-center">
                            <div class="w-14 h-14 rounded-2xl bg-brand-100 flex items-center justify-center mb-4">
                                <svg class="w-7 h-7 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                                        d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
                                </svg>
                            </div>
                            <h2 class="text-lg font-semibold text-gray-900 mb-1">Ask anything about your workforce</h2>
                            <p class="text-sm text-gray-500 mb-6 max-w-md">
                                I'll query the Workforce Twin and give you data-driven insights.
                                Try one of these to get started:
                            </p>
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg">
                                ${STARTERS.map(q => html`
                                    <button key=${q}
                                        onClick=${() => sendMessage(q)}
                                        class="text-left text-sm px-4 py-3 rounded-xl border border-gray-200 hover:border-brand-300 hover:bg-brand-50 transition text-gray-700">
                                        ${q}
                                    </button>
                                `)}
                            </div>
                        </div>
                    ` : html`
                        ${displayMessages.map((m, i) => html`
                            <${MessageBubble}
                                key=${i}
                                msg=${m}
                                isStreaming=${streaming && i === displayMessages.length - 1 && m.role === "assistant"}
                            />
                        `)}
                        <div ref=${messagesEndRef}></div>
                    `}
                </div>

                <!-- Input bar -->
                <div class="flex-shrink-0 border-t border-gray-200 bg-white pt-3">
                    <div class="flex items-center gap-3">
                        <input
                            ref=${inputRef}
                            type="text"
                            value=${input}
                            onInput=${e => setInput(e.target.value)}
                            onKeyDown=${handleKeyDown}
                            placeholder="Ask about roles, skills, automation, headcount..."
                            disabled=${streaming}
                            class="flex-1 border border-gray-300 rounded-xl px-4 py-2.5 text-sm
                                   focus:ring-2 focus:ring-brand-500 focus:border-brand-500
                                   disabled:bg-gray-50 disabled:text-gray-400
                                   placeholder:text-gray-400"
                        />
                        <button
                            onClick=${() => sendMessage()}
                            disabled=${!input.trim() || streaming}
                            class="px-4 py-2.5 rounded-xl text-white text-sm font-medium transition flex-shrink-0
                                   ${!input.trim() || streaming
                                       ? 'bg-gray-300 cursor-not-allowed'
                                       : 'bg-brand-600 hover:bg-brand-700'}">
                            ${streaming ? html`
                                <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                </svg>
                            ` : html`
                                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                                </svg>
                            `}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    window.DT.Chat = Chat;
})();
