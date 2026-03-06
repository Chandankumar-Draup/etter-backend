/**
 * Results View - Display simulation cascade results.
 *
 * 7 tabs: Overview (radar + insights), Financial (waterfall + timeline),
 * Workforce (headcount bars + redeployment flow), Skills (demand donut),
 * Risks (risk matrix), Details (cascade animation + Sankey),
 * Trajectory (v2 only: adoption S-curve, human factors, financial trajectory, feedback loops).
 */

(function () {
    const { html, useState, useEffect, api, fmt,
            MetricCard, Badge, Spinner, ErrorBox, SectionHeader,
            DataTable, ChartCanvas, EmptyState, CHART_COLORS,
            WaterfallChart, TimelineChart, HeadcountCompareChart,
            RedeploymentFlow, CascadeFlow, SankeyDiagram, RiskMatrix,
            TaskDistributionDonut,
            AdoptionSCurve, HumanFactorsChart, FinancialTrajectory,
            FeedbackLoopTimeline, MilestoneCards } = window.DT;

    function Results({ scenarioId, result: propResult, config: propConfig, onNavigate }) {
        const [result, setResult] = useState(propResult);
        const [config, setConfig] = useState(propConfig);
        const [loading, setLoading] = useState(!propResult);
        const [error, setError] = useState(null);
        const [activeTab, setActiveTab] = useState("overview");

        useEffect(() => {
            if (propResult) return;
            if (!scenarioId) { setError("No scenario specified"); setLoading(false); return; }
            setLoading(true);
            api.get(`/scenarios/${scenarioId}`)
                .then(d => {
                    const s = d.scenario;
                    setResult(s.result);
                    setConfig(s.config);
                    setLoading(false);
                })
                .catch(e => { setError(e.message); setLoading(false); });
        }, [scenarioId]);

        if (loading) return html`<${Spinner} text="Loading results..." />`;
        if (error) return html`<${ErrorBox} message=${error} />`;
        if (!result) return html`
            <${EmptyState} icon="chart" title="No results available"
                message="Run a simulation to see cascade results here."
                actionLabel="Run Simulation" onAction=${() => onNavigate("simulator")} />
        `;

        const cascade = result.cascade;
        if (!cascade) {
            return html`
                <div class="fade-in space-y-4">
                    <h1 class="text-2xl font-bold text-gray-900">Simulation Results</h1>
                    <${ErrorBox} message="No cascade results. The simulation scope may have no matching tasks." />
                </div>
            `;
        }

        // Detect v2 engine
        const isV2 = result.engine === "v2_time_stepped";
        const snapshots = result.monthly_snapshots || [];
        const trajSummary = result.trajectory_summary || {};
        const milestones = result.milestones || [];

        const fin = cascade.financial || {};
        const wf = cascade.workforce || {};
        const risks = cascade.risks || {};
        const summary = cascade.summary || {};
        const skills = result.skills_strategy?.summary || {};
        const roleImpacts = cascade.role_impacts?.impacts || [];
        const taskChanges = cascade.task_changes?.changes || [];
        const techInfo = result.technology;
        const recommendation = result.recommendation;

        const tabs = [
            { id: "overview", label: "Overview", icon: "\u{1F4CA}" },
            { id: "financial", label: "Financial", icon: "\u{1F4B0}" },
            { id: "workforce", label: "Workforce", icon: "\u{1F465}" },
            { id: "skills", label: "Skills", icon: "\u{1F4A1}" },
            { id: "risks", label: `Risks (${risks.risk_count || 0})`, icon: "\u26A0\uFE0F" },
            { id: "details", label: "Details", icon: "\u{1F50D}" },
            ...(isV2 ? [{ id: "trajectory", label: "Trajectory", icon: "\u{1F4C8}" }] : []),
        ];

        return html`
            <div class="fade-in space-y-4">
                <!-- Header -->
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-2xl font-bold text-gray-900">
                            ${config?.name || "Simulation Results"}
                        </h1>
                        <div class="flex gap-2 mt-1">
                            <${Badge} text=${(config?.simulation_type || result.simulation_type || "").replace(/_/g, " ")} color="blue" />
                            ${isV2 && html`<${Badge} text="v2 Engine" color="blue" />`}
                            ${techInfo && html`<${Badge} text=${techInfo.name} color="blue" />`}
                            ${recommendation && html`
                                <${Badge}
                                    text=${recommendation.verdict.replace(/_/g, " ")}
                                    color=${recommendation.verdict === "STRONG_RECOMMEND" || recommendation.verdict === "RECOMMEND" ? "green"
                                          : recommendation.verdict === "CONDITIONAL" ? "amber" : "red"}
                                />
                            `}
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <button onClick=${() => onNavigate("comparison", { addScenarioId: scenarioId })}
                            class="text-sm px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-50 transition">
                            Compare
                        </button>
                        <button onClick=${() => onNavigate("simulator")}
                            class="text-sm px-3 py-1.5 rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition">
                            New Simulation
                        </button>
                    </div>
                </div>

                <!-- Tabs -->
                <div class="flex gap-1 border-b border-gray-200 overflow-x-auto">
                    ${tabs.map(tab => html`
                        <button key=${tab.id}
                            onClick=${() => setActiveTab(tab.id)}
                            class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition border-b-2 whitespace-nowrap
                                ${activeTab === tab.id
                                    ? "border-brand-600 text-brand-700"
                                    : "border-transparent text-gray-500 hover:text-gray-700"}">
                            <span class="text-xs">${tab.icon}</span>
                            ${tab.label}
                        </button>
                    `)}
                </div>

                <!-- Tab Content -->
                ${activeTab === "overview" && html`<${OverviewTab} summary=${summary} fin=${fin} wf=${wf} risks=${risks} skills=${skills} recommendation=${recommendation} config=${config} isV2=${isV2} trajSummary=${trajSummary} />`}
                ${activeTab === "financial" && html`<${FinancialTab} fin=${fin} config=${config} result=${result} isV2=${isV2} snapshots=${snapshots} trajSummary=${trajSummary} />`}
                ${activeTab === "workforce" && html`<${WorkforceTab} wf=${wf} roleImpacts=${roleImpacts} />`}
                ${activeTab === "skills" && html`<${SkillsTab} skills=${skills} strategy=${result.skills_strategy} />`}
                ${activeTab === "risks" && html`<${RisksTab} risks=${risks} />`}
                ${activeTab === "details" && html`<${DetailsTab} taskChanges=${taskChanges} roleImpacts=${roleImpacts} cascade=${cascade} />`}
                ${activeTab === "trajectory" && isV2 && html`<${TrajectoryTab} snapshots=${snapshots} milestones=${milestones} trajSummary=${trajSummary} />`}
            </div>
        `;
    }

    // ── Overview Tab ──────────────────────────────────────────────────

    function OverviewTab({ summary, fin, wf, risks, skills, recommendation, config, isV2, trajSummary }) {
        // Radar chart data
        const radarData = {
            labels: ['Financial Impact', 'Workforce Efficiency', 'Skills Growth', 'Low Risk', 'ROI'],
            datasets: [{
                label: config?.name || 'Simulation',
                data: [
                    Math.min(100, Math.abs(fin.net_impact || 0) / Math.max(1, fin.gross_savings || 1) * 100),
                    Math.min(100, (wf.reduction_pct || 0) * 2),
                    Math.min(100, (skills.sunrise_count || 0) * 15),
                    Math.max(0, 100 - (risks.high_risks || 0) * 40),
                    Math.min(100, (fin.roi_pct || 0) / 20),
                ],
                borderColor: CHART_COLORS.info,
                backgroundColor: CHART_COLORS.info + '25',
                pointBackgroundColor: CHART_COLORS.info,
                pointRadius: 4,
            }],
        };

        const radarOpts = {
            scales: { r: { beginAtZero: true, max: 100, ticks: { stepSize: 25, display: false }, pointLabels: { font: { size: 11 } } } },
            plugins: { legend: { display: false } },
        };

        return html`
            <div class="space-y-4">
                <!-- Key metrics -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <${MetricCard} label="Tasks Affected" value=${summary.tasks_affected} color="blue" icon="\u2699\uFE0F" />
                    <${MetricCard} label="Roles Affected" value=${summary.roles_affected} color="blue" icon="\u{1F465}" />
                    <${MetricCard} label="Freed Headcount" value=${Math.round(summary.freed_headcount || 0)} color="blue" icon="\u{1F464}" />
                    <${MetricCard} label="Net Savings" value=${fmt.currency(summary.net_impact)} color="green" icon="\u{1F4B0}" />
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <!-- Radar -->
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Impact Dimensions" />
                        <${ChartCanvas} type="radar" data=${radarData} options=${radarOpts} height="280px" />
                    </div>

                    <!-- Key Insights -->
                    <div class="space-y-3">
                        <!-- Before/After -->
                        <div class="bg-white rounded-xl border border-gray-200 p-4">
                            <${SectionHeader} title="Headcount Impact" />
                            <div class="flex items-center justify-around py-3">
                                <div class="text-center">
                                    <div class="text-3xl font-bold text-gray-900">${fmt.number(Math.round(wf.current_headcount || 0))}</div>
                                    <div class="text-xs text-gray-500 mt-1">Current</div>
                                </div>
                                <svg class="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>
                                <div class="text-center">
                                    <div class="text-3xl font-bold" style=${{color: CHART_COLORS.ai}}>${fmt.number(Math.round((wf.current_headcount || 0) - (wf.freed_headcount || 0)))}</div>
                                    <div class="text-xs text-gray-500 mt-1">Projected</div>
                                </div>
                                <div class="text-center px-3 py-1 bg-amber-50 rounded-lg border border-amber-200">
                                    <div class="text-xl font-bold text-amber-700">-${fmt.pct(wf.reduction_pct)}</div>
                                    <div class="text-xs text-amber-600">Reduction</div>
                                </div>
                            </div>
                        </div>

                        <!-- Recommendation -->
                        ${recommendation && html`
                            <div class="bg-white rounded-xl border border-gray-200 p-4">
                                <${SectionHeader} title="AI Recommendation" />
                                <div class="flex items-start gap-3">
                                    <span class="text-2xl">${recommendation.verdict === "STRONG_RECOMMEND" ? "\u2705" :
                                        recommendation.verdict === "RECOMMEND" ? "\u{1F44D}" :
                                        recommendation.verdict === "CONDITIONAL" ? "\u{1F914}" : "\u26A0\uFE0F"}</span>
                                    <div>
                                        <${Badge} text=${recommendation.verdict.replace(/_/g, " ")}
                                            color=${recommendation.verdict.includes("RECOMMEND") ? "green" : recommendation.verdict === "CONDITIONAL" ? "amber" : "red"} />
                                        <p class="text-sm text-gray-700 mt-2">${recommendation.reasoning}</p>
                                    </div>
                                </div>
                            </div>
                        `}

                        <!-- Financial highlight -->
                        <div class="grid grid-cols-2 gap-3">
                            <${MetricCard} label="ROI" value=${fmt.pct(fin.roi_pct)} color="blue" icon="\u{1F4C8}" />
                            <${MetricCard} label="Payback" value="${fin.payback_months || 0} months" color="blue" />
                        </div>
                    </div>
                </div>

                <!-- v2: Theoretical vs Actual -->
                ${isV2 && trajSummary?.actual_at_end && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Theoretical Max vs Actual (36 months)"
                            subtitle="v2 engine accounts for adoption S-curve, human factors, and feedback loops" />
                        <div class="grid grid-cols-2 gap-4">
                            <!-- Theoretical -->
                            <div class="rounded-lg border border-gray-200 p-4 bg-gray-50">
                                <div class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">Theoretical Maximum</div>
                                <div class="space-y-3">
                                    <div class="flex justify-between items-center">
                                        <span class="text-sm text-gray-600">Freed Headcount</span>
                                        <span class="font-semibold text-gray-900">${fmt.number(Math.round(trajSummary.theoretical_max?.freed_headcount || summary.freed_headcount || 0))}</span>
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <span class="text-sm text-gray-600">Gross Savings</span>
                                        <span class="font-semibold text-gray-900">${fmt.currency(trajSummary.theoretical_max?.gross_savings || fin.gross_savings)}</span>
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <span class="text-sm text-gray-600">Adoption</span>
                                        <span class="font-semibold text-gray-900">100%</span>
                                    </div>
                                </div>
                            </div>
                            <!-- Actual -->
                            <div class="rounded-lg border border-brand-200 p-4 bg-brand-50">
                                <div class="text-xs font-medium text-brand-600 uppercase tracking-wide mb-3">Actual at Month 36</div>
                                <div class="space-y-3">
                                    <div class="flex justify-between items-center">
                                        <span class="text-sm text-gray-600">Freed Headcount</span>
                                        <span class="font-semibold text-brand-700">${fmt.number(Math.round(trajSummary.actual_at_end.effective_freed_hc || 0))}</span>
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <span class="text-sm text-gray-600">Net Savings</span>
                                        <span class="font-semibold text-brand-700">${fmt.currency(trajSummary.actual_at_end.cumulative_net || 0)}</span>
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <span class="text-sm text-gray-600">Adoption</span>
                                        <span class="font-semibold text-brand-700">${fmt.pct((trajSummary.actual_at_end.adoption_level || 0) * 100)}</span>
                                    </div>
                                    <div class="flex justify-between items-center">
                                        <span class="text-sm text-gray-600">NPV</span>
                                        <span class="font-semibold text-brand-700">${fmt.currency(trajSummary.actual_at_end.npv || 0)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <!-- Key v2 metrics -->
                        <div class="grid grid-cols-3 gap-3 mt-3">
                            <${MetricCard} label="Breakeven" value="Month ${trajSummary.breakeven_month || '—'}" color="blue" />
                            <${MetricCard} label="Payback" value="Month ${trajSummary.payback_month || '—'}" color="green" />
                            <${MetricCard} label="ROI" value=${fmt.pct(trajSummary.actual_at_end.roi_pct || 0)} color="blue" />
                        </div>
                    </div>
                `}
            </div>
        `;
    }

    // ── Financial Tab ─────────────────────────────────────────────────

    function FinancialTab({ fin, config, result, isV2, snapshots, trajSummary }) {
        const titleDetails = fin.title_details || [];

        return html`
            <div class="space-y-4">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <${MetricCard} label="Gross Savings" value=${fmt.currency(fin.gross_savings)} color="green" icon="\u{1F4B5}" />
                    <${MetricCard} label="Total Cost" value=${fmt.currency(fin.total_cost)} color="red" icon="\u{1F4B8}" />
                    <${MetricCard} label="Net Impact" value=${fmt.currency(isV2 ? (trajSummary?.actual_at_end?.cumulative_net || fin.net_impact) : fin.net_impact)}
                        color=${((isV2 ? trajSummary?.actual_at_end?.cumulative_net : fin.net_impact) || 0) >= 0 ? "green" : "red"}
                        sub=${isV2 ? "v2 actual (36 months)" : ((fin.net_impact || 0) < 0 ? "Net cost" : "Net savings")} />
                    <${MetricCard} label="ROI" value=${fmt.pct(isV2 ? (trajSummary?.actual_at_end?.roi_pct || fin.roi_pct) : fin.roi_pct)}
                        sub="Payback: ${isV2 ? (trajSummary?.payback_month || '—') : fin.payback_months} months" color="blue" icon="\u{1F4C8}" />
                </div>

                <!-- Waterfall Chart -->
                <div class="bg-white rounded-xl border border-gray-200 p-4">
                    <${SectionHeader} title="Financial Waterfall" subtitle="Savings cascade minus costs" />
                    <${WaterfallChart} fin=${fin} height="300px" />
                </div>

                <!-- Financial Trajectory (v2) or Timeline (v1) -->
                ${isV2 && snapshots.length > 0 ? html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Financial Trajectory (v2)"
                            subtitle="Real monthly savings, costs, and net impact over ${snapshots.length} months" />
                        <${FinancialTrajectory} snapshots=${snapshots}
                            paybackMonth=${trajSummary?.payback_month} />
                    </div>
                ` : html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Savings Timeline"
                            subtitle="Cumulative savings vs investment over ${config?.timeline_months || 36} months" />
                        <${TimelineChart} fin=${fin}
                            timelineMonths=${config?.timeline_months || 36}
                            adoptionCurve=${result?.adoption_curve} />
                    </div>
                `}

                <!-- Cost Breakdown -->
                <div class="bg-white rounded-xl border border-gray-200 p-4">
                    <${SectionHeader} title="Cost Breakdown" />
                    <div class="grid grid-cols-3 gap-3">
                        <${MetricCard} label="Technology Licensing" value=${fmt.currency(fin.technology_licensing)} color="red" />
                        <${MetricCard} label="Implementation" value=${fmt.currency(fin.implementation_cost)} color="red" />
                        <${MetricCard} label="Reskilling" value=${fmt.currency(fin.reskilling_cost)} color="red" />
                    </div>
                </div>

                ${titleDetails.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Per-Title Impact" subtitle="${titleDetails.length} job titles affected" />
                        <${DataTable}
                            columns=${[
                                { key: "title", label: "Job Title" },
                                { key: "headcount", label: "HC" },
                                { key: "avg_salary", label: "Avg Salary", render: r => fmt.currency(r.avg_salary) },
                                { key: "freed_capacity_pct", label: "Freed %", render: r => html`
                                    <span class="${r.freed_capacity_pct > 40 ? 'text-red-600 font-semibold' : ''}">${fmt.pct(r.freed_capacity_pct)}</span>
                                ` },
                                { key: "savings", label: "Savings", render: r => html`
                                    <span class="text-green-700 font-medium">${fmt.currency(r.savings)}</span>
                                ` },
                            ]}
                            rows=${titleDetails}
                        />
                    </div>
                `}
            </div>
        `;
    }

    // ── Workforce Tab ─────────────────────────────────────────────────

    function WorkforceTab({ wf, roleImpacts }) {
        return html`
            <div class="space-y-4">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <${MetricCard} label="Current Headcount" value=${fmt.number(Math.round(wf.current_headcount || 0))} color="blue" icon="\u{1F465}" />
                    <${MetricCard} label="Freed Headcount" value=${fmt.number(Math.round(wf.freed_headcount || 0))} color="blue" icon="\u{1F53B}" />
                    <${MetricCard} label="Reduction" value=${fmt.pct(wf.reduction_pct)} color="red" />
                    <${MetricCard} label="Redeployable" value=${fmt.number(Math.round(wf.redeployable || 0))}
                        sub=${fmt.pct(wf.redeployable_pct)} color="green" icon="\u2705" />
                </div>

                <!-- Redeployment Flow -->
                <div class="bg-white rounded-xl border border-gray-200 p-4">
                    <${SectionHeader} title="Workforce Transition Flow" subtitle="How freed headcount gets redistributed" />
                    <${RedeploymentFlow} workforce=${wf} />
                </div>

                <!-- Headcount Before/After Chart -->
                ${roleImpacts.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Role Impact" subtitle="Current vs projected headcount by role" />
                        <${HeadcountCompareChart} roleImpacts=${roleImpacts} />
                    </div>
                `}

                <!-- Role Impact Table with color-coded transform index -->
                ${roleImpacts.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Transformation Index" subtitle="${roleImpacts.length} roles affected" />
                        <${DataTable}
                            columns=${[
                                { key: "role_name", label: "Role" },
                                { key: "freed_capacity_pct", label: "Freed %",
                                  render: r => html`
                                    <span class="${r.freed_capacity_pct > 40 ? 'text-red-600 font-semibold' : r.freed_capacity_pct > 20 ? 'text-amber-600 font-medium' : ''}">
                                        ${fmt.pct(r.freed_capacity_pct)}
                                    </span>
                                ` },
                                { key: "transformation_index", label: "Transform Index",
                                  render: r => {
                                    const ti = r.transformation_index || 0;
                                    const barColor = ti > 60 ? 'bg-red-500' : ti > 30 ? 'bg-amber-500' : 'bg-green-500';
                                    return html`
                                        <div class="flex items-center gap-2">
                                            <div class="w-20 bg-gray-200 rounded-full h-2.5">
                                                <div class="${barColor} h-2.5 rounded-full transition-all duration-500"
                                                     style=${{width: `${Math.min(100, ti)}%`}}></div>
                                            </div>
                                            <span class="text-xs font-medium ${ti > 60 ? 'text-red-600' : ti > 30 ? 'text-amber-600' : 'text-green-600'}">${Math.round(ti)}</span>
                                        </div>
                                    `;
                                  } },
                                { key: "title_count", label: "Titles",
                                  render: r => (r.title_impacts || []).length },
                            ]}
                            rows=${roleImpacts}
                        />
                    </div>
                `}
            </div>
        `;
    }

    // ── Skills Tab ────────────────────────────────────────────────────

    function SkillsTab({ skills, strategy }) {
        const demand = strategy?.demand_analysis || {};
        const reskilling = strategy?.reskilling_plan || {};
        const buildBuy = strategy?.build_vs_buy?.recommendations || [];

        // Demand donut data
        const sunrise = (demand.sunrise || []).length;
        const sunset = (demand.sunset || []).length;
        const stable = (demand.stable || []).length;
        const hasSkillsData = sunrise + sunset + stable > 0;

        const demandData = hasSkillsData ? {
            labels: ['Sunrise (Growing)', 'Sunset (Declining)', 'Stable'],
            datasets: [{ data: [sunrise, sunset, stable], backgroundColor: [CHART_COLORS.positive, CHART_COLORS.negative, CHART_COLORS.info], borderWidth: 2, borderColor: '#fff' }],
        } : null;

        return html`
            <div class="space-y-4">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <${MetricCard} label="Sunrise Skills" value=${skills.sunrise_count || 0} color="green" icon="\u2191" />
                    <${MetricCard} label="Sunset Skills" value=${skills.sunset_count || 0} color="red" icon="\u2193" />
                    <${MetricCard} label="High-Risk Skills" value=${skills.high_risk_skills || 0} color="amber" icon="\u26A0\uFE0F" />
                    <${MetricCard} label="Reskilling Cost" value=${fmt.currency(skills.total_reskilling_cost)} color="blue"
                        sub="~${skills.avg_reskilling_months || 0} months avg" />
                </div>

                <!-- Skills Demand Distribution -->
                ${demandData && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Skills Demand Shift" subtitle="Distribution of skill lifecycle changes" />
                        <div class="max-w-xs mx-auto">
                            <${ChartCanvas} type="doughnut" data=${demandData}
                                options=${{ cutout: '55%', plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } } } }}
                                height="220px" />
                        </div>
                    </div>
                `}

                ${(demand.sunrise || []).length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Sunrise Skills" subtitle="Emerging skills with growing demand" />
                        <div class="flex flex-wrap gap-2">
                            ${demand.sunrise.map(s => html`
                                <${Badge} key=${s.name} text=${s.name}
                                    color=${s.priority === "high" ? "green" : "blue"} />
                            `)}
                        </div>
                    </div>
                `}

                ${(demand.sunset || []).length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Sunset Skills" subtitle="Declining skills to phase out" />
                        <div class="flex flex-wrap gap-2">
                            ${demand.sunset.map(s => html`
                                <${Badge} key=${s.name} text=${s.name} color="red" />
                            `)}
                        </div>
                    </div>
                `}

                ${buildBuy.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Build vs Buy Recommendations" />
                        <${DataTable}
                            columns=${[
                                { key: "skill", label: "Skill" },
                                { key: "action", label: "Recommendation",
                                  render: r => html`<${Badge} text=${r.action.replace(/_/g, " ")}
                                    color=${r.action === "build" ? "green" : r.action === "buy" ? "blue" : "amber"} />` },
                                { key: "reasoning", label: "Reasoning" },
                            ]}
                            rows=${buildBuy}
                        />
                    </div>
                `}

                <!-- Reskilling Timeline -->
                ${reskilling.skills && reskilling.skills.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Reskilling Timeline"
                            subtitle="Estimated ${reskilling.timeline_months || 0} months total" />
                        <div class="space-y-2">
                            ${reskilling.skills.slice(0, 8).map(s => html`
                                <div key=${s.skill || s.name} class="flex items-center gap-3">
                                    <span class="text-sm text-gray-700 w-40 truncate">${s.skill || s.name}</span>
                                    <div class="flex-1 bg-gray-100 rounded-full h-4 relative">
                                        <div class="bg-brand-500 h-4 rounded-full flex items-center justify-end pr-2"
                                             style=${{width: `${Math.min(100, ((s.months || s.timeline_months || 3) / (reskilling.timeline_months || 12)) * 100)}%`}}>
                                            <span class="text-[10px] text-white font-medium">${s.months || s.timeline_months || 3}mo</span>
                                        </div>
                                    </div>
                                    ${s.cost && html`<span class="text-xs text-gray-500 w-16 text-right">${fmt.currency(s.cost)}</span>`}
                                </div>
                            `)}
                        </div>
                    </div>
                `}
            </div>
        `;
    }

    // ── Risks Tab ─────────────────────────────────────────────────────

    function RisksTab({ risks }) {
        const flags = risks.flags || [];

        return html`
            <div class="space-y-4">
                <div class="grid grid-cols-2 gap-3">
                    <${MetricCard} label="Total Risk Flags" value=${risks.risk_count || 0} color="amber" icon="\u26A0\uFE0F" />
                    <${MetricCard} label="High Severity" value=${risks.high_risks || 0} color="red" icon="\u{1F534}" />
                </div>

                <!-- Risk Matrix -->
                ${flags.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Risk Matrix" subtitle="Severity vs Impact assessment" />
                        <div class="flex justify-center">
                            <${RiskMatrix} risks=${risks} />
                        </div>
                        <!-- Legend -->
                        <div class="mt-3 flex flex-wrap gap-2 justify-center">
                            ${flags.map((f, i) => html`
                                <span key=${i} class="text-xs px-2 py-1 bg-gray-100 rounded-full text-gray-600">
                                    ${i+1}. ${(f.type || '').replace(/_/g, ' ')}
                                </span>
                            `)}
                        </div>
                    </div>
                `}

                ${flags.length > 0 ? html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Risk Details" />
                        <div class="space-y-2">
                            ${flags.map((f, i) => html`
                                <div key=${i} class="flex items-start gap-3 p-3 rounded-lg border
                                    ${f.severity === "high" ? "border-red-200 bg-red-50" : "border-amber-200 bg-amber-50"}">
                                    <${Badge} text=${f.severity} color=${fmt.severity(f.severity)} />
                                    <div class="flex-1">
                                        <div class="text-sm font-medium text-gray-900">
                                            ${(f.type || "").replace(/_/g, " ")}
                                        </div>
                                        <div class="text-xs text-gray-600 mt-0.5">${f.detail}</div>
                                        ${f.entity && html`
                                            <div class="text-xs text-gray-400 mt-0.5">Entity: ${f.entity}</div>
                                        `}
                                        <div class="text-xs text-gray-500 mt-1.5 italic">
                                            ${f.severity === "high"
                                                ? "Mitigation: Consider phased rollout with close monitoring and fallback plan."
                                                : "Mitigation: Monitor metrics quarterly and adjust automation parameters if needed."}
                                        </div>
                                    </div>
                                </div>
                            `)}
                        </div>
                    </div>
                ` : html`
                    <div class="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
                        <div class="text-2xl mb-2">\u2705</div>
                        <div class="text-green-700 font-medium">No risk flags detected</div>
                        <div class="text-sm text-green-600 mt-1">The simulation shows acceptable risk levels</div>
                    </div>
                `}
            </div>
        `;
    }

    // ── Details Tab ───────────────────────────────────────────────────

    function DetailsTab({ taskChanges, roleImpacts, cascade }) {
        const workloadChanges = cascade?.workload_changes?.changes || [];

        return html`
            <div class="space-y-4">
                <!-- Animated Cascade Flow -->
                <div class="bg-white rounded-xl border border-gray-200 p-4">
                    <${SectionHeader} title="Cascade Propagation" subtitle="8-step impact flow \u2014 watch the cascade unfold" />
                    <${CascadeFlow} cascade=${cascade} />
                </div>

                <!-- Task Reclassification Sankey -->
                ${taskChanges.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Task Automation Flow"
                            subtitle="How ${taskChanges.length} tasks shifted automation levels" />
                        <${SankeyDiagram} taskChanges=${taskChanges} height=${280} />
                    </div>
                `}

                ${taskChanges.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Task Reclassifications" subtitle="${taskChanges.length} tasks changed" />
                        <${DataTable}
                            columns=${[
                                { key: "task_name", label: "Task" },
                                { key: "old_level", label: "From",
                                  render: r => html`<${Badge} text=${(r.old_level || "").replace(/_/g, " ")} color="gray" />` },
                                { key: "new_level", label: "To",
                                  render: r => html`<${Badge} text=${(r.new_level || "").replace(/_/g, " ")}
                                    color=${r.new_level === "ai_only" || r.new_level === "ai_led" ? "green" :
                                           r.new_level === "shared" ? "amber" : "gray"} />` },
                                { key: "automation_delta", label: "Delta",
                                  render: r => html`<span class="text-green-600 font-medium">+${((r.automation_delta || 0) * 100).toFixed(0)}%</span>` },
                            ]}
                            rows=${taskChanges.slice(0, 30)}
                        />
                        ${taskChanges.length > 30 && html`
                            <p class="text-xs text-gray-400 mt-2">Showing first 30 of ${taskChanges.length}</p>
                        `}
                    </div>
                `}

                ${workloadChanges.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Workload Shifts" subtitle="${workloadChanges.length} workloads affected" />
                        <${DataTable}
                            columns=${[
                                { key: "workload_name", label: "Workload" },
                                { key: "old_level", label: "From",
                                  render: r => html`<${Badge} text=${(r.old_level || "").replace(/_/g, " ")} color="gray" />` },
                                { key: "new_level", label: "To",
                                  render: r => html`<${Badge} text=${(r.new_level || "").replace(/_/g, " ")} color="green" />` },
                                { key: "automation_score", label: "Score",
                                  render: r => `${Math.round(r.automation_score || 0)}%` },
                            ]}
                            rows=${workloadChanges}
                        />
                    </div>
                `}
            </div>
        `;
    }

    // ── Trajectory Tab (v2 only) ─────────────────────────────────

    function TrajectoryTab({ snapshots, milestones, trajSummary }) {
        const actual = trajSummary?.actual_at_end || {};
        const hfFinal = trajSummary?.human_factors_final || {};

        return html`
            <div class="space-y-4">
                <!-- Milestone Cards -->
                ${milestones.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Key Milestones"
                            subtitle="Snapshot at critical months along the adoption journey" />
                        <${MilestoneCards} milestones=${milestones} />
                    </div>
                `}

                <!-- Adoption S-Curve -->
                ${snapshots.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Adoption S-Curve"
                            subtitle="Bass diffusion model modulated by human factors" />
                        <${AdoptionSCurve} snapshots=${snapshots}
                            breakevenMonth=${trajSummary?.breakeven_month} />
                    </div>
                `}

                <!-- Human Factors Evolution -->
                ${snapshots.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Human Factors Evolution"
                            subtitle="Resistance, morale, proficiency, and culture over time" />
                        <${HumanFactorsChart} snapshots=${snapshots} />
                        <!-- Final HFM Score -->
                        <div class="grid grid-cols-5 gap-2 mt-3">
                            <${MetricCard} label="Resistance" value=${((hfFinal.resistance || 0) * 100).toFixed(0) + "%"}
                                color="red" sub="Lower is better" />
                            <${MetricCard} label="Morale" value=${((hfFinal.morale || 0) * 100).toFixed(0) + "%"} color="blue" />
                            <${MetricCard} label="Proficiency" value=${((hfFinal.proficiency || 0) * 100).toFixed(0) + "%"} color="green" />
                            <${MetricCard} label="Culture" value=${((hfFinal.culture_readiness || 0) * 100).toFixed(0) + "%"} color="blue" />
                            <${MetricCard} label="HFM Score" value=${((hfFinal.composite_multiplier || 0) * 100).toFixed(0) + "%"}
                                color="blue" sub="Composite" />
                        </div>
                    </div>
                `}

                <!-- Financial Trajectory -->
                ${snapshots.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Financial Trajectory"
                            subtitle="Cumulative savings, costs, and net impact with J-curve" />
                        <${FinancialTrajectory} snapshots=${snapshots}
                            paybackMonth=${trajSummary?.payback_month} />
                    </div>
                `}

                <!-- Feedback Loop Timeline -->
                ${snapshots.length > 0 && html`
                    <div class="bg-white rounded-xl border border-gray-200 p-4">
                        <${SectionHeader} title="Feedback Loop Activity"
                            subtitle="Reinforcing (R) and balancing (B) loops active over time" />
                        <${FeedbackLoopTimeline} snapshots=${snapshots} />
                    </div>
                `}

                <!-- Summary metrics -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <${MetricCard} label="Final Adoption" value=${fmt.pct((actual.adoption_level || 0) * 100)} color="green" icon="\u{1F4C8}" />
                    <${MetricCard} label="Freed HC" value=${fmt.number(Math.round(actual.effective_freed_hc || 0))} color="blue" icon="\u{1F464}" />
                    <${MetricCard} label="Net Present Value" value=${fmt.currency(actual.npv || 0)} color="blue" icon="\u{1F4B0}" />
                    <${MetricCard} label="Total ROI" value=${fmt.pct(actual.roi_pct || 0)} color="blue" icon="\u{1F4CA}" />
                </div>
            </div>
        `;
    }

    window.DT.Results = Results;
})();
