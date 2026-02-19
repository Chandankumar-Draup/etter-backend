/**
 * Dashboard View - Executive overview of the Digital Twin state.
 *
 * Shows: enriched KPI strip, function performance chart, readiness gauge,
 * data quality panel, compact quick actions, recent scenarios.
 */

(function () {
    const { html, useState, useEffect, useCallback, useMemo, api, fmt,
            MetricCard, ProgressBar, ErrorBox, SectionHeader, Badge,
            EmptyState, LoadingState, ReadinessGauge, ChartCanvas,
            CHART_COLORS } = window.DT;

    // ── Function Performance Chart ──────────────────────────────────

    function HeadcountChart({ functions, onFunctionClick }) {
        if (!functions || functions.length === 0) return null;

        const sorted = [...functions].sort((a, b) => (b.headcount || 0) - (a.headcount || 0));
        const maxLabelLen = 24;
        const fullNames = sorted.map(f => f.name || 'Unknown');
        const truncLabels = fullNames.map(n =>
            n.length > maxLabelLen ? n.substring(0, maxLabelLen - 1) + '...' : n
        );

        const data = {
            labels: truncLabels,
            datasets: [{
                label: 'Headcount',
                data: sorted.map(f => f.headcount || 0),
                backgroundColor: sorted.map(f => (f.headcount || 0) > 0 ? '#3b82f6' : '#e5e7eb'),
                borderRadius: 4,
                barPercentage: 0.65,
                categoryPercentage: 0.8,
                minBarLength: 4,
            }],
        };

        const options = {
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: ctx => fullNames[ctx[0].dataIndex],
                        afterBody: (ctx) => {
                            const f = sorted[ctx[0].dataIndex];
                            const lines = [];
                            if (f.role_count) lines.push('Roles: ' + f.role_count);
                            if (f.task_count) lines.push('Tasks: ' + f.task_count);
                            return lines;
                        },
                    },
                },
                datalabels: undefined,
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: { display: true, text: 'Headcount', font: { size: 10 }, color: '#6b7280' },
                    grid: { color: '#f3f4f6' },
                },
                y: {
                    grid: { display: false },
                    afterFit: axis => { axis.width = Math.max(axis.width, 150); },
                },
            },
            onHover: (evt, elements) => {
                evt.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
            },
            onClick: (evt, elements) => {
                if (elements.length > 0 && onFunctionClick) {
                    onFunctionClick(sorted[elements[0].index].name);
                }
            },
        };

        const h = Math.max(180, sorted.length * 36);
        return html`<${ChartCanvas} type="bar" data=${data} options=${options} height="${h}px" />`;
    }

    function AutomationChart({ functions, onFunctionClick }) {
        if (!functions || functions.length === 0) return null;

        const sorted = [...functions].sort((a, b) => (b.automation_score || 0) - (a.automation_score || 0));
        const maxLabelLen = 24;
        const fullNames = sorted.map(f => f.name || 'Unknown');
        const truncLabels = fullNames.map(n =>
            n.length > maxLabelLen ? n.substring(0, maxLabelLen - 1) + '...' : n
        );

        const data = {
            labels: truncLabels,
            datasets: [{
                label: 'Automation %',
                data: sorted.map(f => Math.round(f.automation_score || 0)),
                backgroundColor: sorted.map(f => {
                    const a = f.automation_score || 0;
                    return a > 50 ? '#22c55e' : a > 30 ? '#f59e0b' : a > 0 ? '#94a3b8' : '#e5e7eb';
                }),
                borderRadius: 4,
                barPercentage: 0.65,
                categoryPercentage: 0.8,
                minBarLength: 4,
            }],
        };

        const options = {
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: ctx => fullNames[ctx[0].dataIndex],
                        label: ctx => `Automation: ${ctx.raw}%`,
                    },
                },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { callback: v => v + '%' },
                    title: { display: true, text: 'Automation %', font: { size: 10 }, color: '#6b7280' },
                    grid: { color: '#f3f4f6' },
                },
                y: {
                    grid: { display: false },
                    afterFit: axis => { axis.width = Math.max(axis.width, 150); },
                },
            },
            onHover: (evt, elements) => {
                evt.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
            },
            onClick: (evt, elements) => {
                if (elements.length > 0 && onFunctionClick) {
                    onFunctionClick(sorted[elements[0].index].name);
                }
            },
        };

        const h = Math.max(180, sorted.length * 36);
        return html`<${ChartCanvas} type="bar" data=${data} options=${options} height="${h}px" />`;
    }

    // ── Data Quality Panel ──────────────────────────────────────────

    function DataQualityPanel({ validation }) {
        if (!validation) return null;

        const nc = validation.node_counts || {};
        const rc = validation.relationship_counts || {};
        const totalEntities = Object.values(nc).reduce((s, v) => s + (v || 0), 0);
        const totalRels = Object.values(rc).reduce((s, v) => s + (v || 0), 0);

        const totalRoles = nc.DTRole || 0;
        const orphans = validation.orphan_roles || 0;
        const missingWL = validation.roles_without_workloads || 0;
        const missingSkills = validation.roles_without_skills || 0;
        const issues = orphans + missingWL + missingSkills;
        const completeness = totalRoles > 0
            ? Math.round((1 - issues / totalRoles) * 100)
            : 100;

        const alerts = [];
        if (orphans > 0) alerts.push({ label: 'Orphan roles (no parent)', count: orphans });
        if (missingWL > 0) alerts.push({ label: 'Roles without workloads', count: missingWL });
        if (missingSkills > 0) alerts.push({ label: 'Roles without skills', count: missingSkills });

        return html`
            <div class="space-y-4">
                <div class="grid grid-cols-2 gap-3">
                    <div class="bg-gray-50 rounded-lg p-3 text-center">
                        <div class="text-xl font-bold text-gray-900">${fmt.number(totalEntities)}</div>
                        <div class="text-xs text-gray-500">Graph Entities</div>
                    </div>
                    <div class="bg-gray-50 rounded-lg p-3 text-center">
                        <div class="text-xl font-bold text-gray-900">${fmt.number(totalRels)}</div>
                        <div class="text-xs text-gray-500">Relationships</div>
                    </div>
                </div>

                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-xs font-medium text-gray-600 uppercase tracking-wide">Completeness</span>
                        <span class="text-sm font-bold ${completeness >= 90 ? 'text-green-600' : completeness >= 70 ? 'text-amber-600' : 'text-red-600'}">${completeness}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div class="h-2.5 rounded-full transition-all duration-500
                            ${completeness >= 90 ? 'bg-green-500' : completeness >= 70 ? 'bg-amber-500' : 'bg-red-500'}"
                            style=${{width: completeness + '%'}}></div>
                    </div>
                </div>

                ${alerts.length > 0 ? html`
                    <div class="space-y-1.5">
                        <div class="text-xs font-medium text-gray-600 uppercase tracking-wide">Alerts</div>
                        ${alerts.map(a => html`
                            <div key=${a.label} class="flex items-center justify-between text-xs py-1.5 px-2 bg-amber-50 rounded-lg border border-amber-100">
                                <span class="text-amber-800">${a.label}</span>
                                <span class="font-bold text-amber-700">${a.count}</span>
                            </div>
                        `)}
                    </div>
                ` : html`
                    <div class="flex items-center gap-2 text-xs text-green-700 bg-green-50 rounded-lg px-3 py-2 border border-green-100">
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                        </svg>
                        All data quality checks passed
                    </div>
                `}

                <!-- Entity breakdown -->
                <div>
                    <div class="text-xs font-medium text-gray-600 uppercase tracking-wide mb-2">Entity Breakdown</div>
                    <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                        ${[
                            ['Functions', nc.DTFunction],
                            ['SubFunctions', nc.DTSubFunction],
                            ['Job Families', nc.DTJobFamily],
                            ['Roles', nc.DTRole],
                            ['Job Titles', nc.DTJobTitle],
                            ['Workloads', nc.DTWorkload],
                            ['Tasks', nc.DTTask],
                            ['Skills', nc.DTSkill],
                            ['Technologies', nc.DTTechnology],
                        ].map(([label, count]) => html`
                            <div key=${label} class="flex justify-between py-0.5">
                                <span class="text-gray-500">${label}</span>
                                <span class="font-medium text-gray-800">${fmt.number(count || 0)}</span>
                            </div>
                        `)}
                    </div>
                </div>
            </div>
        `;
    }

    // ── Quick Action Button ─────────────────────────────────────────

    // SVG icons for quick actions (professional Lucide-style)
    const QA_ICONS = {
        role_redesign: html`<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>`,
        tech_adoption: html`<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>`,
        graph: html`<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><path stroke-linecap="round" d="M8 6h8M6 8v8m12-8v8M8 18h8"/></svg>`,
        taxonomy: html`<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>`,
    };

    function QuickAction({ icon, svgIcon, label, desc, gradient, hoverBorder, onClick }) {
        return html`
            <button onClick=${onClick}
                class="quick-action-card group p-4 rounded-xl border border-gray-200 bg-gradient-to-br ${gradient}
                       hover:border-brand-300 text-left flex items-center gap-3 cursor-pointer">
                <div class="w-9 h-9 rounded-lg bg-white/80 border border-gray-100 flex items-center justify-center flex-shrink-0 text-brand-600 group-hover:bg-brand-50 transition">
                    ${svgIcon || html`<span class="text-lg">${icon}</span>`}
                </div>
                <div class="min-w-0">
                    <div class="font-semibold text-gray-900 text-sm">${label}</div>
                    <div class="text-xs text-gray-500 truncate">${desc}</div>
                </div>
                <svg class="qa-arrow w-4 h-4 text-gray-300 group-hover:text-brand-500 flex-shrink-0 ml-auto"
                     fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
            </button>
        `;
    }

    // ── Recent Scenarios ────────────────────────────────────────────

    function RecentScenarios({ scenarios, onNavigate }) {
        const [search, setSearch] = useState('');
        const [showAll, setShowAll] = useState(false);

        if (!scenarios || scenarios.length === 0) {
            return html`
                <div class="bg-white rounded-xl border border-gray-200 p-6">
                    <${EmptyState}
                        icon="simulation"
                        title="No simulations yet"
                        message="Run your first workforce simulation to see cascade results, financial impact, and skills analysis."
                        actionLabel="Run Simulation \u2192"
                        onAction=${() => onNavigate("simulator")}
                    />
                </div>
            `;
        }

        // Deduplicate by name+type — keep the latest (first occurrence since API returns latest-first)
        const seen = new Set();
        const deduped = scenarios.filter(s => {
            const key = s.name + '|' + s.type;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });

        // Filter by search
        const filtered = search
            ? deduped.filter(s =>
                (s.name || '').toLowerCase().includes(search.toLowerCase()) ||
                (s.type || '').toLowerCase().includes(search.toLowerCase())
            )
            : deduped;

        const displayLimit = showAll ? filtered.length : 5;
        const displayed = filtered.slice(0, displayLimit);

        const TYPE_ICONS = {
            tech_adoption: html`<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>`,
            multi_tech_adoption: html`<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>`,
            task_distribution: html`<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13h2v8H3zM9 8h2v13H9zM15 11h2v10h-2zM21 4h2v17h-2z"/></svg>`,
            role_redesign: html`<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>`,
        };

        return html`
            <div class="bg-white rounded-xl border border-gray-200 p-6">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h2 class="text-lg font-semibold text-gray-900">Recent Scenarios</h2>
                        <p class="text-sm text-gray-500">${deduped.length} unique scenario(s)</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="relative">
                            <input type="text" value=${search} onInput=${e => setSearch(e.target.value)}
                                placeholder="Filter scenarios..."
                                class="border border-gray-300 rounded-lg pl-8 pr-3 py-1.5 text-xs w-48 focus:ring-brand-500 focus:border-brand-500 outline-none" />
                            <svg class="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                            </svg>
                        </div>
                    </div>
                </div>
                <div class="space-y-2">
                    ${displayed.map((s, i) => {
                        const icon = TYPE_ICONS[s.type] || TYPE_ICONS.role_redesign;
                        const result = s.result || s.cascade || {};
                        const fin = result.financial || {};
                        const wf = result.workforce || {};
                        const preview = fin.roi_pct
                            ? `ROI ${Math.round(fin.roi_pct)}%`
                            : wf.freed_headcount
                            ? `${Math.round(wf.freed_headcount)} FTE freed`
                            : null;
                        return html`
                            <div key=${s.id}
                                class="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 cursor-pointer border border-gray-100 transition group"
                                onClick=${() => onNavigate("results", { scenarioId: s.id })}>
                                <div class="flex items-center gap-3 min-w-0">
                                    <div class="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center text-brand-600 flex-shrink-0">
                                        ${icon}
                                    </div>
                                    <div class="min-w-0">
                                        <div class="flex items-center gap-2">
                                            <span class="font-medium text-gray-900 text-sm truncate">${i + 1}. ${s.name}</span>
                                            ${s.engine === "v2_time_stepped" && html`<${Badge} text="v2" color="blue" />`}
                                        </div>
                                        <div class="flex items-center gap-2 mt-0.5">
                                            <${Badge} text=${s.type.replace(/_/g, " ")} color="blue" />
                                            ${preview && html`<span class="text-xs text-gray-500">${preview}</span>`}
                                            ${s.scope_name && html`<span class="text-xs text-gray-400">\u00b7 ${s.scope_name}</span>`}
                                        </div>
                                    </div>
                                </div>
                                <div class="flex items-center gap-2">
                                    <${Badge}
                                        text=${s.status}
                                        color=${s.status === "completed" ? "green" : s.status === "running" ? "amber" : "gray"}
                                    />
                                    <svg class="w-4 h-4 text-gray-300 group-hover:text-gray-500 transition" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                                    </svg>
                                </div>
                            </div>
                        `;
                    })}
                </div>
                ${filtered.length > 5 && html`
                    <div class="mt-3 text-center">
                        <button onClick=${() => setShowAll(!showAll)}
                            class="text-sm text-brand-600 hover:text-brand-700 font-medium transition">
                            ${showAll ? 'Show less' : `View all ${filtered.length} scenarios`}
                        </button>
                    </div>
                `}
                ${search && filtered.length === 0 && html`
                    <div class="text-center py-6 text-gray-400 text-sm">No scenarios match your search</div>
                `}
            </div>
        `;
    }

    // ── Dashboard Main ──────────────────────────────────────────────

    function Dashboard({ onNavigate }) {
        const [readiness, setReadiness] = useState(null);
        const [hierarchy, setHierarchy] = useState(null);
        const [scenarios, setScenarios] = useState([]);
        const [loading, setLoading] = useState(true);
        const [error, setError] = useState(null);

        const load = () => {
            setLoading(true);
            setError(null);
            Promise.all([
                api.get("/readiness").catch(e => ({ error: e.message })),
                api.get("/hierarchy").catch(e => ({ error: e.message })),
                api.get("/scenarios").catch(e => ({ scenarios: [] })),
            ]).then(([r, h, s]) => {
                if (r.error && typeof r.error === "string") {
                    setError(r.error);
                } else {
                    setReadiness(r);
                }
                if (h.hierarchy) setHierarchy(h.hierarchy);
                setScenarios(s.scenarios || []);
                setLoading(false);
            });
        };

        useEffect(load, []);

        // Extract function-level data from hierarchy (must be before early returns)
        const functions = useMemo(() => {
            if (!hierarchy?.children) return [];
            return hierarchy.children.map(f => ({
                name: f.name,
                headcount: f.headcount || 0,
                automation_score: f.automation_score || 0,
                role_count: f.role_count || 0,
                task_count: f.task_count || 0,
            }));
        }, [hierarchy]);

        if (loading) return html`
            <div class="space-y-6">
                <${LoadingState} type="cards" count=${4} />
                <${LoadingState} type="chart" />
                <${LoadingState} type="cards" count=${3} />
            </div>
        `;

        const rd = readiness?.readiness;
        const val = readiness?.validation;
        const dims = rd?.dimensions || {};
        const nc = val?.node_counts || {};
        const orgAutoScore = hierarchy?.automation_score || 0;
        const orgName = hierarchy?.name || 'Organization';

        return html`
            <div class="fade-in space-y-6">
                <!-- Hero Header -->
                <div class="relative rounded-xl overflow-hidden bg-gradient-to-r from-brand-600 via-brand-700 to-brand-800 p-6 shadow-lg">
                    <div class="absolute inset-0 opacity-10" style=${{backgroundImage:'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' fill-opacity=\'0.4\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")'}}></div>
                    <div class="relative flex items-center justify-between">
                        <div>
                            <h1 class="text-2xl font-bold text-white font-heading">Workforce Twin Dashboard</h1>
                            <p class="text-sm text-blue-100 mt-1">
                                ${orgName} \u00b7 ${fmt.number(hierarchy?.headcount || 0)} headcount \u00b7 ${Math.round(orgAutoScore)}% automation potential
                            </p>
                            <p class="text-xs text-blue-200 mt-2 flex items-center gap-1.5">
                                <span class="w-1.5 h-1.5 rounded-full bg-green-400 pulse-dot"></span>
                                Last updated: ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                ${scenarios.length > 0 ? ` \u00b7 ${scenarios.length} scenario(s) run` : ''}
                            </p>
                        </div>
                        <button onClick=${() => onNavigate("simulator")}
                            class="bg-white text-brand-700 px-5 py-2.5 rounded-lg hover:bg-blue-50 transition text-sm font-semibold flex items-center gap-2 shadow-md hover:shadow-lg cta-pulse">
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                            Run Simulation
                        </button>
                    </div>
                </div>

                ${error && html`<${ErrorBox} message=${error} onRetry=${load} />`}

                <!-- KPI Strip — 4-col desktop, 2-col tablet, 1-col mobile -->
                ${val && html`
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                        <${MetricCard} label="Headcount"
                            value=${fmt.number(hierarchy?.headcount || 0)}
                            icon=${html`<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>`}
                            color="blue" sub="All functions" />
                        <${MetricCard} label="Roles"
                            value=${fmt.number(nc.DTRole || 0)}
                            icon=${html`<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0"/></svg>`}
                            color="blue" sub="${fmt.number(nc.DTJobTitle || 0)} titles" />
                        <${MetricCard} label="Tasks"
                            value=${fmt.number(nc.DTTask || 0)}
                            icon=${html`<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>`}
                            color="blue" sub="${fmt.number(nc.DTWorkload || 0)} workloads" />
                        <${MetricCard} label="Automation"
                            value=${Math.round(orgAutoScore) + '%'}
                            icon=${html`<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`}
                            color=${orgAutoScore > 50 ? "green" : orgAutoScore > 30 ? "amber" : "slate"}
                            sub="Weighted avg" />
                    </div>
                `}

                <!-- Quick Actions (primary workflows — placed right after KPIs) -->
                <div class="bg-white rounded-xl border border-gray-200 p-6">
                    <${SectionHeader} title="Quick Actions" subtitle="Primary workflows" />
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                        <${QuickAction} svgIcon=${QA_ICONS.role_redesign} label="Role Redesign"
                            desc="Simulate automation impact"
                            gradient="from-blue-50 to-white"
                            onClick=${() => onNavigate("simulator")} />
                        <${QuickAction} svgIcon=${QA_ICONS.tech_adoption} label="Tech Adoption"
                            desc="Deploy Copilot, UiPath, AI"
                            gradient="from-brand-50 to-white"
                            onClick=${() => onNavigate("simulator", { type: "tech_adoption" })} />
                        <${QuickAction} svgIcon=${QA_ICONS.graph} label="Explore Graph"
                            desc="Interactive knowledge graph"
                            gradient="from-purple-50 to-white"
                            onClick=${() => onNavigate("graph")} />
                        <${QuickAction} svgIcon=${QA_ICONS.taxonomy} label="Explore Taxonomy"
                            desc="Navigate org structure"
                            gradient="from-green-50 to-white"
                            onClick=${() => onNavigate("explorer")} />
                    </div>
                </div>

                <!-- Function Performance Charts (split: Headcount + Automation) -->
                ${functions.length > 0 && html`
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div class="bg-white rounded-xl border border-gray-200 p-6">
                            <${SectionHeader} title="Headcount by Function"
                                subtitle="Click a bar to explore" />
                            <${HeadcountChart}
                                functions=${functions}
                                onFunctionClick=${name => onNavigate("explorer", { functionName: name })} />
                        </div>
                        <div class="bg-white rounded-xl border border-gray-200 p-6">
                            <${SectionHeader} title="Automation Potential"
                                subtitle="Weighted average by function" />
                            <${AutomationChart}
                                functions=${functions}
                                onFunctionClick=${name => onNavigate("explorer", { functionName: name })} />
                        </div>
                    </div>
                `}

                <!-- Readiness + Data Quality -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    ${rd && html`
                        <div class="bg-white rounded-xl border border-gray-200 p-6">
                            <${SectionHeader} title="Data Readiness"
                                subtitle="Simulation accuracy score" />
                            ${rd.total_score === rd.max_score ? html`
                                <!-- Compact status when perfect score -->
                                <div class="flex items-center gap-3 mb-4 p-3 bg-positive-50 rounded-lg border border-positive-200">
                                    <div class="w-10 h-10 rounded-full bg-positive-100 flex items-center justify-center flex-shrink-0">
                                        <svg class="w-5 h-5 text-positive-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                                        </svg>
                                    </div>
                                    <div>
                                        <div class="text-sm font-semibold text-positive-700">${rd.total_score}/${rd.max_score} \u2014 Fully Ready</div>
                                        <div class="text-xs text-positive-600">All dimensions at maximum. Simulations will be high-fidelity.</div>
                                    </div>
                                </div>
                            ` : html`
                                <div class="flex flex-col items-center mb-4">
                                    <${ReadinessGauge} score=${rd.total_score} maxScore=${rd.max_score} status=${rd.status} />
                                    <${Badge} text=${rd.status} color=${rd.status === "READY" ? "green" : rd.status === "PARTIAL" ? "amber" : "red"} />
                                </div>
                            `}
                            <div class="space-y-1.5">
                                ${Object.entries(dims).map(([key, dim]) => {
                                    const TOOLTIPS = {
                                        enterprise_context: 'Measures completeness of headcount, salary, and cost data across the hierarchy.',
                                        role_decomposition: 'Checks that roles have workloads and tasks attached with proper classifications.',
                                        skills_architecture: 'Verifies skill and technology nodes exist and are linked to roles.',
                                        taxonomy_completeness: 'Ensures all 6 levels of the organizational hierarchy are populated.',
                                        validation_trust: 'Checks for orphan nodes, structural issues, and data consistency.',
                                    };
                                    const tooltipText = TOOLTIPS[key] || '';
                                    const dimLabel = key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
                                    return html`
                                        <div key=${key} class="dt-tooltip">
                                            <${ProgressBar}
                                                label=${dimLabel}
                                                value=${dim.score}
                                                max=${dim.max}
                                                color=${dim.score >= dim.max * 0.7 ? "green" : dim.score >= dim.max * 0.4 ? "amber" : "red"}
                                            />
                                            ${tooltipText && html`<span class="dt-tooltip-text">${tooltipText}</span>`}
                                        </div>
                                    `;
                                })}
                            </div>
                        </div>
                    `}

                    ${val && html`
                        <div class="bg-white rounded-xl border border-gray-200 p-6">
                            <${SectionHeader} title="Data Quality"
                                subtitle="Graph completeness and health" />
                            <${DataQualityPanel} validation=${val} />
                        </div>
                    `}
                </div>

                <!-- Recent Scenarios -->
                <${RecentScenarios} scenarios=${scenarios} onNavigate=${onNavigate} />
            </div>
        `;
    }

    window.DT.Dashboard = Dashboard;
})();
