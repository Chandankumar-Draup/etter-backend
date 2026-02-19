/**
 * Comparison View - Side-by-side multi-scenario comparison.
 *
 * Features: scenario selection (max 4), comparison table with delta highlighting,
 * radar chart with semantic colors, grouped bar chart for financials,
 * per-scenario KPI cards, best-by-ROI and lowest-risk highlighting,
 * adoption overlay, trade-off summary, empty state.
 */

(function () {
    const { html, useState, useEffect, useMemo, api, fmt,
            MetricCard, Badge, Spinner, ErrorBox, SectionHeader,
            DataTable, ChartCanvas, EmptyState, LoadingState,
            CHART_COLORS, AdoptionSCurve } = window.DT;

    const MAX_SELECTIONS = 4;

    // ── Helpers ───────────────────────────────────────────────────────

    const SCENARIO_COLORS = [
        CHART_COLORS.info, CHART_COLORS.positive, CHART_COLORS.warning,
        CHART_COLORS.ai,
    ];

    const TYPE_ICONS = {
        tech_adoption: '\u{1F916}',
        multi_tech_adoption: '\u{1F52C}',
        task_distribution: '\u{1F4CA}',
    };
    const TYPE_BADGE_COLORS = {
        tech_adoption: 'blue',
        multi_tech_adoption: 'blue',
        task_distribution: 'blue',
    };

    function bestValue(items, key, lower) {
        const vals = items.map(x => x[key]);
        return lower ? Math.min(...vals) : Math.max(...vals);
    }
    function worstValue(items, key, lower) {
        const vals = items.map(x => x[key]);
        return lower ? Math.max(...vals) : Math.min(...vals);
    }

    function formatDate(ts) {
        if (!ts) return '';
        const d = new Date(ts * 1000);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    // ── Scenario Selector Card ────────────────────────────────────────

    function ScenarioCard({ scenario, selected, disabled, colorIndex, onToggle }) {
        const s = scenario;
        const icon = TYPE_ICONS[s.type] || '\u{1F504}';
        const badgeColor = TYPE_BADGE_COLORS[s.type] || 'gray';
        const colorBar = selected ? SCENARIO_COLORS[colorIndex % SCENARIO_COLORS.length] : 'transparent';

        return html`
            <div
                class="relative flex items-start gap-3 p-4 rounded-xl border-2 transition-all cursor-pointer
                    ${selected
                        ? 'border-brand-300 bg-brand-50/60 shadow-sm'
                        : disabled
                            ? 'border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed'
                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'}"
                onClick=${() => { if (!disabled || selected) onToggle(s.id); }}>
                <!-- Color indicator bar -->
                <div class="absolute left-0 top-3 bottom-3 w-1 rounded-full" style=${{backgroundColor: colorBar}}></div>
                <input type="checkbox"
                    checked=${selected}
                    disabled=${disabled && !selected}
                    onChange=${() => onToggle(s.id)}
                    class="mt-0.5 rounded text-brand-600 focus:ring-brand-500 flex-shrink-0"
                />
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-base">${icon}</span>
                        <span class="font-semibold text-sm text-gray-900 truncate">${s.name}</span>
                    </div>
                    <div class="flex items-center gap-2 flex-wrap">
                        <${Badge} text=${s.type.replace(/_/g, " ")} color=${badgeColor} />
                        ${s.engine && html`<${Badge} text=${s.engine} color=${s.engine === 'v2_time_stepped' ? 'blue' : 'gray'} />`}
                        ${s.scope_name && html`
                            <span class="text-xs text-gray-400">${(s.scope_type || '').replace(/_/g, ' ')}: ${s.scope_name}</span>
                        `}
                    </div>
                    ${s.created_at > 0 && html`
                        <div class="text-xs text-gray-400 mt-1">${formatDate(s.created_at)}</div>
                    `}
                </div>
            </div>
        `;
    }

    // ── Per-Scenario KPI Cards ────────────────────────────────────────

    function ScenarioKPIRow({ items }) {
        return html`
            <div class="grid gap-4" style=${{gridTemplateColumns: `repeat(${items.length}, 1fr)`}}>
                ${items.map((item, i) => {
                    const color = SCENARIO_COLORS[i % SCENARIO_COLORS.length];
                    return html`
                        <div key=${item.scenario_id}
                            class="rounded-xl border border-gray-200 p-4 space-y-3"
                            style=${{borderTopColor: color, borderTopWidth: '3px'}}>
                            <div class="font-semibold text-sm text-gray-900 truncate">${item.scenario_name}</div>
                            <div class="grid grid-cols-2 gap-2">
                                <div>
                                    <div class="text-xs text-gray-500">Net Impact</div>
                                    <div class="text-sm font-bold ${item.financial.net_impact >= 0 ? 'text-positive-700' : 'text-negative-600'}">
                                        ${fmt.currency(item.financial.net_impact)}
                                    </div>
                                </div>
                                <div>
                                    <div class="text-xs text-gray-500">ROI</div>
                                    <div class="text-sm font-bold ${item.financial.roi_pct >= 0 ? 'text-positive-700' : 'text-negative-600'}">
                                        ${fmt.pct(item.financial.roi_pct)}
                                    </div>
                                </div>
                                <div>
                                    <div class="text-xs text-gray-500">HC Freed</div>
                                    <div class="text-sm font-semibold text-gray-800">
                                        ${Math.round(item.workforce.freed_headcount)}
                                    </div>
                                </div>
                                <div>
                                    <div class="text-xs text-gray-500">Risks</div>
                                    <div class="text-sm font-semibold ${item.risk.high_risks > 0 ? 'text-negative-600' : 'text-positive-700'}">
                                        ${item.risk.total_risks} (${item.risk.high_risks} high)
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                })}
            </div>
        `;
    }

    // ── Grouped Financial Bar Chart ──────────────────────────────────

    function FinancialBarChart({ items }) {
        const data = useMemo(() => ({
            labels: items.map(i => i.scenario_name),
            datasets: [
                {
                    label: "Gross Savings",
                    data: items.map(i => i.financial.gross_savings),
                    backgroundColor: CHART_COLORS.positive,
                    borderRadius: 4,
                },
                {
                    label: "Total Cost",
                    data: items.map(i => -Math.abs(i.financial.total_cost)),
                    backgroundColor: CHART_COLORS.negative,
                    borderRadius: 4,
                },
                {
                    label: "Net Impact",
                    data: items.map(i => i.financial.net_impact),
                    backgroundColor: CHART_COLORS.info,
                    borderRadius: 4,
                },
            ],
        }), [items]);

        const options = {
            indexAxis: 'y',
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${fmt.currency(Math.abs(ctx.raw))}`,
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: '#f3f4f6' },
                    ticks: { callback: v => fmt.currency(v) },
                },
                y: { grid: { display: false } },
            },
        };

        return html`<${ChartCanvas} type="bar" data=${data} options=${options} height="220px" />`;
    }

    // ── Adoption S-Curve Overlay (v2 scenarios) ─────────────────

    function AdoptionOverlay({ items }) {
        const v2Items = items.filter(i => i.v2_snapshots?.length > 0);
        if (v2Items.length === 0) return null;

        const maxMonths = Math.max(...v2Items.map(i => i.v2_snapshots.length));
        const labels = Array.from({ length: maxMonths }, (_, i) => `M${i + 1}`);

        const data = useMemo(() => ({
            labels,
            datasets: v2Items.map((item, i) => {
                const color = SCENARIO_COLORS[items.indexOf(item) % SCENARIO_COLORS.length];
                return {
                    label: item.scenario_name,
                    data: item.v2_snapshots.map(s => (s.adoption?.level || 0) * 100),
                    borderColor: color,
                    backgroundColor: color + "15",
                    fill: i === 0,
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2.5,
                };
            }),
        }), [v2Items]);

        const options = {
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 12, font: { size: 10 } } },
                y: { beginAtZero: true, max: 100, ticks: { callback: v => v + "%" } },
            },
            plugins: {
                legend: { position: "bottom", labels: { usePointStyle: true, padding: 16, font: { size: 12 } } },
                tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.raw.toFixed(1)}%` } },
            },
            interaction: { mode: "index", intersect: false },
        };

        return html`<${ChartCanvas} type="line" data=${data} options=${options} height="280px" />`;
    }

    // ── Delta-Highlighted Table ──────────────────────────────────────

    function DeltaTable({ title, metrics, items, dataKey }) {
        const rangeRow = useMemo(() => {
            const r = {};
            metrics.forEach(m => {
                const vals = items.map(i => i[dataKey][m.key]);
                const min = Math.min(...vals);
                const max = Math.max(...vals);
                r[m.key] = { min, max, spread: max - min };
            });
            return r;
        }, [items, metrics, dataKey]);

        return html`
            <div class="bg-white rounded-xl border border-gray-200 p-4">
                <${SectionHeader} title=${title} />
                <div class="overflow-x-auto">
                    <table class="min-w-full text-sm">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Metric</th>
                                ${items.map((item, i) => html`
                                    <th key=${item.scenario_id}
                                        class="px-4 py-2 text-right text-xs font-medium uppercase"
                                        style=${{color: SCENARIO_COLORS[i % SCENARIO_COLORS.length]}}>
                                        ${item.scenario_name}
                                    </th>
                                `)}
                                <th class="px-4 py-2 text-right text-xs font-medium text-gray-400 uppercase">Range</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-100">
                            ${metrics.map(metric => {
                                const best = bestValue(items.map(i => i[dataKey]), metric.key, metric.lowerBetter);
                                const worst = worstValue(items.map(i => i[dataKey]), metric.key, metric.lowerBetter);
                                return html`
                                    <tr key=${metric.label}>
                                        <td class="px-4 py-2.5 font-medium text-gray-700">${metric.label}</td>
                                        ${items.map(item => {
                                            const val = item[dataKey][metric.key];
                                            const isBest = val === best;
                                            const isWorst = val === worst && items.length > 1;
                                            return html`
                                                <td key=${item.scenario_id}
                                                    class="px-4 py-2.5 text-right ${isBest ? 'text-positive-700 font-semibold bg-positive-50' :
                                                        isWorst ? 'text-negative-600 bg-negative-50' : ''}">
                                                    <span>${metric.fmt(val)}</span>
                                                    ${isBest && items.length > 1 ? html`
                                                        <span class="ml-1 text-xs text-positive-500">\u2605</span>
                                                    ` : null}
                                                </td>
                                            `;
                                        })}
                                        <td class="px-4 py-2.5 text-right text-xs text-gray-400">
                                            ${metric.fmt(rangeRow[metric.key]?.spread || 0)}
                                        </td>
                                    </tr>
                                `;
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    // ── Comparison Results ────────────────────────────────────────────

    function ComparisonResults({ comparison }) {
        const items = comparison.scenarios || [];
        if (items.length === 0) return null;

        // Radar chart with semantic colors
        const radarData = useMemo(() => ({
            labels: ["ROI %", "Net Savings", "Low Risk", "Low HC Reduction", "Skills Coverage"],
            datasets: items.map((item, i) => {
                const color = SCENARIO_COLORS[i % SCENARIO_COLORS.length];
                const maxRoi = Math.max(...items.map(x => Math.abs(x.financial.roi_pct)), 1);
                const maxSavings = Math.max(...items.map(x => Math.abs(x.financial.net_impact)), 1);
                const maxRisk = Math.max(...items.map(x => x.risk.total_risks), 1);
                const maxReduction = Math.max(...items.map(x => x.workforce.reduction_pct), 1);
                const maxSkills = Math.max(...items.map(x => x.skills.sunrise_count), 1);

                return {
                    label: item.scenario_name,
                    data: [
                        maxRoi > 0 ? (item.financial.roi_pct / maxRoi) * 100 : 0,
                        maxSavings > 0 ? (item.financial.net_impact / maxSavings) * 100 : 0,
                        100 - (item.risk.total_risks / maxRisk) * 100,
                        100 - (item.workforce.reduction_pct / maxReduction) * 100,
                        (item.skills.sunrise_count / maxSkills) * 100,
                    ],
                    borderColor: color,
                    backgroundColor: color + "20",
                    pointBackgroundColor: color,
                    pointRadius: 4,
                    borderWidth: 2,
                };
            }),
        }), [items]);

        const radarOptions = {
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { stepSize: 25, display: false },
                    pointLabels: { font: { size: 12, weight: '500' }, color: '#374151' },
                    grid: { color: '#e5e7eb' },
                    angleLines: { color: '#e5e7eb' },
                },
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { usePointStyle: true, padding: 16, font: { size: 12 } },
                },
            },
        };

        const financialMetrics = [
            { label: "Gross Savings", key: "gross_savings", fmt: fmt.currency, lowerBetter: false },
            { label: "Net Impact", key: "net_impact", fmt: fmt.currency, lowerBetter: false },
            { label: "Total Cost", key: "total_cost", fmt: fmt.currency, lowerBetter: true },
            { label: "ROI", key: "roi_pct", fmt: fmt.pct, lowerBetter: false },
            { label: "Payback (months)", key: "payback_months", fmt: v => v, lowerBetter: true },
        ];

        const workforceMetrics = [
            { label: "Freed Headcount", key: "freed_headcount", fmt: v => Math.round(v), lowerBetter: false },
            { label: "Reduction %", key: "reduction_pct", fmt: fmt.pct, lowerBetter: false },
            { label: "Redeployable", key: "redeployable", fmt: v => Math.round(v), lowerBetter: false },
        ];

        const riskMetrics = [
            { label: "Total Risks", key: "total_risks", fmt: v => v, lowerBetter: true },
            { label: "High Risks", key: "high_risks", fmt: v => v, lowerBetter: true },
        ];

        const skillsMetrics = [
            { label: "Sunrise Skills", key: "sunrise_count", fmt: v => v, lowerBetter: false },
            { label: "Sunset Skills", key: "sunset_count", fmt: v => v, lowerBetter: true },
            { label: "Reskilling Cost", key: "reskilling_cost", fmt: fmt.currency, lowerBetter: true },
        ];

        // Find winner details
        const bestRoiItem = items.find(i => i.scenario_name === comparison.best_by_roi);
        const lowestRiskItem = items.find(i => i.scenario_name === comparison.lowest_risk);

        return html`
            <div class="space-y-5 fade-in">
                <!-- Winner Banner -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div class="bg-gradient-to-br from-positive-50 to-white rounded-xl border border-positive-200 p-5">
                        <div class="flex items-center gap-2 mb-2">
                            <span class="text-lg">\u{1F3C6}</span>
                            <div class="text-xs font-semibold text-positive-600 uppercase tracking-wide">Best ROI</div>
                        </div>
                        <div class="text-lg font-bold text-positive-700 truncate">${comparison.best_by_roi}</div>
                        <div class="flex items-center gap-3 mt-2 text-xs text-positive-600">
                            <span>ROI: ${fmt.pct(bestRoiItem?.financial?.roi_pct || 0)}</span>
                            <span>Net: ${fmt.currency(bestRoiItem?.financial?.net_impact || 0)}</span>
                        </div>
                    </div>
                    <div class="bg-gradient-to-br from-info-50 to-white rounded-xl border border-info-200 p-5">
                        <div class="flex items-center gap-2 mb-2">
                            <span class="text-lg">\u{1F6E1}\u{FE0F}</span>
                            <div class="text-xs font-semibold text-info-600 uppercase tracking-wide">Lowest Risk</div>
                        </div>
                        <div class="text-lg font-bold text-info-700 truncate">${comparison.lowest_risk}</div>
                        <div class="flex items-center gap-3 mt-2 text-xs text-info-600">
                            <span>Total: ${lowestRiskItem?.risk?.total_risks || 0} risks</span>
                            <span>High: ${lowestRiskItem?.risk?.high_risks || 0}</span>
                        </div>
                    </div>
                </div>

                <!-- Per-Scenario KPI Strip -->
                <${ScenarioKPIRow} items=${items} />

                <!-- Radar + Grouped Bars Row -->
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div class="bg-white rounded-xl border border-gray-200 p-5">
                        <${SectionHeader} title="Multi-Dimensional Comparison"
                            subtitle="Normalized 0-100 scale across 5 dimensions" />
                        <${ChartCanvas} type="radar" data=${radarData}
                            options=${radarOptions} height="320px" />
                    </div>
                    <div class="bg-white rounded-xl border border-gray-200 p-5">
                        <${SectionHeader} title="Financial Overview"
                            subtitle="Savings, costs, and net impact comparison" />
                        <${FinancialBarChart} items=${items} />
                    </div>
                </div>

                <!-- v2 Adoption S-Curve Overlay -->
                ${items.some(i => i.v2_snapshots?.length > 0) && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-5">
                        <${SectionHeader} title="Adoption Trajectory Comparison"
                            subtitle="v2 engine adoption S-curves overlaid" />
                        <${AdoptionOverlay} items=${items} />
                    </div>
                `}

                <!-- Delta-Highlighted Tables -->
                <${DeltaTable} title="Financial Comparison" metrics=${financialMetrics}
                    items=${items} dataKey="financial" />

                <${DeltaTable} title="Workforce Comparison" metrics=${workforceMetrics}
                    items=${items} dataKey="workforce" />

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <${DeltaTable} title="Risk Comparison" metrics=${riskMetrics}
                        items=${items} dataKey="risk" />
                    <${DeltaTable} title="Skills Comparison" metrics=${skillsMetrics}
                        items=${items} dataKey="skills" />
                </div>

                <!-- Trade-off Summary -->
                ${comparison.trade_off_summary && html`
                    <div class="bg-gradient-to-r from-gray-50 to-white rounded-xl border border-gray-200 p-5">
                        <${SectionHeader} title="Trade-off Summary" />
                        <p class="text-sm text-gray-700 leading-relaxed">${comparison.trade_off_summary}</p>
                    </div>
                `}
            </div>
        `;
    }

    // ── Main Comparison View ─────────────────────────────────────────

    function Comparison({ addScenarioId, onNavigate }) {
        const [scenarios, setScenarios] = useState([]);
        const [selectedIds, setSelectedIds] = useState([]);
        const [comparison, setComparison] = useState(null);
        const [loading, setLoading] = useState(true);
        const [comparing, setComparing] = useState(false);
        const [error, setError] = useState(null);
        const [selectorCollapsed, setSelectorCollapsed] = useState(false);

        useEffect(() => {
            api.get("/scenarios")
                .then(d => {
                    const list = d.scenarios || [];
                    setScenarios(list);
                    // Start with nothing selected, unless navigated with addScenarioId
                    if (addScenarioId) {
                        setSelectedIds([addScenarioId]);
                    }
                    setLoading(false);
                })
                .catch(e => { setError(e.message); setLoading(false); });
        }, []);

        const toggleScenario = (id) => {
            setSelectedIds(prev => {
                if (prev.includes(id)) return prev.filter(x => x !== id);
                if (prev.length >= MAX_SELECTIONS) return prev;
                return [...prev, id];
            });
            setComparison(null);
        };

        const clearSelection = () => {
            setSelectedIds([]);
            setComparison(null);
        };

        const runComparison = async () => {
            if (selectedIds.length < 2) {
                setError("Select at least 2 scenarios to compare");
                return;
            }
            setComparing(true);
            setError(null);
            try {
                const data = await api.post("/compare", { scenario_ids: selectedIds });
                if (data.comparison?.error) {
                    setError(data.comparison.error);
                } else {
                    setComparison(data.comparison);
                    setSelectorCollapsed(true);
                }
            } catch (e) {
                setError(e.message || "Comparison failed");
            } finally {
                setComparing(false);
            }
        };

        // Compute selected index for color assignment
        const selectedColorIndex = (id) => selectedIds.indexOf(id);

        if (loading) return html`
            <div class="space-y-4">
                <${LoadingState} type="cards" count=${2} />
                <${LoadingState} type="chart" />
            </div>
        `;

        const completedScenarios = scenarios
            .filter(s => s.status === "completed")
            .sort((a, b) => (b.created_at || 0) - (a.created_at || 0))
            .slice(0, 10);
        const atLimit = selectedIds.length >= MAX_SELECTIONS;

        return html`
            <div class="fade-in space-y-6">
                <!-- Header -->
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-2xl font-bold text-gray-900">Scenario Comparison</h1>
                        <p class="text-sm text-gray-500">Select 2\u2013${MAX_SELECTIONS} scenarios to compare side-by-side</p>
                    </div>
                    ${selectedIds.length >= 2 && !comparing && html`
                        <button onClick=${runComparison}
                            class="bg-brand-600 text-white px-5 py-2.5 rounded-lg hover:bg-brand-700 transition text-sm font-medium flex items-center gap-2 shadow-sm">
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                            </svg>
                            Compare ${selectedIds.length} Scenarios
                        </button>
                    `}
                </div>

                ${error && html`<${ErrorBox} message=${error} />`}

                <!-- Scenario Selector -->
                <div class="bg-white rounded-xl border border-gray-200 p-6">
                    <div class="flex items-center justify-between cursor-pointer"
                        onClick=${() => setSelectorCollapsed(!selectorCollapsed)}>
                        <div class="flex items-center gap-3">
                            <span class="text-gray-400 text-xs select-none">${selectorCollapsed ? '\u25B6' : '\u25BC'}</span>
                            <div>
                                <h3 class="text-base font-semibold text-gray-900">Select Scenarios</h3>
                                ${completedScenarios.length > 0 && html`
                                    <p class="text-xs text-gray-500 mt-0.5">
                                        ${selectedIds.length} of ${MAX_SELECTIONS} slots used
                                        ${selectorCollapsed && selectedIds.length >= 2
                                            ? html` \u2014 <span class="text-brand-600 font-medium">${selectedIds.length} selected</span>`
                                            : atLimit ? html` \u2014 <span class="text-amber-600 font-medium">limit reached</span>` : ''}
                                    </p>
                                `}
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            ${selectedIds.length > 0 && !selectorCollapsed && html`
                                <button onClick=${(e) => { e.stopPropagation(); clearSelection(); }}
                                    class="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded border border-gray-200 hover:bg-gray-50 transition">
                                    Clear all
                                </button>
                            `}
                            <!-- Selection counter pills -->
                            <div class="flex items-center gap-1">
                                ${Array.from({length: MAX_SELECTIONS}).map((_, i) => html`
                                    <div key=${i}
                                        class="w-2 h-2 rounded-full transition-colors
                                            ${i < selectedIds.length
                                                ? ''
                                                : 'bg-gray-200'}"
                                        style=${{backgroundColor: i < selectedIds.length
                                            ? SCENARIO_COLORS[i % SCENARIO_COLORS.length]
                                            : undefined}}>
                                    </div>
                                `)}
                            </div>
                        </div>
                    </div>

                    ${!selectorCollapsed && (completedScenarios.length === 0 ? html`
                        <${EmptyState}
                            icon="simulation"
                            title="No completed scenarios"
                            message="Run at least two simulations to compare their results side-by-side."
                            actionLabel="Run Simulation \u2192"
                            onAction=${() => onNavigate("simulator")}
                        />
                    ` : html`
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                            ${completedScenarios.map(s => html`
                                <${ScenarioCard}
                                    key=${s.id}
                                    scenario=${s}
                                    selected=${selectedIds.includes(s.id)}
                                    disabled=${atLimit && !selectedIds.includes(s.id)}
                                    colorIndex=${selectedColorIndex(s.id)}
                                    onToggle=${toggleScenario}
                                />
                            `)}
                        </div>

                        <!-- Action bar -->
                        <div class="mt-5 flex items-center justify-between border-t border-gray-100 pt-4">
                            <div class="text-sm text-gray-500">
                                ${selectedIds.length === 0 && 'Pick scenarios to begin'}
                                ${selectedIds.length === 1 && 'Select at least 1 more scenario'}
                                ${selectedIds.length >= 2 && html`
                                    <span class="text-brand-600 font-medium">Ready to compare</span>
                                `}
                            </div>
                            <button onClick=${runComparison}
                                disabled=${selectedIds.length < 2 || comparing}
                                class="px-5 py-2.5 rounded-lg text-sm font-medium text-white transition flex items-center gap-2
                                    ${selectedIds.length < 2 || comparing
                                        ? 'bg-gray-300 cursor-not-allowed'
                                        : 'bg-brand-600 hover:bg-brand-700 shadow-sm'}">
                                ${comparing ? html`
                                    <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                    </svg>
                                    Comparing...
                                ` : html`
                                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                                    </svg>
                                    Compare ${selectedIds.length} Scenarios
                                `}
                            </button>
                        </div>
                    `)}
                </div>

                <!-- Comparison Results -->
                ${comparison && !comparison.error && html`
                    <${ComparisonResults} comparison=${comparison} />
                `}

                ${comparison?.error && html`<${ErrorBox} message=${comparison.error} />`}
            </div>
        `;
    }

    window.DT.Comparison = Comparison;
})();
