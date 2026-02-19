/**
 * Shared UI components for the Digital Twin interface.
 *
 * Uses React 18 + htm (tagged template literal alternative to JSX).
 * All components are registered on window.DT for cross-file access.
 */

const html = htm.bind(React.createElement);
const { useState, useEffect, useRef, useCallback, useMemo } = React;

// ── Chart Colors ────────────────────────────────────────────────────

const CHART_COLORS = {
    positive: '#22c55e',  positiveLight: '#86efac',
    negative: '#ef4444',  negativeLight: '#fca5a5',
    warning:  '#f59e0b',  warningLight: '#fcd34d',
    ai:       '#a855f7',  aiLight: '#d8b4fe',
    info:     '#3b82f6',  infoLight: '#93c5fd',
    neutral:  '#6b7280',  neutralLight: '#d1d5db',
    series: ['#3b82f6','#22c55e','#f59e0b','#a855f7','#ef4444','#06b6d4','#f97316','#ec4899'],
};

// ── API helper ──────────────────────────────────────────────────────

const api = {
    async get(path) {
        const res = await fetch(`/api/dt${path}`);
        if (!res.ok) throw new Error((await res.json()).error || res.statusText);
        return res.json();
    },
    async post(path, body) {
        const res = await fetch(`/api/dt${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error((await res.json()).error || res.statusText);
        return res.json();
    },
    async del(path) {
        const res = await fetch(`/api/dt${path}`, { method: "DELETE" });
        if (!res.ok) throw new Error((await res.json()).error || res.statusText);
        return res.json();
    },
};

// ── MetricCard ──────────────────────────────────────────────────────

function MetricCard({ label, value, sub, icon, color = "blue", onClick }) {
    // Cohesive palette: primary blue for most metrics, green for positive
    // indicators, red for costs/negatives, slate for muted secondary data.
    // Legacy color names (purple, amber, indigo, cyan) map to primary blue.
    const colors = {
        blue:   "bg-brand-50 text-brand-800 border-brand-200",
        green:  "bg-positive-50 text-positive-700 border-positive-200",
        red:    "bg-negative-50 text-negative-700 border-negative-200",
        amber:  "bg-warning-50 text-warning-700 border-warning-200",
        slate:  "bg-gray-50 text-gray-600 border-gray-200",
        // Aliases — route rainbow colors to primary blue
        purple: "bg-brand-50 text-brand-800 border-brand-200",
        indigo: "bg-brand-50 text-brand-800 border-brand-200",
        cyan:   "bg-brand-50 text-brand-800 border-brand-200",
    };
    const cls = colors[color] || colors.blue;
    const cursor = onClick ? "cursor-pointer" : "";
    return html`
        <div class="border rounded-xl p-4 ${cls} ${cursor} hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 fade-in"
             onClick=${onClick}>
            <div class="flex items-center justify-between mb-1">
                <span class="text-xs font-medium uppercase tracking-wide opacity-70">${label}</span>
                ${icon && html`<span class="text-lg">${icon}</span>`}
            </div>
            <div class="text-2xl font-bold font-heading">${value}</div>
            ${sub && html`<div class="text-xs mt-1 opacity-70">${sub}</div>`}
        </div>
    `;
}

// ── Badge ───────────────────────────────────────────────────────────

function Badge({ text, color = "gray" }) {
    const colors = {
        gray:   "bg-gray-100 text-gray-700",
        blue:   "bg-brand-100 text-brand-700",
        green:  "bg-positive-100 text-positive-700 ring-1 ring-positive-200",
        amber:  "bg-warning-100 text-warning-700",
        red:    "bg-negative-100 text-negative-700",
        purple: "bg-brand-100 text-brand-700",
        indigo: "bg-brand-100 text-brand-700",
    };
    return html`
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[color] || colors.gray}">
            ${text}
        </span>
    `;
}

// ── ProgressBar ─────────────────────────────────────────────────────

function ProgressBar({ value, max = 100, label, color = "blue" }) {
    const pct = Math.min(100, Math.round((value / max) * 100));
    const barColors = {
        blue: "bg-blue-500", green: "bg-green-500", amber: "bg-amber-500",
        red: "bg-red-500", purple: "bg-brand-500",
    };
    return html`
        <div class="mb-2">
            ${label && html`
                <div class="flex justify-between text-xs mb-1">
                    <span class="text-gray-600">${label}</span>
                    <span class="font-medium">${value}/${max}</span>
                </div>
            `}
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="${barColors[color] || barColors.blue} h-2 rounded-full transition-all duration-500"
                     style=${{width: `${pct}%`}}></div>
            </div>
        </div>
    `;
}

// ── Spinner ─────────────────────────────────────────────────────────

function Spinner({ size = "md", text = "" }) {
    const sizes = { sm: "h-4 w-4", md: "h-8 w-8", lg: "h-12 w-12" };
    return html`
        <div class="flex flex-col items-center justify-center py-8">
            <svg class="animate-spin ${sizes[size]} text-brand-600" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
            </svg>
            ${text && html`<p class="mt-2 text-sm text-gray-500">${text}</p>`}
        </div>
    `;
}

// ── ErrorBox ────────────────────────────────────────────────────────

function ErrorBox({ message, onRetry }) {
    return html`
        <div class="bg-red-50 border border-red-200 rounded-lg p-4 my-4">
            <div class="flex items-start">
                <span class="text-red-500 mr-2 text-lg">!</span>
                <div class="flex-1">
                    <p class="text-sm text-red-700">${message}</p>
                    ${onRetry && html`
                        <button onClick=${onRetry}
                            class="mt-2 text-xs text-red-600 hover:text-red-800 underline">
                            Try again
                        </button>
                    `}
                </div>
            </div>
        </div>
    `;
}

// ── SectionHeader ───────────────────────────────────────────────────

function SectionHeader({ title, subtitle, action }) {
    return html`
        <div class="flex items-center justify-between mb-4">
            <div>
                <h2 class="text-lg font-semibold text-gray-900">${title}</h2>
                ${subtitle && html`<p class="text-sm text-gray-500">${subtitle}</p>`}
            </div>
            ${action}
        </div>
    `;
}

// ── DataTable ───────────────────────────────────────────────────────

function DataTable({ columns, rows, onRowClick }) {
    if (!rows || rows.length === 0) {
        return html`<p class="text-sm text-gray-400 py-4">No data available</p>`;
    }
    return html`
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 text-sm">
                <thead class="bg-gray-50">
                    <tr>
                        ${columns.map(col => html`
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                ${col.label}
                            </th>
                        `)}
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-100">
                    ${rows.map((row, i) => html`
                        <tr key=${i} class="${onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}"
                            onClick=${() => onRowClick && onRowClick(row)}>
                            ${columns.map(col => html`
                                <td class="px-4 py-2 whitespace-nowrap">
                                    ${col.render ? col.render(row) : row[col.key]}
                                </td>
                            `)}
                        </tr>
                    `)}
                </tbody>
            </table>
        </div>
    `;
}

// ── EmptyState ──────────────────────────────────────────────────────

function EmptyState({ icon = "chart", title, message, actionLabel, onAction }) {
    const icons = {
        chart: html`<svg class="w-16 h-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 13h2v8H3zM9 8h2v13H9zM15 11h2v10h-2zM21 4h2v17h-2z"/></svg>`,
        simulation: html`<svg class="w-16 h-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`,
        data: html`<svg class="w-16 h-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"/></svg>`,
        comparison: html`<svg class="w-16 h-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>`,
    };
    return html`
        <div class="flex flex-col items-center justify-center py-12 text-center">
            ${icons[icon] || icons.chart}
            <h3 class="mt-4 text-lg font-medium text-gray-900">${title || "No data yet"}</h3>
            ${message && html`<p class="mt-1 text-sm text-gray-500 max-w-sm">${message}</p>`}
            ${actionLabel && onAction && html`
                <button onClick=${onAction}
                    class="mt-4 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition">
                    ${actionLabel}
                </button>
            `}
        </div>
    `;
}

// ── LoadingState ────────────────────────────────────────────────────

function LoadingState({ type = "cards", count = 4 }) {
    if (type === "cards") {
        return html`
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                ${Array.from({length: count}).map((_, i) => html`
                    <div key=${i} class="border border-gray-200 rounded-xl p-4 space-y-2">
                        <div class="h-3 w-20 shimmer rounded"></div>
                        <div class="h-8 w-16 shimmer rounded"></div>
                    </div>
                `)}
            </div>
        `;
    }
    if (type === "chart") {
        return html`<div class="h-64 shimmer rounded-xl"></div>`;
    }
    return html`
        <div class="space-y-2">
            ${Array.from({length: count}).map((_, i) => html`
                <div key=${i} class="h-10 shimmer rounded-lg"></div>
            `)}
        </div>
    `;
}

// ── ChartCanvas ─────────────────────────────────────────────────────

function ChartCanvas({ type, data, options, height = "300px" }) {
    const canvasRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        if (!canvasRef.current || !data) return;

        if (chartRef.current) {
            chartRef.current.destroy();
        }

        chartRef.current = new Chart(canvasRef.current, {
            type,
            data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 800, easing: 'easeOutQuart' },
                ...options,
            },
        });

        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
                chartRef.current = null;
            }
        };
    }, [type, JSON.stringify(data), JSON.stringify(options)]);

    return html`
        <div class="chart-animate" style=${{height}}>
            <canvas ref=${canvasRef}></canvas>
        </div>
    `;
}

// ── Formatters ──────────────────────────────────────────────────────

const fmt = {
    currency(val) {
        if (val == null) return "$0";
        const abs = Math.abs(val);
        if (abs >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
        if (abs >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
        return `$${val.toFixed(0)}`;
    },
    pct(val) {
        if (val == null) return "0%";
        return `${val.toFixed(1)}%`;
    },
    number(val) {
        if (val == null) return "0";
        return val.toLocaleString();
    },
    severity(sev) {
        const map = { high: "red", medium: "amber", low: "green" };
        return map[sev] || "gray";
    },
};

// ── ErrorBoundary ──────────────────────────────────────────────────
// Class component required — React hooks can't catch render errors.

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { error };
    }

    componentDidCatch(error, errorInfo) {
        this.setState({ errorInfo });
        console.error("[Digital Twin] Render error:", error, errorInfo);
    }

    render() {
        if (this.state.error) {
            return React.createElement("div", {
                style: { padding: "32px", fontFamily: "monospace", maxWidth: "800px", margin: "0 auto" }
            },
                React.createElement("h2", {
                    style: { color: "#dc2626", fontSize: "20px", marginBottom: "12px" }
                }, "Digital Twin - Rendering Error"),
                React.createElement("pre", {
                    style: {
                        background: "#fef2f2", border: "1px solid #fecaca",
                        borderRadius: "8px", padding: "16px", fontSize: "13px",
                        whiteSpace: "pre-wrap", wordBreak: "break-word", overflow: "auto"
                    }
                }, String(this.state.error)),
                this.state.errorInfo && React.createElement("details", {
                    style: { marginTop: "12px" }
                },
                    React.createElement("summary", {
                        style: { cursor: "pointer", color: "#6b7280", fontSize: "13px" }
                    }, "Component stack trace"),
                    React.createElement("pre", {
                        style: { fontSize: "12px", color: "#6b7280", marginTop: "8px", whiteSpace: "pre-wrap" }
                    }, this.state.errorInfo.componentStack)
                ),
                React.createElement("button", {
                    onClick: () => { this.setState({ error: null, errorInfo: null }); },
                    style: {
                        marginTop: "16px", padding: "8px 16px", background: "#2563eb",
                        color: "white", border: "none", borderRadius: "6px", cursor: "pointer"
                    }
                }, "Try Again")
            );
        }
        return this.props.children;
    }
}

// ── Export to window ────────────────────────────────────────────────

window.DT = window.DT || {};
Object.assign(window.DT, {
    html, useState, useEffect, useRef, useCallback, useMemo,
    api, fmt, CHART_COLORS,
    MetricCard, Badge, ProgressBar, Spinner, ErrorBox,
    SectionHeader, DataTable, ChartCanvas, ErrorBoundary,
    EmptyState, LoadingState,
});
