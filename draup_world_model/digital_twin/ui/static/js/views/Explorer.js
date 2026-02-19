/**
 * Explorer View - Navigate the organizational taxonomy.
 *
 * Features: collapsible tree with headcount bars, breadcrumb trail,
 * tabbed detail panel with overview charts, role/skill/technology/workload/task tables.
 */

(function () {
    const { html, useState, useEffect, useCallback, useMemo, useRef, api, fmt,
            MetricCard, Badge, Spinner, ErrorBox, SectionHeader, DataTable,
            LoadingState, ChartCanvas, TaskDistributionDonut,
            CHART_COLORS } = window.DT;

    // ── TreeNode ────────────────────────────────────────────────────

    function TreeNode({ node, depth = 0, onSelect, selectedId, maxHeadcount }) {
        const [expanded, setExpanded] = useState(depth < 1);
        const hasChildren = node.children && node.children.length > 0;
        const isSelected = node.id === selectedId;
        const indent = depth * 16;

        const typeIcons = {
            organization: "\u{1F3E2}",
            function: "\u{1F4C1}",
            sub_function: "\u{1F4C2}",
            job_family_group: "\u{1F465}",
            job_family: "\u{1F464}",
        };

        const hcPct = (node.headcount && maxHeadcount > 0) ? Math.round((node.headcount / maxHeadcount) * 100) : 0;

        return html`
            <div>
                <div
                    class="flex items-center py-2 px-2 rounded-lg text-sm cursor-pointer transition-all
                        ${isSelected ? 'bg-brand-100 text-brand-800 shadow-sm' : 'hover:bg-gray-100 text-gray-700'}"
                    style=${{paddingLeft: `${indent + 8}px`}}
                    onClick=${() => {
                        if (hasChildren) setExpanded(!expanded);
                        onSelect(node);
                    }}>
                    ${hasChildren ? html`
                        <span class="mr-1.5 text-gray-400 text-xs select-none w-4 text-center transition-transform ${expanded ? 'rotate-90' : ''}" style=${{display:'inline-block',transition:'transform 0.15s ease'}}>
                            \u25B6
                        </span>
                    ` : html`<span class="mr-1.5 w-4"></span>`}
                    <span class="mr-1.5">${typeIcons[node.type] || "\u{1F4CB}"}</span>
                    <span class="truncate flex-1 font-medium">${node.name}</span>
                    ${node.headcount > 0 && html`
                        <div class="flex items-center gap-2 ml-2 flex-shrink-0">
                            <div class="w-20 bg-gray-200 rounded-full h-2">
                                <div class="bg-brand-500 h-2 rounded-full transition-all" style=${{width: `${Math.max(hcPct, 3)}%`}}></div>
                            </div>
                            <span class="text-xs font-medium text-gray-500 min-w-[40px] text-right">${fmt.number(node.headcount)}</span>
                        </div>
                    `}
                    ${(!node.headcount || node.headcount === 0) && depth > 0 && html`
                        <span class="text-xs text-gray-300 ml-2 flex-shrink-0">N/A</span>
                    `}
                </div>
                ${expanded && hasChildren && html`
                    <div class="tree-children">
                        ${node.children.map(child => html`
                            <${TreeNode}
                                key=${child.id}
                                node=${child}
                                depth=${depth + 1}
                                onSelect=${onSelect}
                                selectedId=${selectedId}
                                maxHeadcount=${maxHeadcount}
                            />
                        `)}
                    </div>
                `}
            </div>
        `;
    }

    // ── Breadcrumbs ─────────────────────────────────────────────────

    function Breadcrumbs({ path, onSelect }) {
        if (!path || path.length === 0) return null;
        return html`
            <nav class="flex items-center gap-1 text-sm mb-3 flex-wrap bg-gray-50 rounded-lg px-3 py-2">
                <svg class="w-3.5 h-3.5 text-gray-400 mr-1 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
                </svg>
                ${path.map((node, i) => html`
                    <span key=${node.id} class="flex items-center gap-1">
                        ${i > 0 && html`
                            <svg class="w-3 h-3 text-gray-300 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                            </svg>
                        `}
                        <button onClick=${() => onSelect(node)}
                            class="hover:text-brand-600 transition px-1 py-0.5 rounded
                                ${i === path.length - 1 ? 'text-gray-900 font-semibold bg-white shadow-sm' : 'text-gray-500'}">
                            ${node.name}
                        </button>
                    </span>
                `)}
            </nav>
        `;
    }

    // ── Helpers ──────────────────────────────────────────────────────

    function roleAutomationValue(r) {
        return r.computed_automation_score || r.automation_score || r.automation_potential || 0;
    }

    const LIFECYCLE_COLORS = { emerging: "blue", growing: "green", stable: "gray", declining: "red" };
    const DEMAND_ICONS = { rising: "\u2191", steady: "\u2192", declining: "\u2193" };
    const DEMAND_COLORS = { rising: "green", steady: "gray", declining: "red" };
    const ADOPTION_COLORS = { emerging: "blue", early_adopter: "blue", mainstream: "green", mature: "gray", legacy: "red" };
    const LICENSE_COLORS = { low: "green", medium: "amber", high: "red", enterprise: "blue" };
    const AUTO_LEVEL_COLORS = {
        ai_only: "green", ai_led: "green", shared: "amber", human_led: "gray", human_only: "gray"
    };

    function SearchInput({ value, onChange, placeholder }) {
        return html`
            <input type="text"
                value=${value}
                onInput=${e => onChange(e.target.value)}
                placeholder=${placeholder}
                class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                       focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none" />
        `;
    }

    // ── Tab Bar ──────────────────────────────────────────────────────

    function TabBar({ tabs, active, onChange }) {
        return html`
            <div class="flex gap-1 border-b border-gray-200 mb-4 overflow-x-auto">
                ${tabs.map(t => html`
                    <button key=${t.id}
                        onClick=${() => onChange(t.id)}
                        class="px-3 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors
                            ${active === t.id
                                ? 'border-brand-600 text-brand-700'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}">
                        ${t.label}
                        ${t.count != null ? html`
                            <span class="ml-1.5 text-xs px-1.5 py-0.5 rounded-full
                                ${active === t.id ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-500'}">
                                ${t.count}
                            </span>
                        ` : null}
                    </button>
                `)}
            </div>
        `;
    }

    // ── Charts ───────────────────────────────────────────────────────

    function RoleAutomationChart({ roles }) {
        if (!roles || roles.length === 0) return null;

        const sorted = [...roles].sort((a, b) =>
            roleAutomationValue(b) - roleAutomationValue(a)
        ).slice(0, 15);

        const maxLabelLen = 22;
        const data = {
            labels: sorted.map(r => {
                const n = r.name || 'Unknown';
                return n.length > maxLabelLen ? n.substring(0, maxLabelLen - 1) + '...' : n;
            }),
            datasets: [{
                label: 'Automation Potential %',
                data: sorted.map(r => Math.round(roleAutomationValue(r))),
                backgroundColor: sorted.map(r => {
                    const p = roleAutomationValue(r);
                    return p > 60 ? CHART_COLORS.positive : p > 30 ? CHART_COLORS.warning : CHART_COLORS.info;
                }),
                borderRadius: 4,
            }],
        };

        const fullNames = sorted.map(r => r.name || 'Unknown');
        const options = {
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: ctx => fullNames[ctx[0].dataIndex],
                        label: ctx => `Automation: ${ctx.raw}%`,
                        afterLabel: (ctx) => {
                            const role = sorted[ctx.dataIndex];
                            return `Headcount: ${fmt.number(role.computed_headcount || 0)}`;
                        }
                    }
                },
            },
            scales: {
                x: { beginAtZero: true, max: 100, grid: { color: '#f3f4f6' },
                     ticks: { callback: v => v + '%' } },
                y: { grid: { display: false },
                     afterFit: axis => { axis.width = Math.max(axis.width, 140); } },
            },
        };

        const h = Math.max(180, sorted.length * 28);
        return html`<${ChartCanvas} type="bar" data=${data} options=${options} height="${h}px" />`;
    }

    function SkillCategoryChart({ skills }) {
        if (!skills || skills.length === 0) return null;

        const byCat = {};
        skills.forEach(s => {
            const cat = (s.category || 'other').replace(/_/g, ' ');
            byCat[cat] = (byCat[cat] || 0) + 1;
        });
        const sorted = Object.entries(byCat).sort((a, b) => b[1] - a[1]);
        const catColors = ['#3b82f6', '#8b5cf6', '#22c55e', '#f97316', '#06b6d4', '#ec4899', '#eab308'];

        return html`<${ChartCanvas} type="bar" height="200px"
            data=${{
                labels: sorted.map(([c]) => c),
                datasets: [{
                    data: sorted.map(([, v]) => v),
                    backgroundColor: sorted.map((_, i) => catColors[i % catColors.length]),
                    borderRadius: 4,
                }],
            }}
            options=${{
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: '#f3f4f6' } },
                    y: { grid: { display: false } },
                },
            }} />`;
    }

    function TechCategoryChart({ technologies }) {
        if (!technologies || technologies.length === 0) return null;

        const byCat = {};
        technologies.forEach(t => {
            const cat = (t.category || 'other').replace(/_/g, ' ');
            byCat[cat] = (byCat[cat] || 0) + 1;
        });
        const sorted = Object.entries(byCat).sort((a, b) => b[1] - a[1]);
        const catColors = ['#06b6d4', '#8b5cf6', '#f97316', '#22c55e', '#ec4899', '#3b82f6', '#eab308'];

        return html`<${ChartCanvas} type="doughnut" height="200px"
            data=${{
                labels: sorted.map(([c]) => c),
                datasets: [{
                    data: sorted.map(([, v]) => v),
                    backgroundColor: catColors.slice(0, sorted.length),
                    borderWidth: 0,
                }],
            }}
            options=${{
                plugins: {
                    legend: { position: 'right', labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
                },
                cutout: '55%',
            }} />`;
    }

    function WorkloadEffortChart({ workloads }) {
        if (!workloads || workloads.length === 0) return null;

        const sorted = [...workloads]
            .sort((a, b) => (b.effort_allocation_pct || 0) - (a.effort_allocation_pct || 0))
            .slice(0, 12);

        const maxLabelLen = 22;
        const fullNames = sorted.map(w => w.name || 'Unknown');
        const truncLabels = fullNames.map(n => n.length > maxLabelLen ? n.substring(0, maxLabelLen - 1) + '...' : n);

        return html`<${ChartCanvas} type="bar" height="${Math.max(160, sorted.length * 26)}px"
            data=${{
                labels: truncLabels,
                datasets: [{
                    data: sorted.map(w => w.effort_allocation_pct || 0),
                    backgroundColor: sorted.map(w => {
                        const lev = w.automation_level || '';
                        return lev.includes('ai') ? '#22c55e' : lev === 'shared' ? '#f59e0b' : '#94a3b8';
                    }),
                    borderRadius: 4,
                }],
            }}
            options=${{
                indexAxis: 'y',
                plugins: { legend: { display: false },
                    tooltip: { callbacks: {
                        title: ctx => fullNames[ctx[0].dataIndex],
                        label: ctx => 'Effort: ' + ctx.raw + '%',
                    } } },
                scales: {
                    x: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' }, grid: { color: '#f3f4f6' } },
                    y: { grid: { display: false },
                         afterFit: axis => { axis.width = Math.max(axis.width, 140); } },
                },
            }} />`;
    }

    function CareerBandChart({ jobTitles }) {
        if (!jobTitles || jobTitles.length === 0) return null;

        const byBand = {};
        jobTitles.forEach(jt => {
            const band = (jt.career_band || 'Other').replace(/_/g, ' ');
            byBand[band] = (byBand[band] || 0) + (jt.headcount || 1);
        });
        const sorted = Object.entries(byBand).sort((a, b) => b[1] - a[1]);
        const bandColors = ['#3b82f6', '#8b5cf6', '#22c55e', '#f97316', '#ec4899', '#06b6d4'];

        return html`<${ChartCanvas} type="doughnut" height="200px"
            data=${{
                labels: sorted.map(([b]) => b),
                datasets: [{
                    data: sorted.map(([, v]) => v),
                    backgroundColor: bandColors.slice(0, sorted.length),
                    borderWidth: 0,
                }],
            }}
            options=${{
                plugins: {
                    legend: { position: 'right', labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
                    tooltip: { callbacks: { label: ctx => `${ctx.label}: ${fmt.number(ctx.raw)} headcount` } },
                },
                cutout: '55%',
            }} />`;
    }

    // ── Tab: Overview ────────────────────────────────────────────────

    function OverviewTab({ roles, tasks, skills, technologies, workloads, jobTitles }) {
        return html`
            <div class="space-y-4">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    ${roles.length > 0 && html`
                        <div class="bg-gray-50 rounded-xl p-4">
                            <div class="text-sm font-medium text-gray-700 mb-2">Role Automation Potential</div>
                            <${RoleAutomationChart} roles=${roles} />
                        </div>
                    `}
                    ${tasks.length > 0 && html`
                        <div class="bg-gray-50 rounded-xl p-4">
                            <div class="text-sm font-medium text-gray-700 mb-2">Task Automation Distribution</div>
                            <${TaskDistributionDonut} tasks=${tasks} height="220px" />
                        </div>
                    `}
                </div>
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    ${skills.length > 0 && html`
                        <div class="bg-gray-50 rounded-xl p-4">
                            <div class="text-sm font-medium text-gray-700 mb-2">Skills by Category</div>
                            <${SkillCategoryChart} skills=${skills} />
                        </div>
                    `}
                    ${technologies.length > 0 && html`
                        <div class="bg-gray-50 rounded-xl p-4">
                            <div class="text-sm font-medium text-gray-700 mb-2">Technology Stack</div>
                            <${TechCategoryChart} technologies=${technologies} />
                        </div>
                    `}
                </div>
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    ${workloads.length > 0 && html`
                        <div class="bg-gray-50 rounded-xl p-4">
                            <div class="text-sm font-medium text-gray-700 mb-2">Workload Effort Allocation</div>
                            <${WorkloadEffortChart} workloads=${workloads} />
                        </div>
                    `}
                    ${jobTitles.length > 0 && html`
                        <div class="bg-gray-50 rounded-xl p-4">
                            <div class="text-sm font-medium text-gray-700 mb-2">Workforce by Career Band</div>
                            <${CareerBandChart} jobTitles=${jobTitles} />
                        </div>
                    `}
                </div>
            </div>
        `;
    }

    // ── Tab: Roles ───────────────────────────────────────────────────

    function RolesTab({ roles, workloads }) {
        const [search, setSearch] = useState("");

        // Pre-compute workload count per role
        const wlCountByRole = useMemo(() => {
            const m = {};
            (workloads || []).forEach(wl => {
                const rid = wl.role_id;
                if (rid) m[rid] = (m[rid] || 0) + 1;
            });
            return m;
        }, [workloads]);

        const filtered = useMemo(() => {
            if (!search) return roles;
            const q = search.toLowerCase();
            return roles.filter(r => (r.name || '').toLowerCase().includes(q));
        }, [roles, search]);

        return html`
            <div class="space-y-3">
                <${SearchInput} value=${search} onChange=${setSearch} placeholder="Search roles..." />
                <${DataTable}
                    columns=${[
                        { key: "name", label: "Role Name" },
                        { key: "computed_headcount", label: "Headcount",
                          render: r => fmt.number(r.computed_headcount || 0) },
                        { key: "avg_salary", label: "Avg Salary",
                          render: r => r.avg_salary ? fmt.currency(r.avg_salary) : html`<span class="text-gray-300">-</span>` },
                        { key: "automation_score", label: "Automation",
                          render: r => html`
                            <div class="flex items-center gap-2">
                                <div class="w-16 bg-gray-200 rounded-full h-1.5">
                                    <div class="h-1.5 rounded-full ${roleAutomationValue(r) > 50
                                        ? 'bg-green-500' : roleAutomationValue(r) > 30
                                        ? 'bg-amber-500' : 'bg-blue-500'}"
                                        style=${{width: `${Math.round(roleAutomationValue(r))}%`}}></div>
                                </div>
                                <span class="text-xs text-gray-500">${Math.round(roleAutomationValue(r))}%</span>
                            </div>` },
                        { key: "workloads", label: "Workloads",
                          render: r => html`<span class="text-xs text-gray-600">${wlCountByRole[r.id] || 0}</span>` },
                    ]}
                    rows=${filtered}
                />
                ${filtered.length === 0 && html`
                    <div class="text-center py-6 text-gray-400 text-sm">No roles match your search</div>
                `}
            </div>
        `;
    }

    // ── Tab: Skills ──────────────────────────────────────────────────

    function SkillsTab({ skills }) {
        const [search, setSearch] = useState("");

        const filtered = useMemo(() => {
            if (!search) return skills;
            const q = search.toLowerCase();
            return skills.filter(s =>
                (s.name || '').toLowerCase().includes(q) ||
                (s.category || '').toLowerCase().includes(q) ||
                (s.skill_type || '').toLowerCase().includes(q)
            );
        }, [skills, search]);

        return html`
            <div class="space-y-3">
                <${SearchInput} value=${search} onChange=${setSearch} placeholder="Search skills by name, category, or type..." />
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-2">
                    <div class="lg:col-span-2">
                        <${DataTable}
                            columns=${[
                                { key: "name", label: "Skill" },
                                { key: "category", label: "Category",
                                  render: s => html`<${Badge} text=${(s.category || 'other').replace(/_/g, ' ')} color="blue" />` },
                                { key: "skill_type", label: "Type",
                                  render: s => html`<span class="text-xs text-gray-600">${(s.skill_type || '').replace(/_/g, ' ')}</span>` },
                                { key: "lifecycle_status", label: "Lifecycle",
                                  render: s => s.lifecycle_status
                                      ? html`<${Badge} text=${s.lifecycle_status} color=${LIFECYCLE_COLORS[s.lifecycle_status] || 'gray'} />`
                                      : html`<span class="text-gray-300">-</span>` },
                                { key: "market_demand_trend", label: "Demand",
                                  render: s => {
                                      const t = s.market_demand_trend;
                                      if (!t) return html`<span class="text-gray-300">-</span>`;
                                      const icon = DEMAND_ICONS[t] || '';
                                      const clr = DEMAND_COLORS[t] || 'gray';
                                      return html`<span class="text-xs font-medium text-${clr}-600">${icon} ${t}</span>`;
                                  } },
                            ]}
                            rows=${filtered}
                        />
                    </div>
                    <div class="bg-gray-50 rounded-xl p-4">
                        <div class="text-sm font-medium text-gray-700 mb-2">By Category</div>
                        <${SkillCategoryChart} skills=${skills} />
                    </div>
                </div>
                ${filtered.length === 0 && html`
                    <div class="text-center py-6 text-gray-400 text-sm">No skills match your search</div>
                `}
            </div>
        `;
    }

    // ── Tab: Technology ──────────────────────────────────────────────

    function TechTab({ technologies }) {
        const [search, setSearch] = useState("");

        const filtered = useMemo(() => {
            if (!search) return technologies;
            const q = search.toLowerCase();
            return technologies.filter(t =>
                (t.name || '').toLowerCase().includes(q) ||
                (t.category || '').toLowerCase().includes(q) ||
                (t.vendor || '').toLowerCase().includes(q)
            );
        }, [technologies, search]);

        return html`
            <div class="space-y-3">
                <${SearchInput} value=${search} onChange=${setSearch} placeholder="Search technologies by name, category, or vendor..." />
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-2">
                    <div class="lg:col-span-2">
                        <${DataTable}
                            columns=${[
                                { key: "name", label: "Technology" },
                                { key: "category", label: "Category",
                                  render: t => html`<${Badge} text=${(t.category || 'other').replace(/_/g, ' ')} color="blue" />` },
                                { key: "vendor", label: "Vendor",
                                  render: t => html`<span class="text-xs text-gray-700">${t.vendor || '-'}</span>` },
                                { key: "adoption_stage", label: "Adoption",
                                  render: t => t.adoption_stage
                                      ? html`<${Badge} text=${(t.adoption_stage || '').replace(/_/g, ' ')} color=${ADOPTION_COLORS[t.adoption_stage] || 'gray'} />`
                                      : html`<span class="text-gray-300">-</span>` },
                                { key: "license_cost_tier", label: "License",
                                  render: t => t.license_cost_tier
                                      ? html`<${Badge} text=${t.license_cost_tier} color=${LICENSE_COLORS[t.license_cost_tier] || 'gray'} />`
                                      : html`<span class="text-gray-300">-</span>` },
                            ]}
                            rows=${filtered}
                        />
                    </div>
                    <div class="bg-gray-50 rounded-xl p-4">
                        <div class="text-sm font-medium text-gray-700 mb-2">By Category</div>
                        <${TechCategoryChart} technologies=${technologies} />
                    </div>
                </div>
                ${filtered.length === 0 && html`
                    <div class="text-center py-6 text-gray-400 text-sm">No technologies match your search</div>
                `}
            </div>
        `;
    }

    // ── Tab: Workloads ───────────────────────────────────────────────

    function WorkloadsTab({ workloads, tasks }) {
        const [search, setSearch] = useState("");

        // Pre-compute task count per workload
        const taskCountByWl = useMemo(() => {
            const m = {};
            (tasks || []).forEach(t => {
                const wid = t.workload_id;
                if (wid) m[wid] = (m[wid] || 0) + 1;
            });
            return m;
        }, [tasks]);

        const filtered = useMemo(() => {
            if (!search) return workloads;
            const q = search.toLowerCase();
            return workloads.filter(w =>
                (w.name || '').toLowerCase().includes(q) ||
                (w.automation_level || '').toLowerCase().includes(q)
            );
        }, [workloads, search]);

        return html`
            <div class="space-y-3">
                <${SearchInput} value=${search} onChange=${setSearch} placeholder="Search workloads..." />
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <div class="lg:col-span-2">
                        <${DataTable}
                            columns=${[
                                { key: "name", label: "Workload" },
                                { key: "effort_allocation_pct", label: "Effort",
                                  render: w => html`
                                    <div class="flex items-center gap-2">
                                        <div class="w-14 bg-gray-200 rounded-full h-1.5">
                                            <div class="h-1.5 bg-brand-500 rounded-full"
                                                style=${{width: `${Math.min(w.effort_allocation_pct || 0, 100)}%`}}></div>
                                        </div>
                                        <span class="text-xs text-gray-500">${w.effort_allocation_pct || 0}%</span>
                                    </div>` },
                                { key: "automation_level", label: "Automation",
                                  render: w => w.automation_level
                                      ? html`<${Badge} text=${(w.automation_level || '').replace(/_/g, ' ')}
                                            color=${AUTO_LEVEL_COLORS[w.automation_level] || 'gray'} />`
                                      : html`<span class="text-gray-300">-</span>` },
                                { key: "tasks", label: "Tasks",
                                  render: w => html`<span class="text-xs text-gray-600">${taskCountByWl[w.id] || 0}</span>` },
                            ]}
                            rows=${filtered}
                        />
                    </div>
                    <div class="bg-gray-50 rounded-xl p-4">
                        <div class="text-sm font-medium text-gray-700 mb-2">Effort Distribution</div>
                        <${WorkloadEffortChart} workloads=${workloads} />
                    </div>
                </div>
                ${filtered.length === 0 && html`
                    <div class="text-center py-6 text-gray-400 text-sm">No workloads match your search</div>
                `}
            </div>
        `;
    }

    // ── Tab: Tasks ───────────────────────────────────────────────────

    function TasksTab({ tasks, workloads }) {
        const [search, setSearch] = useState("");

        // Map workload id → name for the parent column
        const wlNames = useMemo(() => {
            const m = {};
            (workloads || []).forEach(w => { m[w.id] = w.name; });
            return m;
        }, [workloads]);

        const filtered = useMemo(() => {
            const list = search
                ? tasks.filter(t => {
                    const q = search.toLowerCase();
                    return (t.name || '').toLowerCase().includes(q) ||
                           (t.classification || '').toLowerCase().includes(q) ||
                           (t.automation_level || '').toLowerCase().includes(q);
                })
                : tasks;
            return list.slice(0, 50);
        }, [tasks, search]);

        return html`
            <div class="space-y-3">
                <${SearchInput} value=${search} onChange=${setSearch}
                    placeholder="Search tasks by name, classification, or automation level..." />
                <${DataTable}
                    columns=${[
                        { key: "name", label: "Task" },
                        { key: "automation_potential", label: "Potential",
                          render: t => t.automation_potential != null ? html`
                            <div class="flex items-center gap-2">
                                <div class="w-12 bg-gray-200 rounded-full h-1.5">
                                    <div class="h-1.5 rounded-full ${t.automation_potential > 60
                                        ? 'bg-green-500' : t.automation_potential > 30
                                        ? 'bg-amber-500' : 'bg-blue-400'}"
                                        style=${{width: `${Math.round(t.automation_potential)}%`}}></div>
                                </div>
                                <span class="text-xs text-gray-500">${Math.round(t.automation_potential)}%</span>
                            </div>` : html`<span class="text-gray-300">-</span>` },
                        { key: "automation_level", label: "Level",
                          render: t => html`<${Badge}
                            text=${(t.automation_level || '').replace(/_/g, ' ')}
                            color=${AUTO_LEVEL_COLORS[t.automation_level] || 'gray'} />` },
                        { key: "classification", label: "Type",
                          render: t => html`<${Badge} text=${(t.classification || '').replace(/_/g, ' ')} color="blue" />` },
                        { key: "time_allocation_pct", label: "Time %",
                          render: t => t.time_allocation_pct != null
                              ? html`<span class="text-xs text-gray-600">${t.time_allocation_pct}%</span>`
                              : html`<span class="text-gray-300">-</span>` },
                        { key: "workload", label: "Workload",
                          render: t => {
                              const wn = wlNames[t.workload_id];
                              return wn
                                  ? html`<span class="text-xs text-gray-600 truncate max-w-[120px] inline-block">${wn}</span>`
                                  : html`<span class="text-gray-300">-</span>`;
                          } },
                    ]}
                    rows=${filtered}
                />
                ${filtered.length === 0 && html`
                    <div class="text-center py-6 text-gray-400 text-sm">No tasks match your search</div>
                `}
                ${!search && tasks.length > 50 && html`
                    <div class="text-center text-xs text-gray-400">Showing first 50 of ${tasks.length} tasks. Use search to narrow.</div>
                `}
            </div>
        `;
    }

    // ── Node Detail Section (for non-scope nodes) ──────────────────

    function NodeDetailSection({ detail }) {
        if (!detail || !detail.node) return null;
        const { node, relationships } = detail;
        const props = node.properties || {};

        const skipProps = new Set(['id', 'name', 'description']);
        const displayProps = Object.entries(props)
            .filter(([k]) => !skipProps.has(k))
            .filter(([, v]) => v != null && v !== '' && !(Array.isArray(v) && v.length === 0));

        // Group relationships
        const relGroups = {};
        (relationships || []).forEach(r => {
            const key = `${r.direction}:${r.type}`;
            if (!relGroups[key]) relGroups[key] = { direction: r.direction, type: r.type, nodes: [] };
            const related = r.direction === 'outgoing' ? r.target : r.source;
            if (related && related.id) relGroups[key].nodes.push(related);
        });

        return html`
            <div class="space-y-4">
                ${props.description && html`
                    <p class="text-sm text-gray-600 leading-relaxed">${props.description}</p>
                `}

                ${displayProps.length > 0 && html`
                    <div class="bg-gray-50 rounded-xl p-4">
                        <div class="text-sm font-medium text-gray-700 mb-3">Properties</div>
                        <div class="grid grid-cols-2 gap-2">
                            ${displayProps.map(([key, val]) => html`
                                <div key=${key} class="text-xs">
                                    <span class="text-gray-500">${key.replace(/_/g, ' ')}</span>
                                    <div class="font-medium text-gray-800 mt-0.5">
                                        ${Array.isArray(val) ? val.join(', ') : String(val)}
                                    </div>
                                </div>
                            `)}
                        </div>
                    </div>
                `}

                ${Object.keys(relGroups).length > 0 && html`
                    <div>
                        <div class="text-sm font-medium text-gray-700 mb-2">Relationships</div>
                        <div class="space-y-3">
                            ${Object.values(relGroups).map(group => {
                                const relLabel = group.type.replace(/^DT_/, '').replace(/_/g, ' ');
                                const arrow = group.direction === 'outgoing' ? '\u2192' : '\u2190';
                                return html`
                                    <div key="${group.direction}:${group.type}">
                                        <div class="text-xs font-medium text-gray-600 mb-1">${arrow} ${relLabel} (${group.nodes.length})</div>
                                        <div class="flex flex-wrap gap-1">
                                            ${group.nodes.slice(0, 20).map(n => html`
                                                <${Badge} key=${n.id} text=${n.name || n.id} color="blue" />
                                            `)}
                                            ${group.nodes.length > 20 && html`
                                                <span class="text-xs text-gray-400 px-1">+${group.nodes.length - 20} more</span>
                                            `}
                                        </div>
                                    </div>
                                `;
                            })}
                        </div>
                    </div>
                `}
            </div>
        `;
    }

    // ── Detail Panel ────────────────────────────────────────────────

    function DetailPanel({ node, scopeData, breadcrumbPath, onSelectNode }) {
        const [activeTab, setActiveTab] = useState("overview");

        // Reset to overview when node changes
        useEffect(() => { setActiveTab("overview"); }, [node?.id]);

        if (!node) {
            return html`
                <div class="flex flex-col items-center justify-center h-full min-h-[400px] text-center px-8">
                    <div class="w-20 h-20 mb-4 rounded-2xl bg-brand-50 flex items-center justify-center">
                        <svg class="w-10 h-10 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-700 mb-2">Explore Your Organization</h3>
                    <p class="text-sm text-gray-400 max-w-xs mb-4">
                        Select any node in the taxonomy tree to explore roles, skills, tasks, and technologies.
                    </p>
                    <div class="grid grid-cols-1 gap-2 text-left w-full max-w-xs">
                        <div class="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 rounded-lg p-2.5">
                            <span class="text-brand-500">1.</span> Click a \u25B6 arrow to expand branches
                        </div>
                        <div class="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 rounded-lg p-2.5">
                            <span class="text-brand-500">2.</span> Click a node name to view details
                        </div>
                        <div class="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 rounded-lg p-2.5">
                            <span class="text-brand-500">3.</span> Use tabs to explore roles, skills, and more
                        </div>
                    </div>
                </div>
            `;
        }

        const summary = scopeData?.scope?.summary;
        const roles = scopeData?.scope?.roles || [];
        const tasks = scopeData?.scope?.tasks || [];
        const skills = scopeData?.scope?.skills || [];
        const technologies = scopeData?.scope?.technologies || [];
        const workloads = scopeData?.scope?.workloads || [];
        const jobTitles = scopeData?.scope?.job_titles || [];

        // Compute headcount-weighted average automation
        const totalHC = roles.reduce((s, r) => s + (r.computed_headcount || 0), 0);
        const avgAutomation = totalHC > 0
            ? roles.reduce((s, r) => s + roleAutomationValue(r) * (r.computed_headcount || 0), 0) / totalHC
            : (roles.length > 0
                ? roles.reduce((s, r) => s + roleAutomationValue(r), 0) / roles.length
                : 0);

        // Total cost
        const totalCost = roles.reduce((s, r) => s + (r.computed_total_cost || 0), 0);

        // Build tabs
        const tabs = [
            { id: "overview", label: "Overview" },
        ];
        if (roles.length > 0) tabs.push({ id: "roles", label: "Roles", count: roles.length });
        if (skills.length > 0) tabs.push({ id: "skills", label: "Skills", count: skills.length });
        if (technologies.length > 0) tabs.push({ id: "tech", label: "Technology", count: technologies.length });
        if (workloads.length > 0) tabs.push({ id: "workloads", label: "Workloads", count: workloads.length });
        if (tasks.length > 0) tabs.push({ id: "tasks", label: "Tasks", count: tasks.length });

        return html`
            <div class="fade-in space-y-4">
                <${Breadcrumbs} path=${breadcrumbPath} onSelect=${onSelectNode} />

                <!-- Header -->
                <div class="border-b border-gray-200 pb-3">
                    <h3 class="text-lg font-semibold text-gray-900">${node.name}</h3>
                    <div class="flex items-center gap-2 mt-1 flex-wrap">
                        <${Badge} text=${(node.type || "").replace(/_/g, " ")} color="blue" />
                        ${node.headcount > 0 && html`
                            <span class="text-xs text-gray-400">${fmt.number(node.headcount)} headcount</span>
                        `}
                        ${totalCost > 0 && html`
                            <span class="text-xs text-gray-400">${fmt.currency(totalCost)} total cost</span>
                        `}
                    </div>
                </div>

                <!-- KPI Strip -->
                ${summary && html`
                    <div class="grid grid-cols-4 lg:grid-cols-7 gap-2">
                        <${MetricCard} label="Roles" value=${summary.role_count} color="blue" />
                        <${MetricCard} label="Headcount" value=${fmt.number(summary.total_headcount)} color="blue" />
                        <${MetricCard} label="Tasks" value=${summary.task_count} color="blue" />
                        <${MetricCard} label="Skills" value=${summary.skill_count} color="blue" />
                        <${MetricCard} label="Tech" value=${summary.tech_count || 0} color="blue" />
                        <${MetricCard} label="Workloads" value=${summary.workload_count} color="slate" />
                        <${MetricCard} label="Automation"
                            value=${Math.round(avgAutomation) + '%'}
                            color=${avgAutomation > 50 ? "green" : avgAutomation > 30 ? "amber" : "slate"} />
                    </div>
                `}

                <!-- Tabs -->
                ${summary && tabs.length > 1 && html`
                    <${TabBar} tabs=${tabs} active=${activeTab} onChange=${setActiveTab} />
                `}

                <!-- Tab Content -->
                ${summary && activeTab === "overview" && html`
                    <${OverviewTab}
                        roles=${roles} tasks=${tasks} skills=${skills}
                        technologies=${technologies} workloads=${workloads} jobTitles=${jobTitles} />
                `}
                ${summary && activeTab === "roles" && html`
                    <${RolesTab} roles=${roles} workloads=${workloads} />
                `}
                ${summary && activeTab === "skills" && html`
                    <${SkillsTab} skills=${skills} />
                `}
                ${summary && activeTab === "tech" && html`
                    <${TechTab} technologies=${technologies} />
                `}
                ${summary && activeTab === "workloads" && html`
                    <${WorkloadsTab} workloads=${workloads} tasks=${tasks} />
                `}
                ${summary && activeTab === "tasks" && html`
                    <${TasksTab} tasks=${tasks} workloads=${workloads} />
                `}

                <!-- Fallback for non-scope nodes -->
                ${!summary && scopeData?.nodeDetail && html`
                    <${NodeDetailSection} detail=${scopeData.nodeDetail} />
                `}

                ${!summary && !scopeData?.nodeDetail && node.type !== "organization" && html`
                    <div class="text-center py-8 text-gray-400 text-sm">
                        <p>Loading details for <strong>${(node.type || "").replace(/_/g, " ")}</strong>...</p>
                    </div>
                `}
            </div>
        `;
    }

    // ── Explorer (Main) ─────────────────────────────────────────────

    function Explorer({ onNavigate }) {
        const [tree, setTree] = useState(null);
        const [loading, setLoading] = useState(true);
        const [error, setError] = useState(null);
        const [selectedNode, setSelectedNode] = useState(null);
        const [scopeData, setScopeData] = useState(null);
        const [scopeLoading, setScopeLoading] = useState(false);
        const [breadcrumbPath, setBreadcrumbPath] = useState([]);

        useEffect(() => {
            api.get("/taxonomy")
                .then(d => { setTree(d.taxonomy); setLoading(false); })
                .catch(e => { setError(e.message); setLoading(false); });
        }, []);

        // Build breadcrumb path by searching the tree
        const findPath = useCallback((tree, targetId, path = []) => {
            if (!tree) return null;
            const current = [...path, tree];
            if (tree.id === targetId) return current;
            if (tree.children) {
                for (const child of tree.children) {
                    const found = findPath(child, targetId, current);
                    if (found) return found;
                }
            }
            return null;
        }, []);

        const handleSelect = useCallback((node) => {
            setSelectedNode(node);
            if (tree) {
                const path = findPath(tree, node.id) || [node];
                setBreadcrumbPath(path);
            }
            // Load scope data for function, sub_function, job_family, and role nodes
            const scopeTypeMap = {
                function: "function",
                sub_function: "sub_function",
                job_family_group: "job_family_group",
                job_family: "job_family",
                role: "role",
                organization: "organization",
            };
            const apiScopeType = scopeTypeMap[node.type];
            if (apiScopeType) {
                setScopeLoading(true);
                setScopeData(null);
                api.get(`/scope/${apiScopeType}/${encodeURIComponent(node.name)}`)
                    .then(d => { setScopeData(d); setScopeLoading(false); })
                    .catch(() => {
                        // Fallback: try node detail endpoint
                        api.get(`/node/${encodeURIComponent(node.id)}`)
                            .then(d => { setScopeData({ nodeDetail: d }); setScopeLoading(false); })
                            .catch(() => { setScopeLoading(false); });
                    });
            } else if (node.id) {
                // For other types, use node detail endpoint
                setScopeLoading(true);
                setScopeData(null);
                api.get(`/node/${encodeURIComponent(node.id)}`)
                    .then(d => { setScopeData({ nodeDetail: d }); setScopeLoading(false); })
                    .catch(() => { setScopeLoading(false); });
            } else {
                setScopeData(null);
            }
        }, [tree, findPath]);

        // Compute max headcount for tree bar scaling
        const maxHeadcount = useMemo(() => {
            if (!tree || !tree.children) return 0;
            return Math.max(...tree.children.map(c => c.headcount || 0), 1);
        }, [tree]);

        if (loading) return html`<${Spinner} text="Loading taxonomy..." />`;
        if (error) return html`<${ErrorBox} message=${error} />`;

        return html`
            <div class="fade-in flex gap-4 h-[calc(100vh-140px)]">
                <!-- Tree sidebar -->
                <div class="w-80 flex-shrink-0 bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
                    <div class="p-3 border-b border-gray-100">
                        <h2 class="text-sm font-semibold text-gray-700">Organizational Taxonomy</h2>
                        <p class="text-xs text-gray-400 mt-0.5">Click to explore, click \u25B6 to expand</p>
                    </div>
                    <div class="flex-1 overflow-y-auto sidebar-scroll p-2">
                        ${tree && html`
                            <${TreeNode}
                                node=${tree}
                                onSelect=${handleSelect}
                                selectedId=${selectedNode?.id}
                                maxHeadcount=${maxHeadcount}
                            />
                        `}
                    </div>
                </div>

                <!-- Detail panel -->
                <div class="flex-1 bg-white rounded-xl border border-gray-200 overflow-y-auto p-6">
                    ${scopeLoading
                        ? html`<${LoadingState} type="cards" count=${6} />`
                        : html`<${DetailPanel}
                            node=${selectedNode}
                            scopeData=${scopeData}
                            breadcrumbPath=${breadcrumbPath}
                            onSelectNode=${handleSelect}
                        />`
                    }
                </div>
            </div>
        `;
    }

    window.DT.Explorer = Explorer;
})();
