/**
 * Graph Explorer View - Full-screen interactive force-directed graph.
 *
 * Shows all nodes and relationships within a selected scope.
 * Click any node to see its properties and relationships in an overlay panel.
 * Collapsible left sidebar with searchable scope, filters, node limit, legend.
 * Compact top bar with breadcrumb, zoom controls, 2D/3D toggle.
 */

(function () {
    const { html, useState, useEffect, useCallback, useMemo, useRef, api, fmt,
            InteractiveGraph, InteractiveGraph3D, MetricCard, Badge, Spinner, ErrorBox,
            SectionHeader, LoadingState, CHART_COLORS,
            NODE_TYPE_LABELS, NODE_CATEGORIES, CATEGORY_COLORS,
            NODE_TYPE_COLORS, EDGE_COLORS } = window.DT;

    // ── Node Detail Panel (Overlay) ──────────────────────────────────

    function NodeDetailPanel({ nodeId, onNavigateToNode, onSimulate, onClose }) {
        const [detail, setDetail] = useState(null);
        const [loading, setLoading] = useState(false);
        const [error, setError] = useState(null);

        useEffect(() => {
            if (!nodeId) { setDetail(null); return; }
            setLoading(true);
            setError(null);
            api.get(`/node/${encodeURIComponent(nodeId)}`)
                .then(d => { setDetail(d); setLoading(false); })
                .catch(e => { setError(e.message); setLoading(false); });
        }, [nodeId]);

        if (loading) return html`<div class="p-4"><${LoadingState} type="rows" count=${5} /></div>`;
        if (error) return html`<div class="p-4"><${ErrorBox} message=${error} /></div>`;
        if (!detail) return null;

        const { node, relationships } = detail;
        const props = node.properties || {};
        const label = NODE_TYPE_LABELS[node.label] || node.label;
        const color = NODE_TYPE_COLORS[node.label] || CATEGORY_COLORS[NODE_CATEGORIES[node.label] || 'taxonomy'] || CHART_COLORS.info;

        const relGroups = {};
        (relationships || []).forEach(r => {
            const key = `${r.direction}:${r.type}`;
            if (!relGroups[key]) relGroups[key] = { direction: r.direction, type: r.type, nodes: [] };
            const related = r.direction === 'outgoing' ? r.target : r.source;
            if (related && related.id) relGroups[key].nodes.push(related);
        });

        const skipProps = new Set(['id', 'name', 'description']);
        const displayProps = Object.entries(props)
            .filter(([k]) => !skipProps.has(k))
            .filter(([, v]) => v != null && v !== '' && !(Array.isArray(v) && v.length === 0));

        const canSimulate = node.label === 'DTFunction' || node.label === 'DTRole';

        return html`
            <div class="fade-in space-y-4 p-4 overflow-y-auto h-full sidebar-scroll">
                <div class="flex items-start justify-between">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                            <div class="w-3 h-3 rounded-full flex-shrink-0" style=${{ backgroundColor: color }}></div>
                            <span class="text-xs font-medium text-gray-500 uppercase">${label}</span>
                        </div>
                        <h3 class="text-lg font-bold text-gray-900 break-words">${node.name}</h3>
                    </div>
                    <button onClick=${onClose}
                        class="ml-2 p-1 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition flex-shrink-0"
                        title="Close panel">
                        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>

                ${props.description && html`
                    <p class="text-xs text-gray-500 leading-relaxed">${props.description}</p>
                `}

                ${(props.total_headcount || props.headcount || props.automation_score != null || props.avg_salary) && html`
                    <div class="grid grid-cols-2 gap-2">
                        ${props.total_headcount && html`<${MetricCard} label="Headcount" value=${fmt.number(props.total_headcount)} color="blue" />`}
                        ${props.headcount && !props.total_headcount && html`<${MetricCard} label="Headcount" value=${fmt.number(props.headcount)} color="blue" />`}
                        ${props.automation_score != null && html`<${MetricCard} label="Automation" value=${Math.round(props.automation_score) + '%'} color="green" />`}
                        ${props.avg_salary && html`<${MetricCard} label="Avg Salary" value=${fmt.currency(props.avg_salary)} color="blue" />`}
                    </div>
                `}

                ${displayProps.length > 0 && html`
                    <div>
                        <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Properties</div>
                        <div class="space-y-1.5">
                            ${displayProps.map(([key, val]) => html`
                                <div key=${key} class="flex items-start justify-between text-xs">
                                    <span class="text-gray-500 mr-2">${key.replace(/_/g, ' ')}</span>
                                    <span class="font-medium text-gray-800 text-right max-w-[60%] truncate">
                                        ${Array.isArray(val) ? val.join(', ') : String(val)}
                                    </span>
                                </div>
                            `)}
                        </div>
                    </div>
                `}

                ${Object.keys(relGroups).length > 0 && html`
                    <div>
                        <div class="text-xs font-semibold text-gray-500 uppercase mb-2">Relationships</div>
                        <div class="space-y-3">
                            ${Object.values(relGroups).map(group => {
                                const relLabel = group.type.replace(/^DT_/, '').replace(/_/g, ' ');
                                const arrow = group.direction === 'outgoing' ? '\u2192' : '\u2190';
                                const edgeColor = EDGE_COLORS[group.type] || '#d1d5db';
                                return html`
                                    <div key="${group.direction}:${group.type}">
                                        <div class="flex items-center gap-1.5 mb-1">
                                            <div class="w-2 h-2 rounded-full" style=${{ backgroundColor: edgeColor }}></div>
                                            <span class="text-xs font-medium text-gray-600">${arrow} ${relLabel}</span>
                                            <span class="text-xs text-gray-400">(${group.nodes.length})</span>
                                        </div>
                                        <div class="flex flex-wrap gap-1">
                                            ${group.nodes.slice(0, 12).map(n => html`
                                                <button key=${n.id}
                                                    onClick=${() => onNavigateToNode && onNavigateToNode(n.id)}
                                                    class="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700 hover:bg-brand-100 hover:text-brand-700 transition truncate max-w-[180px]"
                                                    title=${n.name}>
                                                    ${n.name || n.id}
                                                </button>
                                            `)}
                                            ${group.nodes.length > 12 && html`
                                                <span class="text-xs text-gray-400 px-1">+${group.nodes.length - 12} more</span>
                                            `}
                                        </div>
                                    </div>
                                `;
                            })}
                        </div>
                    </div>
                `}

                ${canSimulate && html`
                    <button onClick=${() => onSimulate && onSimulate(node)}
                        class="w-full px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition flex items-center justify-center gap-2">
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                        Simulate ${label}
                    </button>
                `}
            </div>
        `;
    }

    // ── Minimap ────────────────────────────────────────────────────────

    function Minimap({ nodes, width, height }) {
        if (!nodes || nodes.length === 0) return null;

        // Group nodes by category and show dots
        const dotsByCategory = {};
        nodes.forEach(n => {
            const cat = NODE_CATEGORIES[n.label] || 'taxonomy';
            if (!dotsByCategory[cat]) dotsByCategory[cat] = { color: CATEGORY_COLORS[cat] || '#94a3b8', count: 0 };
            dotsByCategory[cat].count++;
        });

        const cats = Object.entries(dotsByCategory);
        const total = nodes.length;

        return html`
            <div class="p-2 h-full flex flex-col justify-between">
                <div class="text-[9px] font-semibold text-gray-500 uppercase">Minimap</div>
                <div class="flex-1 flex items-center justify-center">
                    <div class="flex gap-1">
                        ${cats.map(([cat, info]) => {
                            const pct = Math.round((info.count / total) * 100);
                            const barH = Math.max(8, Math.round(pct * 0.6));
                            return html`
                                <div key=${cat} class="flex flex-col items-center gap-0.5" title="${cat}: ${info.count} nodes (${pct}%)">
                                    <div class="rounded-sm" style=${{ width: '16px', height: `${barH}px`, backgroundColor: info.color, opacity: 0.8 }}></div>
                                    <div class="text-[8px] text-gray-400">${info.count}</div>
                                </div>
                            `;
                        })}
                    </div>
                </div>
                <div class="text-[9px] text-gray-400 text-center">${total} nodes</div>
            </div>
        `;
    }

    // ── Helpers ────────────────────────────────────────────────────────

    const SCOPE_TYPE_LABELS = {
        function: 'Function', sub_function: 'Sub-Function',
        job_family_group: 'Job Family Group', job_family: 'Job Family', role: 'Role',
    };
    const SCOPE_TYPES = ['function', 'sub_function', 'job_family_group', 'job_family', 'role'];

    // Flatten hierarchy tree into a searchable list for a given scope type
    function flattenHierarchy(tree, scopeType) {
        const results = [];
        if (!tree) return results;

        function walk(node, breadcrumb) {
            const crumb = breadcrumb.length > 0 ? [...breadcrumb, node.name] : [node.name];
            if (node.type === scopeType) {
                results.push({ name: node.name, type: node.type, breadcrumb: crumb.join(' \u203A ') });
            }
            if (node.children) {
                node.children.forEach(c => walk(c, crumb));
            }
        }

        // Organization is the root; walk its children
        if (tree.children) {
            tree.children.forEach(c => walk(c, []));
        }
        return results;
    }

    // ── ScopePanel (Left Sidebar) ─────────────────────────────────────

    function ScopePanel({
        isOpen, onClose, hierarchy,
        scopeType, onScopeTypeChange, scopeSearch, onScopeSearchChange,
        scopeEntity, onScopeEntityChange,
        nodeLimit, onNodeLimitChange,
        nodeTypes, activeFilters, onToggleFilter,
        searchQuery, onSearchChange,
        totalNodes, totalEdges, presentTypes,
    }) {
        const flatEntities = useMemo(() => flattenHierarchy(hierarchy, scopeType), [hierarchy, scopeType]);

        const filteredEntities = useMemo(() => {
            if (!scopeSearch) return flatEntities;
            const q = scopeSearch.toLowerCase();
            return flatEntities.filter(e =>
                e.name.toLowerCase().includes(q) || e.breadcrumb.toLowerCase().includes(q)
            );
        }, [flatEntities, scopeSearch]);

        return html`
            <div class="absolute top-0 left-0 bottom-0 z-20 flex flex-col bg-white border-r border-gray-200 shadow-xl transition-transform duration-200"
                 style=${{ width: '280px', transform: isOpen ? 'translateX(0)' : 'translateX(-100%)' }}>

                <!-- Header -->
                <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                    <h3 class="text-sm font-bold text-gray-900">Scope</h3>
                    <button onClick=${onClose} class="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition" title="Close sidebar">
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>

                <!-- Scope type + search -->
                <div class="px-4 py-3 space-y-2 border-b border-gray-100">
                    <select value=${scopeType} onChange=${e => onScopeTypeChange(e.target.value)}
                        class="w-full border border-gray-300 rounded-lg px-2.5 py-1.5 text-xs font-medium focus:ring-brand-500 focus:border-brand-500 bg-white">
                        ${SCOPE_TYPES.map(st => html`<option key=${st} value=${st}>${SCOPE_TYPE_LABELS[st]}</option>`)}
                    </select>
                    <div class="relative">
                        <input type="text" value=${scopeSearch} onInput=${e => onScopeSearchChange(e.target.value)}
                            placeholder="Search ${SCOPE_TYPE_LABELS[scopeType]}s..."
                            class="w-full border border-gray-300 rounded-lg pl-8 pr-3 py-1.5 text-xs focus:ring-brand-500 focus:border-brand-500 bg-white" />
                        <svg class="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                        </svg>
                    </div>
                </div>

                <!-- Entity list (scrollable) -->
                <div class="flex-1 overflow-y-auto sidebar-scroll">
                    ${filteredEntities.length === 0 && html`
                        <div class="p-4 text-xs text-gray-400 text-center">No matches</div>
                    `}
                    ${filteredEntities.slice(0, 100).map(entity => html`
                        <button key=${entity.name}
                            onClick=${() => onScopeEntityChange(entity)}
                            class="w-full text-left px-4 py-2 border-b border-gray-50 hover:bg-brand-50 transition
                                ${scopeEntity && scopeEntity.name === entity.name && scopeEntity.type === entity.type
                                    ? 'bg-brand-50 border-l-2 border-l-brand-500'
                                    : ''}">
                            <div class="text-xs font-medium text-gray-800 truncate">${entity.name}</div>
                            <div class="text-[10px] text-gray-400 truncate">${entity.breadcrumb}</div>
                        </button>
                    `)}
                    ${filteredEntities.length > 100 && html`
                        <div class="p-3 text-[10px] text-gray-400 text-center">Showing first 100 of ${filteredEntities.length}</div>
                    `}
                </div>

                <!-- Filters + Controls -->
                <div class="border-t border-gray-200 px-4 py-3 space-y-3 max-h-[45%] overflow-y-auto sidebar-scroll">
                    <!-- Node type filters -->
                    <div>
                        <div class="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Node Types</div>
                        <div class="flex flex-wrap gap-1">
                            ${(nodeTypes || []).map(nt => {
                                const color = NODE_TYPE_COLORS[nt] || CATEGORY_COLORS[NODE_CATEGORIES[nt] || 'taxonomy'] || CHART_COLORS.info;
                                const active = activeFilters.includes(nt);
                                const label = NODE_TYPE_LABELS[nt] || nt.replace(/^DT/, '');
                                return html`
                                    <button key=${nt} onClick=${() => onToggleFilter(nt)}
                                        class="flex items-center gap-1 px-2 py-1 rounded-full text-[11px] transition border font-medium
                                            ${active ? 'text-white border-transparent shadow-sm' : 'bg-white text-gray-500 border-gray-200 hover:border-gray-400 hover:shadow-sm'}"
                                        style=${active ? { backgroundColor: color, borderColor: color } : {}}>
                                        <span class="w-2 h-2 rounded-full" style=${{ backgroundColor: active ? '#fff' : color }}></span>
                                        ${label}
                                    </button>
                                `;
                            })}
                        </div>
                    </div>

                    <!-- Node search -->
                    <div class="relative">
                        <input type="text" value=${searchQuery} onInput=${e => onSearchChange(e.target.value)}
                            placeholder="Filter nodes by name..."
                            class="w-full border border-gray-300 rounded-lg pl-8 pr-3 py-1.5 text-xs focus:ring-brand-500 focus:border-brand-500 bg-white" />
                        <svg class="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                        </svg>
                    </div>

                    <!-- Node limit + Stats row -->
                    <div class="flex items-center gap-3">
                        <div class="flex items-center gap-1.5">
                            <span class="text-[10px] text-gray-500 font-medium">Limit:</span>
                            <select value=${nodeLimit} onChange=${e => onNodeLimitChange(Number(e.target.value))}
                                class="border border-gray-300 rounded px-1.5 py-0.5 text-[10px] bg-white">
                                <option value="25">25</option>
                                <option value="50">50</option>
                                <option value="100">100</option>
                                <option value="200">200</option>
                                <option value="300">300</option>
                            </select>
                        </div>
                        <div class="text-[10px] text-gray-400">
                            <span class="font-medium text-gray-600">${totalNodes}</span> nodes
                            <span class="mx-1">|</span>
                            <span class="font-medium text-gray-600">${totalEdges}</span> edges
                        </div>
                    </div>

                    <!-- Legend -->
                    ${presentTypes.length > 0 && html`
                        <div>
                            <div class="text-[10px] font-semibold text-gray-500 uppercase mb-1.5">Legend</div>
                            <div class="grid grid-cols-2 gap-x-2 gap-y-0.5">
                                ${presentTypes.map(nt => html`
                                    <span key=${nt} class="flex items-center gap-1 text-[10px] text-gray-600">
                                        <span class="w-2 h-2 rounded-full flex-shrink-0" style=${{ backgroundColor: NODE_TYPE_COLORS[nt] }}></span>
                                        ${NODE_TYPE_LABELS[nt] || nt.replace(/^DT/, '')}
                                    </span>
                                `)}
                            </div>
                        </div>
                    `}
                </div>
            </div>
        `;
    }

    // ── GraphExplorer (Main) ────────────────────────────────────────

    function GraphExplorer({ onNavigate }) {
        const [graphData, setGraphData] = useState(null);
        const [loading, setLoading] = useState(true);
        const [error, setError] = useState(null);
        const [hierarchy, setHierarchy] = useState(null);

        // Sidebar
        const [sidebarOpen, setSidebarOpen] = useState(true);

        // Scope selection
        const [scopeType, setScopeType] = useState("function");
        const [scopeSearch, setScopeSearch] = useState("");
        const [scopeEntity, setScopeEntity] = useState(null);

        // Graph controls
        const [nodeLimit, setNodeLimit] = useState(100);
        const [selectedNodeId, setSelectedNodeId] = useState(null);
        const [activeFilters, setActiveFilters] = useState([]);
        const [searchQuery, setSearchQuery] = useState("");
        const [view3D, setView3D] = useState(false);

        const graphContainerRef = useRef(null);
        const zoomControlsRef = useRef(null);
        const [graphSize, setGraphSize] = useState({ width: 1200, height: 700 });

        // Measure container
        useEffect(() => {
            const measure = () => {
                if (graphContainerRef.current) {
                    const rect = graphContainerRef.current.getBoundingClientRect();
                    setGraphSize({
                        width: Math.max(600, Math.floor(rect.width)),
                        height: Math.max(400, Math.floor(rect.height)),
                    });
                }
            };
            measure();
            window.addEventListener('resize', measure);
            return () => window.removeEventListener('resize', measure);
        }, [loading]);

        // Load hierarchy tree once
        useEffect(() => {
            api.get("/hierarchy").then(data => {
                const tree = data.hierarchy || data;
                setHierarchy(tree);
                // Auto-select first function
                if (tree.children && tree.children.length > 0) {
                    const first = tree.children[0];
                    setScopeEntity({ name: first.name, type: 'function', breadcrumb: first.name });
                }
            }).catch(() => {});
        }, []);

        // Derive effective scope
        const effectiveScope = useMemo(() => {
            if (!scopeEntity) return null;
            return { type: scopeEntity.type, name: scopeEntity.name };
        }, [scopeEntity]);

        // Load graph data
        useEffect(() => {
            if (!effectiveScope) return;
            setLoading(true);
            setError(null);
            setSelectedNodeId(null);
            const url = `/graph?scope_type=${encodeURIComponent(effectiveScope.type)}&scope_name=${encodeURIComponent(effectiveScope.name)}&limit=${nodeLimit}`;
            api.get(url)
                .then(d => {
                    setGraphData(d);
                    if (d.node_types) setActiveFilters(d.node_types);
                    setLoading(false);
                })
                .catch(e => { setError(e.message); setLoading(false); });
        }, [effectiveScope && effectiveScope.type, effectiveScope && effectiveScope.name, nodeLimit]);

        // When scope type changes, clear search and reset entity to first match
        const handleScopeTypeChange = useCallback((newType) => {
            setScopeType(newType);
            setScopeSearch("");
            // Auto-select first entity of this type
            if (hierarchy) {
                const entities = flattenHierarchy(hierarchy, newType);
                if (entities.length > 0) {
                    setScopeEntity(entities[0]);
                }
            }
        }, [hierarchy]);

        const handleScopeEntityChange = useCallback((entity) => {
            setScopeEntity(entity);
            setActiveFilters([]);
        }, []);

        // Zoom handlers
        const handleZoomControlsReady = useCallback((controls) => {
            zoomControlsRef.current = controls;
        }, []);
        const handleZoomIn = useCallback(() => { zoomControlsRef.current && zoomControlsRef.current.zoomIn(); }, []);
        const handleZoomOut = useCallback(() => { zoomControlsRef.current && zoomControlsRef.current.zoomOut(); }, []);
        const handleFitAll = useCallback(() => { zoomControlsRef.current && zoomControlsRef.current.fitAll(); }, []);

        const handleNodeClick = useCallback((nodeData) => {
            setSelectedNodeId(nodeData && nodeData.id ? nodeData.id : null);
        }, []);
        const handleNavigateToNode = useCallback((nodeId) => { setSelectedNodeId(nodeId); }, []);
        const handleClosePanel = useCallback(() => { setSelectedNodeId(null); }, []);

        const handleSimulate = useCallback((node) => {
            if (node.label === 'DTFunction') onNavigate("simulator", { scopeName: node.name, scopeType: "function" });
            else if (node.label === 'DTRole') onNavigate("simulator", { scopeName: node.name, scopeType: "role" });
        }, [onNavigate]);

        const handleToggleFilter = useCallback((nodeType) => {
            setActiveFilters(prev => prev.includes(nodeType) ? prev.filter(t => t !== nodeType) : [...prev, nodeType]);
        }, []);

        // Filter nodes by search query
        const filteredData = useMemo(() => {
            if (!graphData) return null;
            if (!searchQuery) return graphData;
            const q = searchQuery.toLowerCase();
            const matchingIds = new Set();
            graphData.nodes.forEach(n => {
                if ((n.name || '').toLowerCase().includes(q) || (n.label || '').toLowerCase().includes(q)) matchingIds.add(n.id);
            });
            graphData.edges.forEach(e => {
                if (matchingIds.has(e.source)) matchingIds.add(e.target);
                if (matchingIds.has(e.target)) matchingIds.add(e.source);
            });
            return {
                ...graphData,
                nodes: graphData.nodes.filter(n => matchingIds.has(n.id)),
                edges: graphData.edges.filter(e => matchingIds.has(e.source) && matchingIds.has(e.target)),
            };
        }, [graphData, searchQuery]);

        const visibleNodes = filteredData?.nodes || [];
        const visibleEdges = filteredData?.edges || [];

        const presentTypes = useMemo(() => {
            if (!graphData) return [];
            return (graphData.node_types || []).filter(nt => NODE_TYPE_COLORS[nt]);
        }, [graphData]);

        // Breadcrumb text for top bar
        const breadcrumb = scopeEntity ? scopeEntity.breadcrumb : 'Select a scope';

        if (error) {
            return html`
                <div class="fade-in p-6">
                    <h1 class="text-2xl font-bold text-gray-900 mb-4">Graph Explorer</h1>
                    <${ErrorBox} message=${error} />
                </div>
            `;
        }

        if (loading && !graphData) {
            return html`
                <div class="fade-in flex flex-col items-center justify-center" style=${{ height: 'calc(100vh - 120px)' }}>
                    <${Spinner} text="Loading graph data..." />
                </div>
            `;
        }

        return html`
            <div class="fade-in relative" style=${{ height: 'calc(100vh - 120px)', minHeight: '500px' }}>

                <!-- Graph Canvas -->
                <div ref=${graphContainerRef}
                     class="absolute inset-0 bg-white rounded-xl border border-gray-200 overflow-hidden">
                    ${view3D ? html`
                        <${InteractiveGraph3D}
                            nodes=${visibleNodes} edges=${visibleEdges}
                            selectedNodeId=${selectedNodeId} onNodeClick=${handleNodeClick}
                            width=${graphSize.width} height=${graphSize.height}
                            filters=${activeFilters} onZoomControlsReady=${handleZoomControlsReady} />
                    ` : html`
                        <${InteractiveGraph}
                            nodes=${visibleNodes} edges=${visibleEdges}
                            selectedNodeId=${selectedNodeId} onNodeClick=${handleNodeClick}
                            width=${graphSize.width} height=${graphSize.height}
                            filters=${activeFilters} onZoomControlsReady=${handleZoomControlsReady} />
                    `}
                </div>

                <!-- Left Sidebar -->
                <${ScopePanel}
                    isOpen=${sidebarOpen} onClose=${() => setSidebarOpen(false)}
                    hierarchy=${hierarchy}
                    scopeType=${scopeType} onScopeTypeChange=${handleScopeTypeChange}
                    scopeSearch=${scopeSearch} onScopeSearchChange=${setScopeSearch}
                    scopeEntity=${scopeEntity} onScopeEntityChange=${handleScopeEntityChange}
                    nodeLimit=${nodeLimit} onNodeLimitChange=${setNodeLimit}
                    nodeTypes=${graphData?.node_types || []}
                    activeFilters=${activeFilters} onToggleFilter=${handleToggleFilter}
                    searchQuery=${searchQuery} onSearchChange=${setSearchQuery}
                    totalNodes=${visibleNodes.length} totalEdges=${visibleEdges.length}
                    presentTypes=${presentTypes} />

                <!-- Compact Top Bar -->
                <div class="absolute top-3 z-10 right-3 flex items-center gap-2 pointer-events-none"
                     style=${{ left: sidebarOpen ? '296px' : '12px', transition: 'left 0.2s ease' }}>

                    <!-- Sidebar toggle (only when closed) -->
                    ${!sidebarOpen && html`
                        <button onClick=${() => setSidebarOpen(true)}
                            class="pointer-events-auto bg-white/95 backdrop-blur-sm border border-gray-200 shadow-lg rounded-lg p-2 hover:bg-gray-50 transition"
                            title="Open sidebar">
                            <svg class="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                            </svg>
                        </button>
                    `}

                    <!-- Breadcrumb -->
                    <div class="pointer-events-auto flex-1 bg-white/95 backdrop-blur-sm border border-gray-200 shadow-lg rounded-lg px-3 py-2 min-w-0">
                        <div class="text-xs text-gray-600 truncate font-medium">${breadcrumb}</div>
                    </div>

                    <!-- Zoom Controls -->
                    <div class="pointer-events-auto flex bg-white/95 backdrop-blur-sm border border-gray-200 shadow-lg rounded-lg overflow-hidden">
                        <button onClick=${handleZoomOut} class="px-2.5 py-2 hover:bg-gray-100 transition border-r border-gray-200" title="Zoom out">
                            <svg class="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
                            </svg>
                        </button>
                        <button onClick=${handleFitAll} class="px-2.5 py-2 hover:bg-gray-100 transition border-r border-gray-200" title="Fit to view">
                            <svg class="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
                            </svg>
                        </button>
                        <button onClick=${handleZoomIn} class="px-2.5 py-2 hover:bg-gray-100 transition" title="Zoom in">
                            <svg class="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                            </svg>
                        </button>
                    </div>

                    <!-- 2D/3D Toggle -->
                    <div class="pointer-events-auto flex bg-white/95 backdrop-blur-sm border border-gray-200 shadow-lg rounded-lg overflow-hidden relative">
                        <div class="absolute inset-y-0 w-1/2 bg-brand-600 rounded-md transition-transform duration-300 ease-in-out"
                             style=${{ transform: view3D ? 'translateX(100%)' : 'translateX(0)' }}></div>
                        <button onClick=${() => setView3D(false)}
                            class="relative z-10 px-3 py-2 text-xs font-medium transition-colors duration-200
                                ${!view3D ? 'text-white' : 'text-gray-600 hover:text-gray-900'}">
                            2D
                        </button>
                        <button onClick=${() => setView3D(true)}
                            class="relative z-10 px-3 py-2 text-xs font-medium transition-colors duration-200
                                ${view3D ? 'text-white' : 'text-gray-600 hover:text-gray-900'}">
                            3D
                        </button>
                    </div>
                </div>

                <!-- Minimap (bottom-left, only in 2D mode) -->
                ${!view3D && !loading && visibleNodes.length > 0 && html`
                    <div class="absolute z-10 bg-white/95 backdrop-blur-sm border border-gray-200 shadow-lg rounded-lg overflow-hidden pointer-events-auto"
                         style=${{ bottom: '12px', left: sidebarOpen ? '296px' : '12px', width: '140px', height: '100px', transition: 'left 0.2s ease' }}>
                        <${Minimap} nodes=${visibleNodes} width=${140} height=${100} />
                    </div>
                `}

                <!-- Loading overlay -->
                ${loading && graphData && html`
                    <div class="absolute inset-0 bg-white/60 flex items-center justify-center z-10 rounded-xl">
                        <${Spinner} text="Loading..." />
                    </div>
                `}

                <!-- Node Detail Panel (right) -->
                ${selectedNodeId && html`
                    <div class="absolute top-0 right-0 bottom-0 w-96 z-20
                                bg-white border-l border-gray-200 shadow-2xl overflow-hidden fade-in"
                         style=${{ maxWidth: '90vw' }}>
                        <${NodeDetailPanel}
                            nodeId=${selectedNodeId}
                            onNavigateToNode=${handleNavigateToNode}
                            onSimulate=${handleSimulate}
                            onClose=${handleClosePanel} />
                    </div>
                `}
            </div>
        `;
    }

    window.DT.GraphExplorer = GraphExplorer;
})();
