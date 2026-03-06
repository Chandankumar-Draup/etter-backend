/**
 * Simulator View - Configure and run simulations.
 *
 * Streamlined layout: header with preset chips, type+scope row,
 * single config card, sticky run bar, slim sidebar with donut preview.
 */

(function () {
    const { html, useState, useEffect, useMemo, api, fmt,
            MetricCard, Badge, Spinner, ErrorBox, SectionHeader,
            EmptyState, TaskDistributionDonut, CHART_COLORS } = window.DT;

    // ── Preset Scenarios (trimmed to 5 most useful) ─────────────────

    const PRESETS = [
        { label: "Conservative Pilot", icon: "\u{1F331}", type: "role_redesign", factor: 0.3, timeline: 12 },
        { label: "Moderate Adoption",  icon: "\u2696\uFE0F", type: "role_redesign", factor: 0.5, timeline: 36 },
        { label: "Aggressive Transform", icon: "\u{1F680}", type: "role_redesign", factor: 0.8, timeline: 24 },
        { label: "Copilot Rollout",    icon: "\u{1F916}", type: "tech_adoption", tech: "Microsoft Copilot", timeline: 24 },
        { label: "Target 60% AI",      icon: "\u{1F3AF}", type: "task_distribution", dist: { human_only_pct: 5, human_led_pct: 15, shared_pct: 20, ai_led_pct: 40, ai_only_pct: 20 }, timeline: 36 },
    ];

    // ── Simulation Type Definitions ───────────────────────────────────

    const SIM_TYPES = [
        { id: "role_redesign",       label: "Role Redesign",       icon: "\u{1F504}" },
        { id: "tech_adoption",       label: "Tech Adoption",       icon: "\u{1F916}" },
        { id: "multi_tech_adoption", label: "Multi-Tech Deploy",   icon: "\u{1F4BB}" },
        { id: "task_distribution",   label: "Target Distribution", icon: "\u{1F3AF}" },
    ];

    // ── Advanced Settings Component ──────────────────────────────────

    function AdvancedSettings({ settings, onChange }) {
        const [open, setOpen] = useState(false);

        const update = (key, val) => onChange({ ...settings, [key]: val });
        const updateOrg = (key, val) => onChange({
            ...settings,
            organization: { ...settings.organization, [key]: val },
        });

        return html`
            <div class="border-t border-gray-100 mt-5">
                <button onClick=${() => setOpen(!open)}
                    class="w-full flex items-center justify-between py-3 hover:bg-gray-50 transition px-1">
                    <div class="flex items-center gap-2">
                        <svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                  d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
                        </svg>
                        <span class="text-xs font-medium text-gray-500">Advanced Settings</span>
                    </div>
                    <svg class="w-3.5 h-3.5 text-gray-400 transition ${open ? 'rotate-180' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                    </svg>
                </button>

                ${open && html`
                    <div class="pb-2 space-y-5 pt-2 px-1">

                        <!-- Engine -->
                        <div>
                            <label class="text-xs font-semibold text-gray-500 uppercase mb-2 block">Simulation Engine</label>
                            <div class="flex gap-2">
                                ${[["v2", "v2 Time-Stepped (Recommended)"], ["v1", "v1 Single-Shot"]].map(([val, label]) => html`
                                    <button key=${val}
                                        onClick=${() => update("engine", val)}
                                        class="flex-1 px-3 py-2 rounded-lg border text-xs font-medium transition
                                            ${settings.engine === val
                                                ? 'border-brand-500 bg-brand-50 text-brand-700'
                                                : 'border-gray-200 text-gray-600 hover:border-gray-300'}">
                                        ${label}
                                    </button>
                                `)}
                            </div>
                        </div>

                        <!-- J-Curve -->
                        <div>
                            <label class="text-xs font-semibold text-gray-500 uppercase mb-2 block">J-Curve Productivity Dip</label>
                            <div class="flex items-center gap-3 mb-2">
                                <label class="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox"
                                        checked=${settings.j_curve_enabled}
                                        onChange=${e => update("j_curve_enabled", e.target.checked)}
                                        class="rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
                                    <span class="text-xs text-gray-600">Enable J-Curve</span>
                                </label>
                            </div>
                            ${settings.j_curve_enabled && html`
                                <div class="grid grid-cols-2 gap-3">
                                    <div>
                                        <span class="text-xs text-gray-500">Dip: ${Math.round(settings.j_curve_dip_pct)}%</span>
                                        <input type="range" min="5" max="30" step="1"
                                            value=${settings.j_curve_dip_pct}
                                            onChange=${e => update("j_curve_dip_pct", parseInt(e.target.value))}
                                            class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600" />
                                    </div>
                                    <div>
                                        <span class="text-xs text-gray-500">Duration: ${settings.j_curve_duration_months}mo</span>
                                        <input type="range" min="3" max="12" step="1"
                                            value=${settings.j_curve_duration_months}
                                            onChange=${e => update("j_curve_duration_months", parseInt(e.target.value))}
                                            class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600" />
                                    </div>
                                </div>
                            `}
                        </div>

                        <!-- Organization Profile -->
                        <div>
                            <label class="text-xs font-semibold text-gray-500 uppercase mb-2 block">Organization Profile</label>
                            <div class="space-y-2">
                                ${[
                                    ["initial_resistance", "Initial Resistance", "red"],
                                    ["initial_morale", "Initial Morale", "amber"],
                                    ["initial_ai_proficiency", "AI Proficiency", "green"],
                                    ["initial_culture_readiness", "Culture Readiness", "blue"],
                                ].map(([key, label, color]) => html`
                                    <div key=${key}>
                                        <div class="flex justify-between text-xs mb-0.5">
                                            <span class="text-gray-500">${label}</span>
                                            <span class="font-medium text-${color}-600">${((settings.organization[key] || 0) * 100).toFixed(0)}%</span>
                                        </div>
                                        <input type="range" min="0" max="1" step="0.05"
                                            value=${settings.organization[key] || 0}
                                            onChange=${e => updateOrg(key, parseFloat(e.target.value))}
                                            class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-${color}-600" />
                                    </div>
                                `)}
                            </div>
                        </div>

                        <!-- Redeployability -->
                        <div>
                            <label class="text-xs font-semibold text-gray-500 uppercase mb-1 block">Redeployability</label>
                            <div class="flex justify-between text-xs mb-0.5">
                                <span class="text-gray-500">Redeployable %</span>
                                <span class="font-medium">${settings.redeployability_pct}%</span>
                            </div>
                            <input type="range" min="0" max="100" step="5"
                                value=${settings.redeployability_pct}
                                onChange=${e => update("redeployability_pct", parseInt(e.target.value))}
                                class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600" />
                        </div>
                    </div>
                `}
            </div>
        `;
    }

    // ── Task Distribution Panel ──────────────────────────────────────

    function TaskDistributionPanel({ distribution, onChange }) {
        const levels = [
            { key: "human_only_pct", label: "Human Only", color: "#94a3b8" },
            { key: "human_led_pct", label: "Human Led", color: "#64748b" },
            { key: "shared_pct", label: "Shared", color: CHART_COLORS.warning },
            { key: "ai_led_pct", label: "AI Led", color: CHART_COLORS.ai },
            { key: "ai_only_pct", label: "AI Only", color: CHART_COLORS.positive },
        ];

        const total = levels.reduce((s, l) => s + (distribution[l.key] || 0), 0);
        const valid = Math.abs(total - 100) < 0.5;

        const handleChange = (key, val) => {
            onChange({ ...distribution, [key]: val });
        };

        return html`
            <div class="space-y-3">
                <div class="flex items-center justify-between">
                    <span class="text-sm font-medium text-gray-700">Target Distribution</span>
                    <span class="text-xs font-medium ${valid ? 'text-green-600' : 'text-red-600'}">
                        Total: ${total}% ${valid ? '\u2713' : '(must equal 100%)'}
                    </span>
                </div>

                <!-- Stacked bar preview -->
                <div class="flex h-6 rounded-lg overflow-hidden">
                    ${levels.map(l => {
                        const pct = distribution[l.key] || 0;
                        if (pct <= 0) return null;
                        return html`<div key=${l.key}
                            style=${{ width: pct + '%', backgroundColor: l.color }}
                            class="flex items-center justify-center text-xs text-white font-medium"
                            title="${l.label}: ${pct}%">
                            ${pct >= 8 ? pct + '%' : ''}
                        </div>`;
                    })}
                </div>

                <!-- Sliders -->
                ${levels.map(l => html`
                    <div key=${l.key}>
                        <div class="flex justify-between text-xs mb-0.5">
                            <span class="flex items-center gap-1.5">
                                <span class="w-2.5 h-2.5 rounded-full" style=${{ backgroundColor: l.color }}></span>
                                <span class="text-gray-600">${l.label}</span>
                            </span>
                            <span class="font-medium text-gray-800">${distribution[l.key] || 0}%</span>
                        </div>
                        <input type="range" min="0" max="100" step="5"
                            value=${distribution[l.key] || 0}
                            onChange=${e => handleChange(l.key, parseInt(e.target.value))}
                            class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
                    </div>
                `)}
            </div>
        `;
    }

    // ── Scope Level Definitions ────────────────────────────────────

    const SCOPE_LEVELS = [
        { id: "function",         label: "Function" },
        { id: "sub_function",     label: "Sub-Function" },
        { id: "job_family_group", label: "Job Family Group" },
        { id: "job_family",       label: "Job Family" },
    ];

    // ── Main Simulator ──────────────────────────────────────────────

    function Simulator({ onNavigate, initialParams }) {
        // Config state
        const [simType, setSimType] = useState(initialParams?.type || "role_redesign");
        const [automationFactor, setAutomationFactor] = useState(0.5);
        const [techName, setTechName] = useState("Microsoft Copilot");
        const [selectedTechs, setSelectedTechs] = useState([]);
        const [distribution, setDistribution] = useState({
            human_only_pct: 10, human_led_pct: 15, shared_pct: 25, ai_led_pct: 35, ai_only_pct: 15,
        });
        const [timeline, setTimeline] = useState(36);
        const [scenarioName, setScenarioName] = useState("");

        // Scope state — multi-level
        const [scopeLevel, setScopeLevel] = useState("function");
        const [taxonomy, setTaxonomy] = useState(null);
        const [scopeSelections, setScopeSelections] = useState({
            function: initialParams?.scopeName || "",
            sub_function: "",
            job_family_group: "",
            job_family: "",
        });

        // Advanced settings
        const [advancedSettings, setAdvancedSettings] = useState({
            engine: "v2",
            j_curve_enabled: false,
            j_curve_dip_pct: 15,
            j_curve_duration_months: 6,
            redeployability_pct: 60,
            organization: {
                initial_resistance: 0.6,
                initial_morale: 0.7,
                initial_ai_proficiency: 0.1,
                initial_culture_readiness: 0.3,
            },
        });

        // Data state
        const [technologies, setTechnologies] = useState([]);
        const [running, setRunning] = useState(false);
        const [error, setError] = useState(null);

        // Preview state
        const [scopePreview, setScopePreview] = useState(null);
        const [previewLoading, setPreviewLoading] = useState(false);

        // Fetch taxonomy tree + technologies on mount
        useEffect(() => {
            api.get("/taxonomy").then(d => {
                const tree = d.taxonomy;
                setTaxonomy(tree);
                // Auto-select first function if no initial
                if (tree?.children?.length > 0 && !scopeSelections.function) {
                    setScopeSelections(prev => ({ ...prev, function: tree.children[0].name }));
                }
            }).catch(() => {});
            api.get("/technologies").then(d => setTechnologies(d.technologies || [])).catch(() => {});
        }, []);

        // Derive options at each level from taxonomy tree
        const scopeOptions = useMemo(() => {
            if (!taxonomy) return { function: [], sub_function: [], job_family_group: [], job_family: [] };
            const funcs = taxonomy.children || [];
            const selFunc = funcs.find(f => f.name === scopeSelections.function);
            const sfs = selFunc?.children || [];
            const selSf = sfs.find(sf => sf.name === scopeSelections.sub_function);
            const jfgs = selSf?.children || [];
            const selJfg = jfgs.find(jfg => jfg.name === scopeSelections.job_family_group);
            const jfs = selJfg?.children || [];
            return {
                function: funcs,
                sub_function: sfs,
                job_family_group: jfgs,
                job_family: jfs,
            };
        }, [taxonomy, scopeSelections]);

        // The effective scope name and type for the API
        const scopeName = scopeSelections[scopeLevel] || scopeSelections.function;
        const scopeType = scopeLevel;

        // Headcount from the taxonomy node (reliable, pre-computed)
        const scopeHeadcount = useMemo(() => {
            const opts = scopeOptions[scopeLevel] || [];
            const node = opts.find(o => o.name === scopeName);
            return node?.headcount || 0;
        }, [scopeOptions, scopeLevel, scopeName]);

        // Handle scope level change — clear downstream selections
        const handleScopeLevelChange = (level) => {
            setScopeLevel(level);
            const levels = SCOPE_LEVELS.map(l => l.id);
            const idx = levels.indexOf(level);
            const updated = { ...scopeSelections };
            // Clear selections below the new level
            for (let i = idx + 1; i < levels.length; i++) {
                updated[levels[i]] = "";
            }
            // Auto-select first option at the new level if empty
            const opts = scopeOptions[level] || [];
            if (!updated[level] && opts.length > 0) {
                updated[level] = opts[0].name;
            }
            setScopeSelections(updated);
        };

        // Handle selection change at a specific level — clear downstream
        const handleScopeSelect = (level, value) => {
            const levels = SCOPE_LEVELS.map(l => l.id);
            const idx = levels.indexOf(level);
            const updated = { ...scopeSelections, [level]: value };
            for (let i = idx + 1; i < levels.length; i++) {
                updated[levels[i]] = "";
            }
            setScopeSelections(updated);
        };

        // Fetch scope preview when effective scope changes
        useEffect(() => {
            if (!scopeName) return;
            setPreviewLoading(true);
            api.get(`/scope/${encodeURIComponent(scopeType)}/${encodeURIComponent(scopeName)}`)
                .then(d => { setScopePreview(d.scope); setPreviewLoading(false); })
                .catch(() => { setScopePreview(null); setPreviewLoading(false); });
        }, [scopeName, scopeType]);

        const applyPreset = (preset) => {
            setSimType(preset.type);
            if (preset.factor) setAutomationFactor(preset.factor);
            if (preset.tech) setTechName(preset.tech);
            if (preset.techs) setSelectedTechs(preset.techs);
            if (preset.dist) setDistribution(preset.dist);
            setTimeline(preset.timeline);
        };

        const toggleTech = (name) => {
            setSelectedTechs(prev =>
                prev.includes(name) ? prev.filter(t => t !== name) : [...prev, name]
            );
        };

        const handleRun = async () => {
            setRunning(true);
            setError(null);
            try {
                let params = {};
                if (simType === "role_redesign") {
                    params = { automation_factor: automationFactor };
                } else if (simType === "tech_adoption") {
                    params = { technology_name: techName, adoption_months: 12 };
                } else if (simType === "multi_tech_adoption") {
                    params = { technology_names: selectedTechs, adoption_months: 12 };
                } else if (simType === "task_distribution") {
                    params = { distribution_target: distribution };
                }

                const config = {};
                if (advancedSettings.j_curve_enabled) {
                    config.j_curve_enabled = true;
                    config.j_curve_dip_pct = advancedSettings.j_curve_dip_pct;
                    config.j_curve_duration_months = advancedSettings.j_curve_duration_months;
                }
                if (advancedSettings.redeployability_pct !== 60) {
                    config.redeployability_pct = advancedSettings.redeployability_pct;
                }
                const org = advancedSettings.organization;
                if (org.initial_resistance !== 0.6 || org.initial_morale !== 0.7 ||
                    org.initial_ai_proficiency !== 0.1 || org.initial_culture_readiness !== 0.3) {
                    config.organization = org;
                }

                const body = {
                    type: simType,
                    scope_name: scopeName,
                    scope_type: scopeType,
                    name: scenarioName || undefined,
                    parameters: params,
                    timeline_months: timeline,
                    engine: advancedSettings.engine,
                };
                if (Object.keys(config).length > 0) body.config = config;

                const result = await api.post("/simulate", body);

                setRunning(false);
                onNavigate("results", {
                    scenarioId: result.scenario_id,
                    result: result.result,
                    config: result.config,
                });
            } catch (e) {
                setError(e.message);
                setRunning(false);
            }
        };

        const selectedTech = technologies.find(t => t.name === techName);
        const currentType = SIM_TYPES.find(s => s.id === simType);
        const canRun = !(running || (simType === "multi_tech_adoption" && selectedTechs.length === 0));

        // Summary line for the sticky bar
        const scopeLevelLabel = SCOPE_LEVELS.find(l => l.id === scopeLevel)?.label || "Function";
        const summaryParts = [currentType?.label, `${scopeLevelLabel}: ${scopeName}`];
        if (simType === "role_redesign") summaryParts.push(`Factor ${automationFactor.toFixed(2)}`);
        if (simType === "tech_adoption") summaryParts.push(techName);
        if (simType === "multi_tech_adoption" && selectedTechs.length > 0) summaryParts.push(`${selectedTechs.length} techs`);
        summaryParts.push(`${timeline}mo`);

        return html`
            <div class="fade-in space-y-4 pb-20">

                <!-- ── Header row: title + preset chips ── -->
                <div class="flex items-start justify-between gap-4">
                    <div>
                        <h1 class="text-2xl font-bold text-gray-900">Run Simulation</h1>
                        <p class="text-sm text-gray-500">Configure and run a cascade simulation</p>
                    </div>
                    <div class="flex items-center gap-1.5 flex-wrap justify-end">
                        <span class="text-xs text-gray-400 mr-1">Quick start:</span>
                        ${PRESETS.map(p => html`
                            <button key=${p.label} onClick=${() => applyPreset(p)}
                                class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-gray-200
                                       hover:border-brand-300 hover:bg-brand-50 transition text-xs font-medium text-gray-700"
                                title=${p.label}>
                                <span class="text-sm">${p.icon}</span>
                                ${p.label}
                            </button>
                        `)}
                    </div>
                </div>

                ${error && html`<${ErrorBox} message=${error} />`}

                <!-- ── Type tabs ── -->
                <div class="bg-white rounded-xl border border-gray-200 p-4">
                    <div class="flex bg-gray-100 rounded-lg p-0.5 gap-0.5">
                        ${SIM_TYPES.map(st => html`
                            <button key=${st.id}
                                onClick=${() => setSimType(st.id)}
                                class="px-3 py-1.5 rounded-md text-sm font-medium transition flex items-center gap-1.5
                                    ${simType === st.id
                                        ? 'bg-white text-brand-700 shadow-sm'
                                        : 'text-gray-600 hover:text-gray-900'}">
                                <span class="text-base">${st.icon}</span>
                                ${st.label}
                            </button>
                        `)}
                    </div>
                </div>

                <!-- ── Scope selector (multi-level) ── -->
                <div class="bg-white rounded-xl border border-gray-200 p-4">
                    <div class="flex items-center gap-3 flex-wrap">
                        <span class="text-xs text-gray-500 font-medium">Scope level:</span>
                        <div class="flex bg-gray-100 rounded-md p-0.5 gap-0.5">
                            ${SCOPE_LEVELS.map(lvl => html`
                                <button key=${lvl.id}
                                    onClick=${() => handleScopeLevelChange(lvl.id)}
                                    class="px-2.5 py-1 rounded text-xs font-medium transition
                                        ${scopeLevel === lvl.id
                                            ? 'bg-white text-brand-700 shadow-sm'
                                            : 'text-gray-500 hover:text-gray-700'}">
                                    ${lvl.label}
                                </button>
                            `)}
                        </div>

                        <div class="flex items-center gap-2 ml-auto flex-wrap">
                            <!-- Cascading dropdowns: show from function down to the selected level -->
                            ${SCOPE_LEVELS.filter((_, i) => i <= SCOPE_LEVELS.findIndex(l => l.id === scopeLevel)).map(lvl => {
                                const opts = scopeOptions[lvl.id] || [];
                                if (opts.length === 0) return null;
                                return html`
                                    <select key=${lvl.id}
                                        value=${scopeSelections[lvl.id] || ""}
                                        onChange=${e => handleScopeSelect(lvl.id, e.target.value)}
                                        class="border border-gray-300 rounded-lg px-2.5 py-1.5 text-xs focus:ring-brand-500 focus:border-brand-500 max-w-[200px]">
                                        ${!scopeSelections[lvl.id] && html`
                                            <option value="" disabled>Select ${lvl.label}...</option>
                                        `}
                                        ${opts.map(o => html`
                                            <option key=${o.id || o.name} value=${o.name}>
                                                ${o.name}${o.headcount ? ` (${fmt.number(o.headcount)} HC)` : ''}
                                            </option>
                                        `)}
                                    </select>
                                    ${lvl.id !== scopeLevel ? html`
                                        <svg class="w-3 h-3 text-gray-300 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                                        </svg>
                                    ` : ''}
                                `;
                            })}
                        </div>
                    </div>
                </div>

                <!-- ── Main content: config card + sidebar ── -->
                <div class="flex gap-5">

                    <!-- Left: unified config card -->
                    <div class="flex-1 min-w-0">
                        <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-5">

                            <!-- Scope metrics bar -->
                            ${scopePreview && !previewLoading && html`
                                <div class="flex gap-3">
                                    ${[
                                        { val: scopePreview.summary?.role_count || 0, label: "Roles", color: "blue" },
                                        { val: fmt.number(scopeHeadcount || scopePreview.summary?.total_headcount || 0), label: "Headcount", color: "green" },
                                        { val: scopePreview.summary?.task_count || 0, label: "Tasks", color: "blue" },
                                        { val: scopePreview.summary?.skill_count || 0, label: "Skills", color: "blue" },
                                    ].map(m => html`
                                        <div key=${m.label} class="flex-1 text-center py-2 bg-${m.color}-50 rounded-lg">
                                            <div class="text-base font-bold text-${m.color}-700">${m.val}</div>
                                            <div class="text-[10px] text-${m.color}-600">${m.label}</div>
                                        </div>
                                    `)}
                                </div>
                            `}
                            ${previewLoading && html`
                                <div class="flex gap-3">
                                    ${[1,2,3,4].map(i => html`
                                        <div key=${i} class="flex-1 h-14 shimmer rounded-lg"></div>
                                    `)}
                                </div>
                            `}

                            <!-- Type-specific parameters -->
                            ${simType === "role_redesign" && html`
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">
                                        Automation Factor: <span class="text-brand-600">${automationFactor.toFixed(2)}</span>
                                    </label>
                                    <input type="range" min="0.1" max="1.0" step="0.05"
                                        value=${automationFactor}
                                        onChange=${e => setAutomationFactor(parseFloat(e.target.value))}
                                        class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600" />
                                    <div class="flex justify-between text-xs text-gray-400 mt-1">
                                        <span>Conservative (0.1)</span>
                                        <span>Moderate (0.5)</span>
                                        <span>Aggressive (1.0)</span>
                                    </div>
                                </div>
                            `}

                            ${simType === "tech_adoption" && html`
                                <div class="space-y-3">
                                    <label class="block text-sm font-medium text-gray-700">Select Technology</label>
                                    <div class="grid grid-cols-2 gap-2">
                                        ${technologies.map(t => html`
                                            <button key=${t.name}
                                                onClick=${() => setTechName(t.name)}
                                                class="p-3 rounded-lg border-2 text-left text-sm transition
                                                    ${techName === t.name
                                                        ? 'border-brand-500 bg-brand-50'
                                                        : 'border-gray-200 hover:border-gray-300'}">
                                                <div class="font-medium">${t.name}</div>
                                                <div class="text-xs text-gray-500">${t.vendor}</div>
                                                <div class="flex gap-1 mt-1">
                                                    <${Badge} text=${t.license_tier} color="blue" />
                                                    <${Badge} text=${t.adoption_speed} color="blue" />
                                                </div>
                                            </button>
                                        `)}
                                    </div>
                                    ${selectedTech && html`
                                        <div class="bg-gray-50 rounded-lg p-3 text-sm">
                                            <div class="font-medium text-gray-700 mb-1">Capabilities:</div>
                                            <div class="flex flex-wrap gap-1">
                                                ${selectedTech.capabilities.map(c => html`
                                                    <${Badge} key=${c} text=${c} color="blue" />
                                                `)}
                                            </div>
                                        </div>
                                    `}
                                </div>
                            `}

                            ${simType === "multi_tech_adoption" && html`
                                <div class="space-y-3">
                                    <label class="block text-sm font-medium text-gray-700">Select Technologies (multiple)</label>
                                    ${selectedTechs.length > 0 && html`
                                        <div class="flex flex-wrap gap-1">
                                            ${selectedTechs.map(name => html`
                                                <span key=${name}
                                                    class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-brand-100 text-brand-700">
                                                    ${name}
                                                    <button onClick=${() => toggleTech(name)}
                                                        class="hover:text-brand-900 ml-0.5">\u00D7</button>
                                                </span>
                                            `)}
                                        </div>
                                    `}
                                    <div class="grid grid-cols-2 gap-2">
                                        ${technologies.map(t => {
                                            const active = selectedTechs.includes(t.name);
                                            return html`
                                                <button key=${t.name}
                                                    onClick=${() => toggleTech(t.name)}
                                                    class="p-3 rounded-lg border-2 text-left text-sm transition
                                                        ${active
                                                            ? 'border-brand-500 bg-brand-50'
                                                            : 'border-gray-200 hover:border-gray-300'}">
                                                    <div class="flex items-center justify-between">
                                                        <div class="font-medium">${t.name}</div>
                                                        ${active && html`
                                                            <svg class="w-4 h-4 text-brand-600" fill="currentColor" viewBox="0 0 20 20">
                                                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                                                            </svg>
                                                        `}
                                                    </div>
                                                    <div class="text-xs text-gray-500">${t.vendor}</div>
                                                    <div class="flex gap-1 mt-1">
                                                        <${Badge} text=${t.license_tier} color="blue" />
                                                        <${Badge} text=${t.adoption_speed} color="blue" />
                                                    </div>
                                                </button>
                                            `;
                                        })}
                                    </div>
                                </div>
                            `}

                            ${simType === "task_distribution" && html`
                                <${TaskDistributionPanel}
                                    distribution=${distribution}
                                    onChange=${setDistribution}
                                />
                            `}

                            <!-- Timeline + Name row -->
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">
                                        Timeline: <span class="text-brand-600">${timeline}mo</span>
                                    </label>
                                    <input type="range" min="12" max="60" step="6"
                                        value=${timeline}
                                        onChange=${e => setTimeline(parseInt(e.target.value))}
                                        class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600" />
                                    <div class="flex justify-between text-xs text-gray-400 mt-1">
                                        <span>1yr</span>
                                        <span>3yr</span>
                                        <span>5yr</span>
                                    </div>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Scenario Name</label>
                                    <input type="text"
                                        value=${scenarioName}
                                        onChange=${e => setScenarioName(e.target.value)}
                                        placeholder=${`${simType.replace(/_/g, ' ')} - ${scopeName}`}
                                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-brand-500 focus:border-brand-500" />
                                </div>
                            </div>

                            <!-- Advanced Settings (inline, collapsible) -->
                            <${AdvancedSettings}
                                settings=${advancedSettings}
                                onChange=${setAdvancedSettings}
                            />
                        </div>
                    </div>

                    <!-- Right: slim sidebar with donut only -->
                    <div class="w-56 flex-shrink-0">
                        <div class="bg-white rounded-xl border border-gray-200 p-4 sticky top-20">
                            <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Current Distribution</div>
                            ${previewLoading ? html`
                                <div class="h-40 shimmer rounded-lg"></div>
                            ` : scopePreview?.tasks?.length > 0 ? html`
                                <${TaskDistributionDonut} tasks=${scopePreview.tasks} height="180px" />
                                <div class="text-center text-[10px] text-gray-400 mt-1">${scopeLevelLabel}: ${scopeName}</div>
                            ` : html`
                                <div class="h-40 flex items-center justify-center">
                                    <p class="text-xs text-gray-400">No task data</p>
                                </div>
                            `}
                        </div>
                    </div>
                </div>

                <!-- ── Sticky bottom run bar ── -->
                <div class="fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur border-t border-gray-200 z-30">
                    <div class="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
                        <div class="text-sm text-gray-500 truncate">
                            ${summaryParts.join('  \u2022  ')}
                        </div>
                        <button
                            onClick=${handleRun}
                            disabled=${!canRun}
                            class="px-6 py-2.5 rounded-lg font-medium text-white transition flex items-center gap-2 shadow-sm flex-shrink-0
                                ${!canRun
                                    ? 'bg-gray-300 cursor-not-allowed'
                                    : 'bg-brand-600 hover:bg-brand-700'}">
                            ${running
                                ? html`<span class="flex items-center gap-2">
                                    <span class="pulse-dot inline-block w-2 h-2 rounded-full bg-white"></span>
                                    Running Cascade...
                                  </span>`
                                : html`
                                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                                    </svg>
                                    Run Simulation
                                `}
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    window.DT.Simulator = Simulator;
})();
