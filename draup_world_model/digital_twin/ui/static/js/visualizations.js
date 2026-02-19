/**
 * Shared visualization components for the Digital Twin interface.
 *
 * D3.js-based: ForceGraph, SankeyDiagram, RiskMatrix, RedeploymentFlow
 * Chart.js-based: ReadinessGauge, WaterfallChart, TimelineChart,
 *                 HeadcountCompareChart, TaskDistributionDonut
 * React-based: CascadeFlow
 */

(function () {
    const { html, useState, useEffect, useRef, useMemo, CHART_COLORS, fmt } = window.DT;

    // ── Graph Schema Edge Mapping ─────────────────────────────────────

    const GRAPH_EDGES = [
        { rel: 'DT_CONTAINS', from: 'DTOrganization', to: 'DTFunction' },
        { rel: 'DT_CONTAINS', from: 'DTFunction', to: 'DTSubFunction' },
        { rel: 'DT_CONTAINS', from: 'DTSubFunction', to: 'DTJobFamilyGroup' },
        { rel: 'DT_CONTAINS', from: 'DTJobFamilyGroup', to: 'DTJobFamily' },
        { rel: 'DT_HAS_ROLE', from: 'DTJobFamily', to: 'DTRole' },
        { rel: 'DT_HAS_TITLE', from: 'DTRole', to: 'DTJobTitle' },
        { rel: 'DT_HAS_WORKLOAD', from: 'DTRole', to: 'DTWorkload' },
        { rel: 'DT_CONTAINS_TASK', from: 'DTWorkload', to: 'DTTask' },
        { rel: 'DT_REQUIRES_SKILL', from: 'DTRole', to: 'DTSkill' },
        { rel: 'DT_USES_TECHNOLOGY', from: 'DTRole', to: 'DTTechnology' },
    ];

    const NODE_CATEGORIES = {
        DTOrganization: 'taxonomy', DTFunction: 'taxonomy',
        DTSubFunction: 'taxonomy', DTJobFamilyGroup: 'taxonomy', DTJobFamily: 'taxonomy',
        DTRole: 'work', DTJobTitle: 'work', DTWorkload: 'work', DTTask: 'work',
        DTSkill: 'capability', DTTechnology: 'capability',
    };

    const CATEGORY_COLORS = {
        taxonomy: CHART_COLORS.info,
        work: CHART_COLORS.ai,
        capability: CHART_COLORS.positive,
    };

    // Per-type distinct colors for graph visualization
    const NODE_TYPE_COLORS = {
        DTOrganization:    '#1e40af',  // dark blue
        DTFunction:        '#3b82f6',  // blue
        DTSubFunction:     '#6366f1',  // indigo
        DTJobFamilyGroup:  '#8b5cf6',  // violet
        DTJobFamily:       '#a855f7',  // purple
        DTRole:            '#ec4899',  // pink
        DTJobTitle:        '#f43f5e',  // rose
        DTWorkload:        '#f97316',  // orange
        DTTask:            '#eab308',  // yellow
        DTSkill:           '#22c55e',  // green
        DTTechnology:      '#06b6d4',  // cyan
        DTWorkflow:        '#14b8a6',  // teal
        DTWorkflowTask:    '#84cc16',  // lime
    };

    // ── ForceGraph ────────────────────────────────────────────────────

    function ForceGraph({ nodeCounts, relCounts, width = 600, height = 350 }) {
        const containerRef = useRef(null);
        const simRef = useRef(null);

        useEffect(() => {
            if (!containerRef.current || !nodeCounts) return;

            // Clear previous
            d3.select(containerRef.current).selectAll("*").remove();

            // Build nodes
            const nodes = Object.entries(nodeCounts)
                .filter(([, count]) => count > 0)
                .map(([label, count]) => ({
                    id: label,
                    label: label.replace(/^DT/, ''),
                    count,
                    r: Math.sqrt(count) * 3 + 8,
                    category: NODE_CATEGORIES[label] || 'taxonomy',
                }));

            const nodeIds = new Set(nodes.map(n => n.id));

            // Build links
            const links = GRAPH_EDGES
                .filter(e => nodeIds.has(e.from) && nodeIds.has(e.to))
                .map(e => ({
                    source: e.from,
                    target: e.to,
                    rel: e.rel.replace(/^DT_/, '').replace(/_/g, ' '),
                    value: (relCounts || {})[e.rel] || 1,
                }));

            const svg = d3.select(containerRef.current)
                .append("svg")
                .attr("viewBox", `0 0 ${width} ${height}`)
                .attr("width", "100%")
                .attr("height", height);

            // Tooltip
            const tooltip = d3.select(containerRef.current)
                .append("div")
                .attr("class", "graph-tooltip")
                .style("opacity", 0);

            // Simulation
            const sim = d3.forceSimulation(nodes)
                .force("link", d3.forceLink(links).id(d => d.id).distance(80))
                .force("charge", d3.forceManyBody().strength(-250))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collide", d3.forceCollide().radius(d => d.r + 5));

            simRef.current = sim;

            // Links
            const link = svg.append("g")
                .selectAll("line")
                .data(links)
                .join("line")
                .attr("stroke", "#d1d5db")
                .attr("stroke-width", d => Math.log(d.value + 1) * 1.2 + 0.5)
                .attr("stroke-opacity", 0.6);

            // Nodes
            const node = svg.append("g")
                .selectAll("g")
                .data(nodes)
                .join("g")
                .call(d3.drag()
                    .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                    .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
                    .on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
                );

            node.append("circle")
                .attr("r", d => d.r)
                .attr("fill", d => CATEGORY_COLORS[d.category])
                .attr("fill-opacity", 0.85)
                .attr("stroke", d => d3.color(CATEGORY_COLORS[d.category]).darker(0.5))
                .attr("stroke-width", 1.5);

            node.append("text")
                .text(d => d.label)
                .attr("text-anchor", "middle")
                .attr("dy", d => d.r + 14)
                .attr("font-size", 10)
                .attr("fill", "#374151")
                .attr("font-weight", 500);

            node.append("text")
                .text(d => d.count)
                .attr("text-anchor", "middle")
                .attr("dy", 4)
                .attr("font-size", d => Math.min(d.r * 0.8, 14))
                .attr("fill", "white")
                .attr("font-weight", 700);

            // Hover
            node.on("mouseover", (e, d) => {
                tooltip.transition().duration(150).style("opacity", 1);
                tooltip.html(`<strong>${d.label}</strong>: ${d.count} nodes`)
                    .style("left", (e.offsetX + 10) + "px")
                    .style("top", (e.offsetY - 10) + "px");
            }).on("mouseout", () => {
                tooltip.transition().duration(200).style("opacity", 0);
            });

            sim.on("tick", () => {
                link
                    .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
                node.attr("transform", d => {
                    d.x = Math.max(d.r, Math.min(width - d.r, d.x));
                    d.y = Math.max(d.r, Math.min(height - d.r, d.y));
                    return `translate(${d.x},${d.y})`;
                });
            });

            return () => { sim.stop(); };
        }, [nodeCounts, relCounts, width, height]);

        return html`<div ref=${containerRef} class="chart-animate" style=${{position:'relative', width:'100%'}}></div>`;
    }

    // ── ReadinessGauge ────────────────────────────────────────────────

    function ReadinessGauge({ score, maxScore, status }) {
        const canvasRef = useRef(null);
        const chartRef = useRef(null);

        useEffect(() => {
            if (!canvasRef.current) return;
            if (chartRef.current) chartRef.current.destroy();

            const color = status === "READY" ? CHART_COLORS.positive
                        : status === "PARTIAL" ? CHART_COLORS.warning : CHART_COLORS.negative;
            const bgColor = status === "READY" ? CHART_COLORS.positiveLight
                          : status === "PARTIAL" ? CHART_COLORS.warningLight : CHART_COLORS.negativeLight;

            chartRef.current = new Chart(canvasRef.current, {
                type: 'doughnut',
                data: {
                    datasets: [{ data: [score, maxScore - score], backgroundColor: [color, bgColor + '40'], borderWidth: 0 }],
                },
                options: {
                    cutout: '75%',
                    rotation: -90,
                    circumference: 180,
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                    animation: { animateRotate: true, duration: 1200 },
                },
                plugins: [{
                    id: 'centerText',
                    afterDraw(chart) {
                        const { ctx, chartArea: { top, bottom, left, right } } = chart;
                        const cx = (left + right) / 2;
                        const cy = bottom - 10;
                        ctx.save();
                        ctx.font = 'bold 28px system-ui';
                        ctx.fillStyle = color;
                        ctx.textAlign = 'center';
                        ctx.fillText(score, cx, cy - 8);
                        ctx.font = '12px system-ui';
                        ctx.fillStyle = '#6b7280';
                        ctx.fillText(`/ ${maxScore}`, cx, cy + 10);
                        ctx.restore();
                    }
                }],
            });

            return () => { if (chartRef.current) { chartRef.current.destroy(); chartRef.current = null; } };
        }, [score, maxScore, status]);

        return html`<div style=${{height:'140px', width:'200px'}}><canvas ref=${canvasRef}></canvas></div>`;
    }

    // ── WaterfallChart ────────────────────────────────────────────────

    function WaterfallChart({ fin, height = "300px" }) {
        const gross = fin.gross_savings || 0;
        const tech = fin.technology_licensing || 0;
        const impl = fin.implementation_cost || 0;
        const resk = fin.reskilling_cost || 0;
        const net = fin.net_impact || 0;

        // Running total for spacers
        const r1 = gross - tech;
        const r2 = r1 - impl;
        const r3 = r2 - resk;

        const data = {
            labels: ['Gross Savings', 'Tech License', 'Implementation', 'Reskilling', 'Net Impact'],
            datasets: [
                {
                    label: 'Spacer',
                    data: [0, r1, r2, r3, 0],
                    backgroundColor: 'transparent',
                    borderWidth: 0,
                    stack: 'stack',
                },
                {
                    label: 'Value',
                    data: [gross, tech, impl, resk, Math.abs(net)],
                    backgroundColor: [
                        CHART_COLORS.positive,
                        CHART_COLORS.negative,
                        CHART_COLORS.warning,
                        CHART_COLORS.ai,
                        net >= 0 ? CHART_COLORS.info : CHART_COLORS.negative,
                    ],
                    borderRadius: 4,
                    stack: 'stack',
                },
            ],
        };

        const options = {
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            if (ctx.datasetIndex === 0) return null;
                            return fmt.currency(ctx.raw);
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true,
                    stacked: true,
                    ticks: { callback: v => fmt.currency(v) },
                },
            },
        };

        return html`<${window.DT.ChartCanvas} type="bar" data=${data} options=${options} height=${height} />`;
    }

    // ── TimelineChart ─────────────────────────────────────────────────

    function TimelineChart({ fin, timelineMonths = 36, adoptionCurve }) {
        const gross = fin.gross_savings || 0;
        const totalCost = fin.total_cost || 0;
        const payback = fin.payback_months || 0;
        const monthlyGross = gross / timelineMonths;

        const months = [];
        const cumSavings = [];
        const cumCost = [];
        for (let m = 0; m <= timelineMonths; m += 3) {
            months.push(`Mo ${m}`);
            cumSavings.push(monthlyGross * m);
            cumCost.push(totalCost);
        }

        const datasets = [
            {
                label: 'Cumulative Savings',
                data: cumSavings,
                borderColor: CHART_COLORS.positive,
                backgroundColor: CHART_COLORS.positive + '20',
                fill: true, tension: 0.3, pointRadius: 2,
            },
            {
                label: 'Total Investment',
                data: cumCost,
                borderColor: CHART_COLORS.negative,
                backgroundColor: CHART_COLORS.negative + '10',
                fill: true, borderDash: [5, 3], pointRadius: 0,
            },
        ];

        const options = {
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
            },
            scales: {
                x: { grid: { display: false } },
                y: { ticks: { callback: v => fmt.currency(v) } },
            },
        };

        return html`<${window.DT.ChartCanvas} type="line" data=${{ labels: months, datasets }} options=${options} height="260px" />`;
    }

    // ── SankeyDiagram ─────────────────────────────────────────────────

    const LEVEL_COLORS = {
        human_only: '#94a3b8', human_led: '#64748b',
        shared: CHART_COLORS.warning, ai_led: CHART_COLORS.ai, ai_only: CHART_COLORS.positive,
    };

    function SankeyDiagram({ taskChanges, width = 600, height = 300 }) {
        const containerRef = useRef(null);

        useEffect(() => {
            if (!containerRef.current || !taskChanges || taskChanges.length === 0) return;
            d3.select(containerRef.current).selectAll("*").remove();

            // Aggregate flows
            const flowMap = {};
            taskChanges.forEach(t => {
                const key = `${t.old_level}|${t.new_level}`;
                flowMap[key] = (flowMap[key] || 0) + 1;
            });

            // Build node list
            const allLevels = new Set();
            Object.keys(flowMap).forEach(k => { const [a, b] = k.split('|'); allLevels.add(a); allLevels.add(b); });
            const levelOrder = ['human_only', 'human_led', 'shared', 'ai_led', 'ai_only'];
            const sortedLevels = levelOrder.filter(l => allLevels.has(l));

            const nodes = [];
            const nodeIndex = {};
            sortedLevels.forEach(l => {
                nodeIndex['src_' + l] = nodes.length;
                nodes.push({ name: l.replace(/_/g, ' ') + ' (before)', id: 'src_' + l });
            });
            sortedLevels.forEach(l => {
                nodeIndex['tgt_' + l] = nodes.length;
                nodes.push({ name: l.replace(/_/g, ' ') + ' (after)', id: 'tgt_' + l });
            });

            const links = Object.entries(flowMap).map(([key, value]) => {
                const [src, tgt] = key.split('|');
                return { source: nodeIndex['src_' + src], target: nodeIndex['tgt_' + tgt], value };
            }).filter(l => l.source !== undefined && l.target !== undefined);

            if (links.length === 0) return;

            const margin = { top: 10, right: 10, bottom: 10, left: 10 };
            const w = width - margin.left - margin.right;
            const h = height - margin.top - margin.bottom;

            const svg = d3.select(containerRef.current)
                .append("svg")
                .attr("viewBox", `0 0 ${width} ${height}`)
                .attr("width", "100%")
                .attr("height", height);

            const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

            const sankey = d3.sankey()
                .nodeWidth(18)
                .nodePadding(12)
                .extent([[0, 0], [w, h]]);

            const { nodes: sNodes, links: sLinks } = sankey({ nodes: nodes.map(d => ({...d})), links: links.map(d => ({...d})) });

            // Links
            g.append("g").selectAll("path")
                .data(sLinks)
                .join("path")
                .attr("d", d3.sankeyLinkHorizontal())
                .attr("fill", "none")
                .attr("stroke", d => {
                    const tgtLevel = sortedLevels[d.target.index - sortedLevels.length] || 'shared';
                    return LEVEL_COLORS[tgtLevel] || '#94a3b8';
                })
                .attr("stroke-opacity", 0.4)
                .attr("stroke-width", d => Math.max(1, d.width));

            // Nodes
            g.append("g").selectAll("rect")
                .data(sNodes)
                .join("rect")
                .attr("x", d => d.x0).attr("y", d => d.y0)
                .attr("width", d => d.x1 - d.x0)
                .attr("height", d => Math.max(1, d.y1 - d.y0))
                .attr("fill", d => {
                    const level = d.id.replace(/^(src_|tgt_)/, '');
                    return LEVEL_COLORS[level] || '#94a3b8';
                })
                .attr("rx", 3);

            // Labels
            g.append("g").selectAll("text")
                .data(sNodes)
                .join("text")
                .attr("x", d => d.x0 < w / 2 ? d.x0 - 6 : d.x1 + 6)
                .attr("y", d => (d.y0 + d.y1) / 2)
                .attr("dy", "0.35em")
                .attr("text-anchor", d => d.x0 < w / 2 ? "end" : "start")
                .attr("font-size", 11)
                .attr("fill", "#374151")
                .text(d => d.name);

        }, [taskChanges, width, height]);

        if (!taskChanges || taskChanges.length === 0) return null;
        return html`<div ref=${containerRef} class="chart-animate" style=${{width:'100%'}}></div>`;
    }

    // ── CascadeFlow ───────────────────────────────────────────────────

    function CascadeFlow({ cascade }) {
        const [visibleSteps, setVisibleSteps] = useState(0);

        useEffect(() => {
            setVisibleSteps(0);
            const steps = 7;
            let step = 0;
            const timer = setInterval(() => {
                step++;
                setVisibleSteps(step);
                if (step >= steps) clearInterval(timer);
            }, 300);
            return () => clearInterval(timer);
        }, [cascade]);

        const steps = [
            { label: 'Tasks', value: cascade.task_changes?.tasks_affected || 0, color: 'bg-brand-100 text-brand-700 border-brand-200', icon: '\u2699\uFE0F' },
            { label: 'Workloads', value: cascade.workload_changes?.workloads_affected || 0, color: 'bg-blue-100 text-blue-700 border-blue-200', icon: '\u{1F4CB}' },
            { label: 'Roles', value: cascade.role_impacts?.roles_affected || 0, color: 'bg-brand-100 text-brand-700 border-brand-200', icon: '\u{1F465}' },
            { label: 'Skills', value: Math.abs(cascade.skill_shifts?.net_skill_shift || 0), color: 'bg-green-100 text-green-700 border-green-200', icon: '\u{1F4A1}' },
            { label: 'Workforce', value: Math.round(cascade.workforce?.freed_headcount || 0), color: 'bg-amber-100 text-amber-700 border-amber-200', icon: '\u{1F464}' },
            { label: 'Financial', value: fmt.currency(cascade.financial?.net_impact), color: 'bg-emerald-100 text-emerald-700 border-emerald-200', icon: '\u{1F4B0}' },
            { label: 'Risks', value: cascade.risks?.risk_count || 0, color: 'bg-red-100 text-red-700 border-red-200', icon: '\u26A0\uFE0F' },
        ];

        return html`
            <div class="flex items-center gap-1 flex-wrap">
                ${steps.map((step, i) => html`
                    <div key=${i} class="flex items-center" style=${{opacity: i < visibleSteps ? 1 : 0.15, transition: 'opacity 0.3s ease'}}>
                        <div class="cascade-step px-3 py-2 border rounded-lg ${step.color} text-center min-w-[80px]"
                             style=${{animationDelay: `${i * 0.3}s`}}>
                            <div class="text-lg">${step.icon}</div>
                            <div class="font-bold text-sm">${step.value}</div>
                            <div class="text-xs opacity-80">${step.label}</div>
                        </div>
                        ${i < steps.length - 1 && html`
                            <svg width="24" height="16" class="mx-0.5 flex-shrink-0" style=${{opacity: i < visibleSteps - 1 ? 1 : 0.15}}>
                                <line x1="0" y1="8" x2="18" y2="8" stroke="#d1d5db" stroke-width="2" class="${i < visibleSteps - 1 ? 'draw-in' : ''}" />
                                <polygon points="16,4 24,8 16,12" fill="#d1d5db" />
                            </svg>
                        `}
                    </div>
                `)}
            </div>
        `;
    }

    // ── HeadcountCompareChart ─────────────────────────────────────────

    function HeadcountCompareChart({ roleImpacts }) {
        if (!roleImpacts || roleImpacts.length === 0) return null;

        const labels = roleImpacts.map(r => r.role_name || 'Unknown');
        const currentHC = roleImpacts.map(r =>
            (r.title_impacts || []).reduce((sum, ti) => sum + (ti.headcount || 0), 0)
        );
        const postHC = roleImpacts.map((r, i) => {
            const freed = r.freed_capacity_pct || 0;
            return Math.round(currentHC[i] * (1 - freed / 100));
        });

        const data = {
            labels,
            datasets: [
                { label: 'Current', data: currentHC, backgroundColor: CHART_COLORS.info, borderRadius: 4 },
                { label: 'Post-Automation', data: postHC, backgroundColor: CHART_COLORS.ai, borderRadius: 4 },
            ],
        };

        const options = {
            indexAxis: 'y',
            plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
            scales: {
                x: { beginAtZero: true, grid: { color: '#f3f4f6' } },
                y: { grid: { display: false } },
            },
        };

        const h = Math.max(200, roleImpacts.length * 50);
        return html`<${window.DT.ChartCanvas} type="bar" data=${data} options=${options} height="${h}px" />`;
    }

    // ── TaskDistributionDonut ─────────────────────────────────────────

    function TaskDistributionDonut({ tasks, height = "220px" }) {
        if (!tasks || tasks.length === 0) return null;

        const counts = {};
        tasks.forEach(t => {
            const level = t.automation_level || 'unknown';
            counts[level] = (counts[level] || 0) + 1;
        });

        const levelLabels = Object.keys(counts).map(l => l.replace(/_/g, ' '));
        const levelColors = Object.keys(counts).map(l => LEVEL_COLORS[l] || '#94a3b8');

        const data = {
            labels: levelLabels,
            datasets: [{ data: Object.values(counts), backgroundColor: levelColors, borderWidth: 2, borderColor: '#fff' }],
        };

        const options = {
            cutout: '55%',
            plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 }, padding: 8 } } },
        };

        return html`<${window.DT.ChartCanvas} type="doughnut" data=${data} options=${options} height=${height} />`;
    }

    // ── RedeploymentFlow ──────────────────────────────────────────────

    function RedeploymentFlow({ workforce }) {
        if (!workforce) return null;
        const current = Math.round(workforce.current_headcount || 0);
        const freed = Math.round(workforce.freed_headcount || 0);
        const redeployable = Math.round(workforce.redeployable || 0);
        const reduction = freed - redeployable;
        if (freed <= 0) return null;

        const w = 500, h = 120;
        const redeployPct = freed > 0 ? redeployable / freed : 0;

        return html`
            <div class="chart-animate" style=${{width:'100%',maxWidth:'500px',margin:'0 auto'}}>
                <svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}">
                    <!-- Current -->
                    <rect x="0" y="20" width="100" height="60" rx="8" fill=${CHART_COLORS.info} fill-opacity="0.15" stroke=${CHART_COLORS.info} stroke-width="1.5"/>
                    <text x="50" y="44" text-anchor="middle" font-size="12" font-weight="600" fill=${CHART_COLORS.info}>Current</text>
                    <text x="50" y="62" text-anchor="middle" font-size="16" font-weight="700" fill=${CHART_COLORS.info}>${current.toLocaleString()}</text>

                    <!-- Arrow to Freed -->
                    <line x1="105" y1="50" x2="155" y2="50" stroke="#d1d5db" stroke-width="2" marker-end="url(#arrowGray)"/>

                    <!-- Freed -->
                    <rect x="160" y="20" width="100" height="60" rx="8" fill=${CHART_COLORS.warning} fill-opacity="0.15" stroke=${CHART_COLORS.warning} stroke-width="1.5"/>
                    <text x="210" y="44" text-anchor="middle" font-size="12" font-weight="600" fill=${CHART_COLORS.warning}>Freed</text>
                    <text x="210" y="62" text-anchor="middle" font-size="16" font-weight="700" fill=${CHART_COLORS.warning}>${freed.toLocaleString()}</text>

                    <!-- Arrow to Redeployable -->
                    <line x1="265" y1="38" x2="345" y2="25" stroke=${CHART_COLORS.positive} stroke-width="2" marker-end="url(#arrowGreen)"/>
                    <!-- Arrow to Reduction -->
                    <line x1="265" y1="62" x2="345" y2="80" stroke=${CHART_COLORS.negative} stroke-width="2" marker-end="url(#arrowRed)"/>

                    <!-- Redeployable -->
                    <rect x="350" y="5" width="140" height="40" rx="8" fill=${CHART_COLORS.positive} fill-opacity="0.15" stroke=${CHART_COLORS.positive} stroke-width="1.5"/>
                    <text x="420" y="22" text-anchor="middle" font-size="10" font-weight="600" fill=${CHART_COLORS.positive}>Redeployable</text>
                    <text x="420" y="38" text-anchor="middle" font-size="14" font-weight="700" fill=${CHART_COLORS.positive}>${redeployable} (${Math.round(redeployPct*100)}%)</text>

                    <!-- Reduction -->
                    <rect x="350" y="60" width="140" height="40" rx="8" fill=${CHART_COLORS.negative} fill-opacity="0.15" stroke=${CHART_COLORS.negative} stroke-width="1.5"/>
                    <text x="420" y="77" text-anchor="middle" font-size="10" font-weight="600" fill=${CHART_COLORS.negative}>Net Reduction</text>
                    <text x="420" y="93" text-anchor="middle" font-size="14" font-weight="700" fill=${CHART_COLORS.negative}>${reduction} (${Math.round((1-redeployPct)*100)}%)</text>

                    <!-- Arrow markers -->
                    <defs>
                        <marker id="arrowGray" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0,0 8,3 0,6" fill="#d1d5db"/></marker>
                        <marker id="arrowGreen" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0,0 8,3 0,6" fill=${CHART_COLORS.positive}/></marker>
                        <marker id="arrowRed" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0,0 8,3 0,6" fill=${CHART_COLORS.negative}/></marker>
                    </defs>
                </svg>
            </div>
        `;
    }

    // ── RiskMatrix ────────────────────────────────────────────────────

    function RiskMatrix({ risks }) {
        const flags = risks?.flags || [];
        if (flags.length === 0) return null;

        const w = 400, h = 300;
        const margin = { top: 30, right: 20, bottom: 40, left: 70 };
        const iw = w - margin.left - margin.right;
        const ih = h - margin.top - margin.bottom;

        // Map risks to grid positions
        const severityMap = { high: 2, medium: 1, low: 0 };
        const typeMap = { high_automation: 2, workforce_reduction: 2, skill_gap: 1, broad_change: 1 };
        const labels = ['Low', 'Medium', 'High'];
        const gridColors = [
            ['#dcfce7', '#fef9c3', '#fde68a'],
            ['#fef9c3', '#fde68a', '#fecaca'],
            ['#fde68a', '#fecaca', '#fca5a5'],
        ];

        const plotted = flags.map((f, i) => ({
            x: (typeMap[f.type] ?? 1),
            y: severityMap[f.severity] ?? 1,
            label: (f.type || '').replace(/_/g, ' '),
            severity: f.severity,
            idx: i,
        }));

        const cellW = iw / 3, cellH = ih / 3;

        return html`
            <div class="chart-animate" style=${{width:'100%',maxWidth:'420px'}}>
                <svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}">
                    <g transform="translate(${margin.left},${margin.top})">
                        ${[0,1,2].map(row => [0,1,2].map(col => html`
                            <rect key="${row}-${col}" x=${col*cellW} y=${(2-row)*cellH} width=${cellW} height=${cellH}
                                  fill=${gridColors[row][col]} stroke="white" stroke-width="2" rx="4"/>
                        `))}
                        ${plotted.map((p, i) => html`
                            <circle key=${i}
                                cx=${p.x * cellW + cellW/2 + (i % 2 === 0 ? -8 : 8)}
                                cy=${(2-p.y) * cellH + cellH/2}
                                r="10" fill=${p.severity === 'high' ? CHART_COLORS.negative : CHART_COLORS.warning}
                                stroke="white" stroke-width="2"/>
                            <text x=${p.x * cellW + cellW/2 + (i % 2 === 0 ? -8 : 8)} y=${(2-p.y) * cellH + cellH/2 + 4}
                                  text-anchor="middle" font-size="10" fill="white" font-weight="700">${i+1}</text>
                        `)}
                        <!-- Axis labels -->
                        ${labels.map((l, i) => html`
                            <text key="y${i}" x="-8" y=${(2-i)*cellH + cellH/2 + 4} text-anchor="end" font-size="11" fill="#6b7280">${l}</text>
                            <text key="x${i}" x=${i*cellW + cellW/2} y=${ih + 20} text-anchor="middle" font-size="11" fill="#6b7280">${l}</text>
                        `)}
                    </g>
                    <text x=${margin.left - 50} y=${margin.top + ih/2} text-anchor="middle" transform="rotate(-90, ${margin.left - 50}, ${margin.top + ih/2})" font-size="12" fill="#374151" font-weight="600">Severity</text>
                    <text x=${margin.left + iw/2} y=${h - 5} text-anchor="middle" font-size="12" fill="#374151" font-weight="600">Impact</text>
                </svg>
            </div>
        `;
    }

    // ── HierarchyTree (Collapsible D3 Tree Layout) ──────────────────────

    function HierarchyTree({ data, width = 900, height = 500, onNodeClick }) {
        const containerRef = useRef(null);
        const [expanded, setExpanded] = useState(false);

        useEffect(() => {
            if (!containerRef.current || !data) return;

            const el = containerRef.current;
            d3.select(el).selectAll("*").remove();

            const margin = { top: 20, right: 120, bottom: 20, left: 60 };
            const w = width - margin.left - margin.right;
            const h = height - margin.top - margin.bottom;

            const TYPE_COLORS = {
                organization: '#1e40af',
                function: CHART_COLORS.info,
                sub_function: '#6366f1',
                job_family_group: CHART_COLORS.ai,
                job_family: '#c084fc',
                role: CHART_COLORS.positive,
            };
            const TYPE_ICONS = {
                organization: '\u{1F3E2}', function: '\u{1F4C1}',
                sub_function: '\u{1F4C2}', job_family_group: '\u{1F465}',
                job_family: '\u{1F464}', role: '\u{1F9D1}\u200D\u{1F4BC}',
            };

            // Build D3 hierarchy — initially collapse below depth 1
            const root = d3.hierarchy(data);
            root.descendants().forEach(d => {
                d._children = d.children;
                if (d.depth > 1) d.children = null;
            });

            const svg = d3.select(el)
                .append("svg")
                .attr("width", "100%")
                .attr("height", height)
                .attr("viewBox", `0 0 ${width} ${height}`)
                .style("font-family", "system-ui, sans-serif");

            const g = svg.append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);

            // Zoom
            const zoom = d3.zoom()
                .scaleExtent([0.3, 3])
                .on("zoom", (e) => g.attr("transform", e.transform));
            svg.call(zoom);
            svg.call(zoom.transform, d3.zoomIdentity.translate(margin.left, margin.top));

            const treeLayout = d3.tree().nodeSize([32, 220]);

            // Tooltip
            const tooltip = d3.select(el)
                .append("div")
                .style("position", "absolute")
                .style("pointer-events", "none")
                .style("background", "rgba(0,0,0,0.85)")
                .style("color", "white")
                .style("padding", "8px 12px")
                .style("border-radius", "6px")
                .style("font-size", "12px")
                .style("line-height", "1.5")
                .style("z-index", "100")
                .style("opacity", 0)
                .style("max-width", "250px");

            function update(source) {
                treeLayout(root);

                const nodes = root.descendants();
                const links = root.links();

                // Center the tree vertically
                let minY = Infinity, maxY = -Infinity;
                nodes.forEach(d => { minY = Math.min(minY, d.x); maxY = Math.max(maxY, d.x); });
                const offsetY = h / 2 - (minY + maxY) / 2;
                nodes.forEach(d => d.x += offsetY);

                // Transition
                const t = g.transition().duration(400);

                // Links
                const link = g.selectAll("path.link").data(links, d => d.target.data.id);
                link.enter()
                    .append("path")
                    .attr("class", "link")
                    .attr("fill", "none")
                    .attr("stroke", "#d1d5db")
                    .attr("stroke-width", 1.5)
                    .attr("d", () => {
                        const o = { x: source.x, y: source.y };
                        return diagonal({ source: o, target: o });
                    })
                    .merge(link)
                    .transition(t)
                    .attr("stroke", d => {
                        const c = TYPE_COLORS[d.target.data.type] || '#d1d5db';
                        return c + '60';
                    })
                    .attr("d", diagonal);

                link.exit().transition(t)
                    .attr("d", () => {
                        const o = { x: source.x, y: source.y };
                        return diagonal({ source: o, target: o });
                    })
                    .remove();

                // Nodes
                const node = g.selectAll("g.node").data(nodes, d => d.data.id);

                const nodeEnter = node.enter()
                    .append("g")
                    .attr("class", "node")
                    .attr("transform", `translate(${source.y},${source.x})`)
                    .style("cursor", "pointer")
                    .on("click", (e, d) => {
                        if (d._children || d.children) {
                            d.children = d.children ? null : d._children;
                            update(d);
                        }
                        if (onNodeClick) onNodeClick(d.data);
                    })
                    .on("mouseover", (e, d) => {
                        const nd = d.data;
                        let info = `<strong>${nd.name}</strong><br/>Type: ${(nd.type || '').replace(/_/g, ' ')}`;
                        if (nd.headcount) info += `<br/>Headcount: ${nd.headcount.toLocaleString()}`;
                        if (nd.role_count) info += `<br/>Roles: ${nd.role_count}`;
                        if (nd.task_count) info += `<br/>Tasks: ${nd.task_count}`;
                        if (nd.automation_potential) info += `<br/>Automation: ${Math.round(nd.automation_potential)}%`;
                        tooltip.html(info)
                            .style("opacity", 1)
                            .style("left", (e.offsetX + 15) + "px")
                            .style("top", (e.offsetY - 10) + "px");
                    })
                    .on("mousemove", (e) => {
                        tooltip.style("left", (e.offsetX + 15) + "px")
                               .style("top", (e.offsetY - 10) + "px");
                    })
                    .on("mouseout", () => {
                        tooltip.style("opacity", 0);
                    });

                // Circle
                nodeEnter.append("circle")
                    .attr("r", 0)
                    .attr("fill", d => TYPE_COLORS[d.data.type] || '#6b7280')
                    .attr("stroke", d => d3.color(TYPE_COLORS[d.data.type] || '#6b7280').darker(0.4))
                    .attr("stroke-width", 2);

                // Label
                nodeEnter.append("text")
                    .attr("dy", "0.32em")
                    .attr("x", d => (d._children || d.children) ? -14 : 14)
                    .attr("text-anchor", d => (d._children || d.children) ? "end" : "start")
                    .attr("font-size", d => d.depth === 0 ? 13 : d.depth === 1 ? 12 : 11)
                    .attr("font-weight", d => d.depth <= 1 ? 600 : 400)
                    .attr("fill", "#374151")
                    .text(d => {
                        const name = d.data.name;
                        const hc = d.data.headcount;
                        return hc > 0 ? `${name} (${hc.toLocaleString()})` : name;
                    });

                // Expand/collapse indicator
                nodeEnter.append("text")
                    .attr("class", "expand-icon")
                    .attr("dy", "0.35em")
                    .attr("text-anchor", "middle")
                    .attr("font-size", 8)
                    .attr("fill", "white")
                    .attr("font-weight", 700)
                    .text(d => d._children && !d.children ? '+' : d.children && d.children.length ? '\u2212' : '');

                // Update
                const nodeUpdate = nodeEnter.merge(node);
                nodeUpdate.transition(t)
                    .attr("transform", d => `translate(${d.y},${d.x})`);

                nodeUpdate.select("circle")
                    .attr("r", d => d.depth === 0 ? 10 : d._children && !d.children ? 8 : 6)
                    .attr("fill", d => {
                        if (d._children && !d.children) {
                            return d3.color(TYPE_COLORS[d.data.type] || '#6b7280').darker(0.2);
                        }
                        return TYPE_COLORS[d.data.type] || '#6b7280';
                    });

                nodeUpdate.select(".expand-icon")
                    .text(d => d._children && !d.children ? '+' : d.children && d.children.length ? '\u2212' : '');

                // Exit
                node.exit().transition(t)
                    .attr("transform", `translate(${source.y},${source.x})`)
                    .remove()
                    .select("circle").attr("r", 0);
            }

            function diagonal(d) {
                return `M${d.source.y},${d.source.x}
                        C${(d.source.y + d.target.y) / 2},${d.source.x}
                         ${(d.source.y + d.target.y) / 2},${d.target.x}
                         ${d.target.y},${d.target.x}`;
            }

            update(root);

        }, [data, width, height]);

        const toggleAll = () => {
            // Re-render with expanded/collapsed state
            setExpanded(prev => !prev);
        };

        // Re-run effect when expanded changes by rebuilding with all nodes expanded
        useEffect(() => {
            if (!containerRef.current || !data) return;
            // The main effect handles rendering; toggling expanded triggers full re-render
        }, [expanded]);

        return html`
            <div ref=${containerRef} class="chart-animate"
                 style=${{position:'relative', width:'100%', overflow:'hidden', borderRadius:'8px', background:'#fafbfc'}}>
            </div>
        `;
    }

    // ── InteractiveGraph (Entity-Level Force Graph) ───────────────────

    const EDGE_COLORS = {
        DT_CONTAINS: '#93c5fd',
        DT_HAS_ROLE: '#a78bfa',
        DT_HAS_TITLE: '#c4b5fd',
        DT_HAS_WORKLOAD: '#c084fc',
        DT_CONTAINS_TASK: '#d8b4fe',
        DT_REQUIRES_SKILL: '#86efac',
        DT_USES_TECHNOLOGY: '#6ee7b7',
        DT_ADJACENT_TO: '#fcd34d',
        DT_PART_OF_WORKFLOW: '#fdba74',
        DT_TASK_USES_ROLE: '#fca5a5',
    };

    const NODE_TYPE_LABELS = {
        DTOrganization: 'Organization', DTFunction: 'Function',
        DTSubFunction: 'Sub-Function', DTJobFamilyGroup: 'Job Family Group',
        DTJobFamily: 'Job Family', DTRole: 'Role', DTJobTitle: 'Job Title',
        DTWorkload: 'Workload', DTTask: 'Task',
        DTSkill: 'Skill', DTTechnology: 'Technology',
        DTWorkflow: 'Workflow', DTWorkflowTask: 'Workflow Task',
    };

    const NODE_RADII = {
        DTOrganization: 18, DTFunction: 14, DTSubFunction: 10,
        DTJobFamilyGroup: 8, DTJobFamily: 8,
        DTRole: 11, DTJobTitle: 6, DTWorkload: 7, DTTask: 5,
        DTSkill: 7, DTTechnology: 8,
        DTWorkflow: 9, DTWorkflowTask: 5,
    };

    function InteractiveGraph({ nodes, edges, selectedNodeId, onNodeClick, width = 900, height = 600, filters, onZoomControlsReady }) {
        const containerRef = useRef(null);
        const simRef = useRef(null);

        useEffect(() => {
            if (!containerRef.current || !nodes || nodes.length === 0) return;

            const el = containerRef.current;
            d3.select(el).selectAll("*").remove();

            // Filter nodes by visible types
            const visibleTypes = filters ? new Set(filters) : null;
            const filteredNodes = visibleTypes
                ? nodes.filter(n => visibleTypes.has(n.label))
                : nodes;
            const nodeIdSet = new Set(filteredNodes.map(n => n.id));
            const filteredEdges = edges.filter(e =>
                nodeIdSet.has(e.source) && nodeIdSet.has(e.target)
            );

            // Build D3 data
            const simNodes = filteredNodes.map(n => ({
                ...n,
                r: NODE_RADII[n.label] || 6,
                category: NODE_CATEGORIES[n.label] || 'taxonomy',
                displayLabel: NODE_TYPE_LABELS[n.label] || n.label,
            }));
            const nodeMap = {};
            simNodes.forEach(n => { nodeMap[n.id] = n; });

            const simLinks = filteredEdges
                .filter(e => nodeMap[e.source] && nodeMap[e.target])
                .map(e => ({
                    source: e.source,
                    target: e.target,
                    type: e.type,
                }));

            const svg = d3.select(el)
                .append("svg")
                .attr("width", "100%")
                .attr("height", height)
                .attr("viewBox", `0 0 ${width} ${height}`)
                .style("font-family", "system-ui, sans-serif")
                .style("background", "#fafbfc")
                .style("border-radius", "8px");

            // Arrow markers
            const defs = svg.append("defs");
            Object.keys(EDGE_COLORS).forEach(rel => {
                defs.append("marker")
                    .attr("id", `arrow-${rel}`)
                    .attr("viewBox", "0 0 10 6")
                    .attr("refX", 20).attr("refY", 3)
                    .attr("markerWidth", 8).attr("markerHeight", 6)
                    .attr("orient", "auto")
                    .append("polygon")
                    .attr("points", "0,0 10,3 0,6")
                    .attr("fill", EDGE_COLORS[rel] || "#d1d5db");
            });

            const g = svg.append("g");

            // Zoom
            const zoom = d3.zoom()
                .scaleExtent([0.2, 4])
                .on("zoom", (e) => g.attr("transform", e.transform));
            svg.call(zoom);

            // Expose zoom controls to parent
            if (onZoomControlsReady) {
                onZoomControlsReady({
                    zoomIn: () => svg.transition().duration(300).call(zoom.scaleBy, 1.3),
                    zoomOut: () => svg.transition().duration(300).call(zoom.scaleBy, 0.77),
                    fitAll: () => {
                        const bounds = g.node().getBBox();
                        if (bounds.width > 0 && bounds.height > 0) {
                            const sc = Math.min(0.9 * width / bounds.width, 0.9 * height / bounds.height, 1.5);
                            const tx = width / 2 - sc * (bounds.x + bounds.width / 2);
                            const ty = height / 2 - sc * (bounds.y + bounds.height / 2);
                            svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(sc));
                        }
                    },
                });
            }

            // Tooltip
            const tooltip = d3.select(el)
                .append("div")
                .style("position", "absolute")
                .style("pointer-events", "none")
                .style("background", "rgba(15,23,42,0.9)")
                .style("color", "white")
                .style("padding", "8px 12px")
                .style("border-radius", "8px")
                .style("font-size", "12px")
                .style("line-height", "1.6")
                .style("z-index", "100")
                .style("opacity", 0)
                .style("max-width", "280px")
                .style("box-shadow", "0 4px 12px rgba(0,0,0,0.15)");

            // Force simulation
            const sim = d3.forceSimulation(simNodes)
                .force("link", d3.forceLink(simLinks).id(d => d.id).distance(d => {
                    const s = nodeMap[typeof d.source === 'string' ? d.source : d.source.id];
                    const t = nodeMap[typeof d.target === 'string' ? d.target : d.target.id];
                    return ((s?.r || 6) + (t?.r || 6)) * 2.5 + 30;
                }))
                .force("charge", d3.forceManyBody().strength(d => -(d.r || 6) * 12))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collide", d3.forceCollide().radius(d => (d.r || 6) + 4))
                .force("x", d3.forceX(width / 2).strength(0.03))
                .force("y", d3.forceY(height / 2).strength(0.03));

            simRef.current = sim;

            // Links
            const link = g.append("g")
                .selectAll("line")
                .data(simLinks)
                .join("line")
                .attr("stroke", d => EDGE_COLORS[d.type] || "#d1d5db")
                .attr("stroke-width", 1.2)
                .attr("stroke-opacity", 0.5)
                .attr("marker-end", d => `url(#arrow-${d.type})`);

            // Nodes
            const node = g.append("g")
                .selectAll("g")
                .data(simNodes)
                .join("g")
                .style("cursor", "pointer")
                .call(d3.drag()
                    .on("start", (e, d) => {
                        if (!e.active) sim.alphaTarget(0.3).restart();
                        d.fx = d.x; d.fy = d.y;
                    })
                    .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
                    .on("end", (e, d) => {
                        if (!e.active) sim.alphaTarget(0);
                        d.fx = null; d.fy = null;
                    })
                );

            node.append("circle")
                .attr("r", d => d.r)
                .attr("fill", d => {
                    if (d.id === selectedNodeId) return '#f59e0b';
                    return NODE_TYPE_COLORS[d.label] || CATEGORY_COLORS[d.category] || CHART_COLORS.info;
                })
                .attr("fill-opacity", 0.85)
                .attr("stroke", d => {
                    if (d.id === selectedNodeId) return '#d97706';
                    const base = NODE_TYPE_COLORS[d.label] || CATEGORY_COLORS[d.category] || CHART_COLORS.info;
                    return d3.color(base).darker(0.5);
                })
                .attr("stroke-width", d => d.id === selectedNodeId ? 3 : 1.5);

            // Node label (all nodes, font scales with radius — increased sizes)
            node.append("text")
                .text(d => {
                    const n = d.name || '';
                    const maxLen = d.r >= 10 ? 22 : d.r >= 8 ? 18 : 14;
                    return n.length > maxLen ? n.substring(0, maxLen - 2) + '\u2026' : n;
                })
                .attr("text-anchor", "middle")
                .attr("dy", d => d.r + 14)
                .attr("font-size", d => d.r >= 14 ? 12 : d.r >= 10 ? 11 : d.r >= 7 ? 10 : 8)
                .attr("fill", "#374151")
                .attr("font-weight", 500)
                .style("pointer-events", "none");

            // Click
            node.on("click", (e, d) => {
                e.stopPropagation();
                if (onNodeClick) onNodeClick(d);
            });

            // Hover
            node.on("mouseover", (e, d) => {
                let info = `<strong>${d.name || d.id}</strong><br/>`;
                info += `<span style="opacity:0.7">${d.displayLabel}</span>`;
                if (d.headcount) info += `<br/>Headcount: ${d.headcount.toLocaleString()}`;
                if (d.automation != null) info += `<br/>Automation: ${Math.round(d.automation)}%`;
                if (d.description) {
                    const desc = d.description.length > 80 ? d.description.substring(0, 78) + '...' : d.description;
                    info += `<br/><span style="opacity:0.6;font-size:11px">${desc}</span>`;
                }
                tooltip.html(info)
                    .style("opacity", 1)
                    .style("left", (e.offsetX + 15) + "px")
                    .style("top", (e.offsetY - 10) + "px");

                // Highlight connected
                const connected = new Set();
                simLinks.forEach(l => {
                    const sid = typeof l.source === 'string' ? l.source : l.source.id;
                    const tid = typeof l.target === 'string' ? l.target : l.target.id;
                    if (sid === d.id) connected.add(tid);
                    if (tid === d.id) connected.add(sid);
                });
                connected.add(d.id);

                node.select("circle")
                    .attr("fill-opacity", n => connected.has(n.id) ? 1 : 0.2)
                    .attr("stroke-opacity", n => connected.has(n.id) ? 1 : 0.2);
                node.selectAll("text")
                    .attr("opacity", n => connected.has(n.id) ? 1 : 0.15);
                link.attr("stroke-opacity", l => {
                    const sid = typeof l.source === 'string' ? l.source : l.source.id;
                    const tid = typeof l.target === 'string' ? l.target : l.target.id;
                    return (sid === d.id || tid === d.id) ? 0.8 : 0.05;
                });
            })
            .on("mousemove", (e) => {
                tooltip.style("left", (e.offsetX + 15) + "px")
                       .style("top", (e.offsetY - 10) + "px");
            })
            .on("mouseout", () => {
                tooltip.style("opacity", 0);
                node.select("circle").attr("fill-opacity", 0.85).attr("stroke-opacity", 1);
                node.selectAll("text").attr("opacity", 1);
                link.attr("stroke-opacity", 0.5);
            });

            // Click background to deselect
            svg.on("click", () => {
                if (onNodeClick) onNodeClick(null);
            });

            sim.on("tick", () => {
                link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
                node.attr("transform", d => `translate(${d.x},${d.y})`);
            });

            // Fit zoom after stabilization
            sim.on("end", () => {
                const bounds = g.node().getBBox();
                if (bounds.width > 0 && bounds.height > 0) {
                    const scale = Math.min(
                        0.9 * width / bounds.width,
                        0.9 * height / bounds.height,
                        1.5
                    );
                    const tx = width / 2 - scale * (bounds.x + bounds.width / 2);
                    const ty = height / 2 - scale * (bounds.y + bounds.height / 2);
                    svg.transition().duration(500)
                        .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
                }
            });

            return () => { sim.stop(); };
        }, [nodes, edges, selectedNodeId, width, height, filters ? filters.join(',') : '']);

        if (!nodes || nodes.length === 0) {
            return html`<div class="flex items-center justify-center text-gray-400 text-sm" style=${{height: height + 'px'}}>
                No graph data available
            </div>`;
        }

        return html`<div ref=${containerRef} class="chart-animate"
            style=${{position:'relative', width:'100%', overflow:'hidden'}}></div>`;
    }

    // ── InteractiveGraph3D (WebGL 3D Force Graph) ─────────────────────

    function InteractiveGraph3D({ nodes, edges, selectedNodeId, onNodeClick, width = 900, height = 600, filters, onZoomControlsReady }) {
        const containerRef = useRef(null);
        const graphRef = useRef(null);

        useEffect(() => {
            if (!containerRef.current || !nodes || nodes.length === 0) return;
            if (typeof ForceGraph3D === 'undefined') return;

            const el = containerRef.current;

            // Filter nodes by visible types
            const visibleTypes = filters ? new Set(filters) : null;
            const filteredNodes = visibleTypes
                ? nodes.filter(n => visibleTypes.has(n.label))
                : nodes;
            const nodeIdSet = new Set(filteredNodes.map(n => n.id));
            const filteredEdges = edges.filter(e =>
                nodeIdSet.has(e.source) && nodeIdSet.has(e.target)
            );

            // Build graph data (clone to avoid mutation)
            const graphNodes = filteredNodes.map(n => ({
                id: n.id,
                name: n.name || n.id,
                label: n.label,
                displayLabel: NODE_TYPE_LABELS[n.label] || n.label,
                val: (NODE_RADII[n.label] || 6) * 0.6,
                color: n.id === selectedNodeId
                    ? '#f59e0b'
                    : (NODE_TYPE_COLORS[n.label] || CATEGORY_COLORS[NODE_CATEGORIES[n.label] || 'taxonomy'] || CHART_COLORS.info),
                headcount: n.headcount,
                automation: n.automation,
                description: n.description,
            }));
            const graphLinks = filteredEdges
                .filter(e => nodeIdSet.has(e.source) && nodeIdSet.has(e.target))
                .map(e => ({
                    source: e.source,
                    target: e.target,
                    type: e.type,
                    color: (EDGE_COLORS[e.type] || '#d1d5db') + '99',
                }));

            // Destroy previous instance
            if (graphRef.current) {
                graphRef.current._destructor();
                graphRef.current = null;
            }
            // Clear container children
            while (el.firstChild) el.removeChild(el.firstChild);

            // Helper: create a text sprite for node labels
            function makeTextSprite(text, color) {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                const fontSize = 48;
                ctx.font = `500 ${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;
                const truncated = text.length > 18 ? text.substring(0, 16) + '...' : text;
                const textWidth = ctx.measureText(truncated).width;
                canvas.width = textWidth + 16;
                canvas.height = fontSize + 12;
                // Re-set font after resize
                ctx.font = `500 ${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;
                ctx.fillStyle = color || '#374151';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(truncated, canvas.width / 2, canvas.height / 2);

                const texture = new THREE.CanvasTexture(canvas);
                texture.minFilter = THREE.LinearFilter;
                const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
                const sprite = new THREE.Sprite(spriteMat);
                // Scale sprite so text is readable (~proportional to canvas)
                const scaleFactor = 0.15;
                sprite.scale.set(canvas.width * scaleFactor, canvas.height * scaleFactor, 1);
                return sprite;
            }

            const graph = ForceGraph3D()(el)
                .width(width)
                .height(height)
                .backgroundColor('#fafbfc')
                .graphData({ nodes: graphNodes, links: graphLinks })
                // Custom node: sphere + text label
                .nodeThreeObject(node => {
                    const group = new THREE.Group();
                    // Sphere
                    const radius = Math.max(2, (node.val || 4) * 0.8);
                    const geo = new THREE.SphereGeometry(radius, 16, 12);
                    const mat = new THREE.MeshLambertMaterial({ color: node.color, transparent: true, opacity: 0.9 });
                    const sphere = new THREE.Mesh(geo, mat);
                    group.add(sphere);
                    // Text label below sphere
                    const label = makeTextSprite(node.name, '#374151');
                    label.position.set(0, -(radius + 5), 0);
                    group.add(label);
                    return group;
                })
                .nodeThreeObjectExtend(false)
                .nodeLabel(n => {
                    let tip = `<div style="background:rgba(15,23,42,0.92);color:white;padding:8px 12px;border-radius:8px;font-size:12px;line-height:1.6;max-width:280px;box-shadow:0 4px 12px rgba(0,0,0,0.15)">`;
                    tip += `<strong>${n.name}</strong><br/>`;
                    tip += `<span style="opacity:0.7">${n.displayLabel}</span>`;
                    if (n.headcount) tip += `<br/>Headcount: ${n.headcount.toLocaleString()}`;
                    if (n.automation != null) tip += `<br/>Automation: ${Math.round(n.automation)}%`;
                    if (n.description) {
                        const desc = n.description.length > 80 ? n.description.substring(0, 78) + '...' : n.description;
                        tip += `<br/><span style="opacity:0.6;font-size:11px">${desc}</span>`;
                    }
                    tip += '</div>';
                    return tip;
                })
                // Link styling
                .linkColor('color')
                .linkWidth(0.8)
                .linkOpacity(0.6)
                .linkDirectionalArrowLength(3.5)
                .linkDirectionalArrowRelPos(1)
                // Interaction
                .onNodeClick(node => {
                    if (onNodeClick) onNodeClick(node);
                })
                .onBackgroundClick(() => {
                    if (onNodeClick) onNodeClick(null);
                })
                // Force tuning
                .d3Force('charge', d3.forceManyBody().strength(n => -(n.val || 6) * 25))
                .d3Force('link', d3.forceLink().id(d => d.id).distance(d => {
                    const sVal = d.source.val || 6;
                    const tVal = d.target.val || 6;
                    return (sVal + tVal) * 4 + 40;
                }));

            // Enable panning (right-click drag or Ctrl+left-click drag)
            const controls = graph.controls();
            controls.enablePan = true;
            controls.screenSpacePanning = true;   // pan up/down in screen space

            graphRef.current = graph;

            // Expose zoom controls to parent
            if (onZoomControlsReady) {
                onZoomControlsReady({
                    zoomIn: () => {
                        if (!graphRef.current) return;
                        const cam = graphRef.current.camera();
                        cam.position.multiplyScalar(0.77);
                    },
                    zoomOut: () => {
                        if (!graphRef.current) return;
                        const cam = graphRef.current.camera();
                        cam.position.multiplyScalar(1.3);
                    },
                    fitAll: () => {
                        if (!graphRef.current) return;
                        graphRef.current.zoomToFit(400);
                    },
                });
            }

            return () => {
                if (graphRef.current) {
                    graphRef.current._destructor();
                    graphRef.current = null;
                }
            };
        }, [nodes, edges, selectedNodeId, width, height, filters ? filters.join(',') : '']);

        // Resize handling
        useEffect(() => {
            if (graphRef.current && width && height) {
                graphRef.current.width(width).height(height);
            }
        }, [width, height]);

        if (!nodes || nodes.length === 0) {
            return html`<div class="flex items-center justify-center text-gray-400 text-sm" style=${{height: height + 'px'}}>
                No graph data available
            </div>`;
        }

        return html`<div ref=${containerRef} class="graph-3d-container"
            style=${{position:'relative', width:'100%', height: height + 'px', overflow:'hidden', borderRadius:'12px'}}></div>`;
    }

    // ── v2 Time-Series: Adoption S-Curve ──────────────────────────────

    function AdoptionSCurve({ snapshots, breakevenMonth }) {
        if (!snapshots || snapshots.length === 0) return null;

        const months = snapshots.map(s => `Mo ${s.month}`);
        const adoption = snapshots.map(s => Math.round((s.adoption?.level || 0) * 100));

        const datasets = [{
            label: 'Adoption %',
            data: adoption,
            borderColor: CHART_COLORS.ai,
            backgroundColor: CHART_COLORS.ai + '20',
            fill: true, tension: 0.4, pointRadius: 1, pointHoverRadius: 4,
            borderWidth: 2.5,
        }];

        const annotations = {};
        if (breakevenMonth && breakevenMonth > 0) {
            annotations.breakeven = {
                type: 'line', xMin: breakevenMonth, xMax: breakevenMonth,
                borderColor: CHART_COLORS.positive, borderDash: [6, 3], borderWidth: 1.5,
                label: { display: true, content: `Breakeven Mo ${breakevenMonth}`, position: 'start',
                         font: { size: 10 }, backgroundColor: CHART_COLORS.positive + 'CC' },
            };
        }

        const options = {
            plugins: {
                legend: { display: false },
                annotation: Object.keys(annotations).length > 0 ? { annotations } : undefined,
            },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } },
                y: { min: 0, max: 100, ticks: { callback: v => v + '%' }, grid: { color: '#f3f4f6' } },
            },
        };

        return html`
            <div>
                <div class="text-sm font-medium text-gray-600 mb-2">Technology Adoption Curve (S-Curve)</div>
                <${window.DT.ChartCanvas} type="line" data=${{ labels: months, datasets }} options=${options} height="260px" />
            </div>
        `;
    }

    // ── v2 Time-Series: Human Factors Chart ───────────────────────────

    function HumanFactorsChart({ snapshots }) {
        if (!snapshots || snapshots.length === 0) return null;

        const months = snapshots.map(s => `Mo ${s.month}`);
        const hf = snapshots.map(s => s.human_factors || {});

        const datasets = [
            { label: 'Resistance', data: hf.map(h => (h.resistance || 0).toFixed(2)),
              borderColor: CHART_COLORS.negative, backgroundColor: CHART_COLORS.negative + '10',
              borderWidth: 2, tension: 0.3, pointRadius: 0, fill: false },
            { label: 'Morale', data: hf.map(h => (h.morale || 0).toFixed(2)),
              borderColor: CHART_COLORS.warning, backgroundColor: CHART_COLORS.warning + '10',
              borderWidth: 2, tension: 0.3, pointRadius: 0, fill: false },
            { label: 'Proficiency', data: hf.map(h => (h.proficiency || 0).toFixed(2)),
              borderColor: CHART_COLORS.positive, backgroundColor: CHART_COLORS.positive + '10',
              borderWidth: 2, tension: 0.3, pointRadius: 0, fill: false },
            { label: 'Culture', data: hf.map(h => (h.culture_readiness || 0).toFixed(2)),
              borderColor: CHART_COLORS.info, backgroundColor: CHART_COLORS.info + '10',
              borderWidth: 2, tension: 0.3, pointRadius: 0, fill: false },
        ];

        const options = {
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
            },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } },
                y: { min: 0, max: 1, ticks: { callback: v => (v * 100).toFixed(0) + '%' }, grid: { color: '#f3f4f6' } },
            },
        };

        return html`
            <div>
                <div class="text-sm font-medium text-gray-600 mb-2">Human Factors Evolution</div>
                <${window.DT.ChartCanvas} type="line" data=${{ labels: months, datasets }} options=${options} height="260px" />
            </div>
        `;
    }

    // ── v2 Time-Series: Financial Trajectory ──────────────────────────

    function FinancialTrajectory({ snapshots, paybackMonth }) {
        if (!snapshots || snapshots.length === 0) return null;

        const months = snapshots.map(s => `Mo ${s.month}`);
        const fin = snapshots.map(s => s.financial || {});

        const datasets = [
            { label: 'Cumulative Savings', data: fin.map(f => f.cumulative_savings || 0),
              borderColor: CHART_COLORS.positive, backgroundColor: CHART_COLORS.positive + '15',
              fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 },
            { label: 'Cumulative Costs', data: fin.map(f => f.cumulative_costs || 0),
              borderColor: CHART_COLORS.negative, backgroundColor: CHART_COLORS.negative + '10',
              fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2, borderDash: [5, 3] },
            { label: 'Cumulative Net', data: fin.map(f => f.cumulative_net || 0),
              borderColor: CHART_COLORS.info, backgroundColor: CHART_COLORS.info + '10',
              fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2.5 },
        ];

        const annotations = {};
        if (paybackMonth && paybackMonth > 0 && paybackMonth <= snapshots.length) {
            annotations.payback = {
                type: 'line', xMin: paybackMonth, xMax: paybackMonth,
                borderColor: CHART_COLORS.positive, borderDash: [6, 3], borderWidth: 1.5,
                label: { display: true, content: `Payback Mo ${paybackMonth}`, position: 'start',
                         font: { size: 10 }, backgroundColor: CHART_COLORS.positive + 'CC' },
            };
        }

        const options = {
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                annotation: Object.keys(annotations).length > 0 ? { annotations } : undefined,
            },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } },
                y: { ticks: { callback: v => fmt.currency(v) }, grid: { color: '#f3f4f6' } },
            },
        };

        return html`
            <div>
                <div class="text-sm font-medium text-gray-600 mb-2">Financial Trajectory</div>
                <${window.DT.ChartCanvas} type="line" data=${{ labels: months, datasets }} options=${options} height="280px" />
            </div>
        `;
    }

    // ── v2 Time-Series: Feedback Loop Timeline ────────────────────────

    function FeedbackLoopTimeline({ snapshots }) {
        if (!snapshots || snapshots.length === 0) return null;
        const containerRef = useRef(null);

        const LOOP_META = {
            R1: { name: 'Productivity Flywheel', type: 'reinforcing', color: CHART_COLORS.positive },
            R2: { name: 'Capability Compound', type: 'reinforcing', color: '#06b6d4' },
            B1: { name: 'Change Resistance', type: 'balancing', color: CHART_COLORS.negative },
            B2: { name: 'Skill Gap Brake', type: 'balancing', color: CHART_COLORS.warning },
            B3: { name: 'Knowledge Drain', type: 'balancing', color: '#f97316' },
        };

        useEffect(() => {
            if (!containerRef.current) return;
            const el = containerRef.current;
            d3.select(el).selectAll("*").remove();

            const loops = Object.keys(LOOP_META);
            const margin = { top: 20, right: 20, bottom: 30, left: 140 };
            const rowH = 28;
            const w = 700;
            const h = margin.top + margin.bottom + loops.length * rowH;
            const iw = w - margin.left - margin.right;

            const svg = d3.select(el)
                .append("svg")
                .attr("viewBox", `0 0 ${w} ${h}`)
                .attr("width", "100%")
                .attr("height", h);

            const xScale = d3.scaleLinear()
                .domain([0, snapshots.length])
                .range([margin.left, margin.left + iw]);

            // Grid
            svg.append("g")
                .selectAll("line")
                .data(d3.range(0, snapshots.length + 1, 6))
                .join("line")
                .attr("x1", d => xScale(d)).attr("x2", d => xScale(d))
                .attr("y1", margin.top).attr("y2", h - margin.bottom)
                .attr("stroke", "#e5e7eb").attr("stroke-dasharray", "2,2");

            // X-axis labels
            svg.append("g")
                .selectAll("text")
                .data(d3.range(0, snapshots.length + 1, 6))
                .join("text")
                .attr("x", d => xScale(d))
                .attr("y", h - 8)
                .attr("text-anchor", "middle")
                .attr("font-size", 10)
                .attr("fill", "#6b7280")
                .text(d => `Mo ${d}`);

            loops.forEach((loopId, i) => {
                const meta = LOOP_META[loopId];
                const y = margin.top + i * rowH;

                // Row label
                svg.append("text")
                    .attr("x", margin.left - 8)
                    .attr("y", y + rowH / 2 + 4)
                    .attr("text-anchor", "end")
                    .attr("font-size", 11)
                    .attr("fill", meta.color)
                    .attr("font-weight", 500)
                    .text(meta.name);

                // Find active periods
                let inActive = false;
                let start = 0;
                snapshots.forEach((snap, mi) => {
                    const active = (snap.active_feedback_loops || []).includes(loopId);
                    if (active && !inActive) { start = mi; inActive = true; }
                    if ((!active || mi === snapshots.length - 1) && inActive) {
                        const end = active ? mi + 1 : mi;
                        svg.append("rect")
                            .attr("x", xScale(start))
                            .attr("y", y + 4)
                            .attr("width", Math.max(2, xScale(end) - xScale(start)))
                            .attr("height", rowH - 8)
                            .attr("rx", 3)
                            .attr("fill", meta.color)
                            .attr("fill-opacity", 0.6);
                        inActive = false;
                    }
                });
            });

        }, [snapshots]);

        return html`
            <div>
                <div class="text-sm font-medium text-gray-600 mb-2">Feedback Loop Activity Timeline</div>
                <div ref=${containerRef} class="chart-animate" style=${{width:'100%'}}></div>
            </div>
        `;
    }

    // ── v2 Time-Series: Milestone Cards ───────────────────────────────

    function MilestoneCards({ milestones }) {
        if (!milestones || Object.keys(milestones).length === 0) return null;

        const entries = Object.entries(milestones).sort((a, b) => a[1].month - b[1].month);

        return html`
            <div>
                <div class="text-sm font-medium text-gray-600 mb-3">Key Milestones</div>
                <div class="flex gap-3 overflow-x-auto pb-2">
                    ${entries.map(([key, ms]) => {
                        const adoption = Math.round((ms.adoption?.level || 0) * 100);
                        const freed = Math.round(ms.workforce?.effective_freed_hc || 0);
                        const net = ms.financial?.cumulative_net || 0;
                        const hfm = ms.human_factors?.composite_multiplier || ms.human_factors?.hfm || 0;

                        return html`
                            <div key=${key} class="min-w-[140px] bg-white border border-gray-200 rounded-xl p-3 flex-shrink-0 hover:shadow-md transition-shadow">
                                <div class="text-xs font-semibold text-brand-600 mb-2">Month ${ms.month}</div>
                                <div class="space-y-1.5 text-xs">
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Adoption</span>
                                        <span class="font-semibold text-brand-700">${adoption}%</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Freed HC</span>
                                        <span class="font-semibold text-amber-700">${freed}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">Net Impact</span>
                                        <span class="font-semibold ${net >= 0 ? 'text-green-700' : 'text-red-700'}">${fmt.currency(net)}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span class="text-gray-500">HFM</span>
                                        <span class="font-semibold text-blue-700">${(hfm * 100).toFixed(0)}%</span>
                                    </div>
                                </div>
                            </div>
                        `;
                    })}
                </div>
            </div>
        `;
    }

    // ── Export ─────────────────────────────────────────────────────────

    Object.assign(window.DT, {
        ForceGraph, ReadinessGauge, WaterfallChart, TimelineChart,
        SankeyDiagram, CascadeFlow, HeadcountCompareChart,
        TaskDistributionDonut, RedeploymentFlow, RiskMatrix,
        HierarchyTree, InteractiveGraph, InteractiveGraph3D,
        AdoptionSCurve, HumanFactorsChart, FinancialTrajectory,
        FeedbackLoopTimeline, MilestoneCards,
        GRAPH_EDGES, LEVEL_COLORS, NODE_CATEGORIES, CATEGORY_COLORS,
        NODE_TYPE_LABELS, NODE_TYPE_COLORS, EDGE_COLORS,
    });
})();
