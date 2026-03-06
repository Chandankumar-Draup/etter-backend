/**
 * Main application - React shell with client-side routing.
 *
 * Navigation: Dashboard | Explorer | Graph | Simulator | Scenarios (Results, Compare) | Assistant
 * Responsive hamburger menu for screens below 1024px.
 */

(function () {
    const { html, useState, useCallback, useEffect, useRef,
            Dashboard, Explorer, GraphExplorer, Simulator, Results, Comparison,
            Chat, ErrorBoundary } = window.DT;

    /** Primary nav items shown individually on desktop. */
    const PRIMARY_NAV = [
        { id: "dashboard", label: "Dashboard", icon: "\u{1F4CA}" },
        { id: "explorer",  label: "Explorer",  icon: "\u{1F5C2}" },
        { id: "graph",     label: "Graph",     icon: "\u{1F578}\uFE0F" },
        { id: "simulator", label: "Simulator", icon: "\u{26A1}" },
    ];

    /** Items grouped under the "Scenarios" dropdown on desktop. */
    const SCENARIO_NAV = [
        { id: "results",    label: "Results", icon: "\u{1F4C8}" },
        { id: "comparison", label: "Compare", icon: "\u{1F50D}" },
    ];

    /** Assistant item — always visible on desktop, included in mobile menu. */
    const ASSISTANT_NAV = { id: "chat", label: "Assistant", icon: "\u{1F4AC}" };

    /** Flat list of every navigable item (used by mobile menu & renderView). */
    const ALL_NAV = [...PRIMARY_NAV, ...SCENARIO_NAV, ASSISTANT_NAV];

    /* ------------------------------------------------------------------ */
    /*  Hamburger icon (3-line)                                           */
    /* ------------------------------------------------------------------ */
    function HamburgerIcon() {
        return html`
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
        `;
    }

    /* ------------------------------------------------------------------ */
    /*  Close icon (X)                                                    */
    /* ------------------------------------------------------------------ */
    function CloseIcon() {
        return html`
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
        `;
    }

    /* ------------------------------------------------------------------ */
    /*  Chevron-down icon for Scenarios dropdown                          */
    /* ------------------------------------------------------------------ */
    function ChevronDown({ open }) {
        return html`
            <svg class="w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}"
                 fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
        `;
    }

    /* ------------------------------------------------------------------ */
    /*  Scenarios dropdown (desktop)                                      */
    /* ------------------------------------------------------------------ */
    function ScenariosDropdown({ view, navigate }) {
        const [open, setOpen] = useState(false);
        const ref = useRef(null);

        // Close on outside click
        useEffect(() => {
            const handler = (e) => {
                if (ref.current && !ref.current.contains(e.target)) setOpen(false);
            };
            document.addEventListener("mousedown", handler);
            return () => document.removeEventListener("mousedown", handler);
        }, []);

        const isActive = SCENARIO_NAV.some(s => s.id === view);

        return html`
            <div class="relative" ref=${ref}>
                <button
                    onClick=${() => setOpen(!open)}
                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all duration-150
                        ${isActive
                            ? "bg-brand-50 text-brand-700 font-medium"
                            : "text-gray-500 hover:bg-gray-100 hover:text-gray-900"}">
                    <span>\u{1F3AF}</span>
                    <span>Scenarios</span>
                    <${ChevronDown} open=${open} />
                </button>

                ${open && html`
                    <div class="absolute top-full left-0 mt-1 w-44 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50 fade-in">
                        ${SCENARIO_NAV.map(item => html`
                            <button key=${item.id}
                                onClick=${() => { navigate(item.id); setOpen(false); }}
                                class="w-full flex items-center gap-2 px-3 py-2 text-sm transition-all duration-150
                                    ${view === item.id
                                        ? "bg-brand-50 text-brand-700 font-medium"
                                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"}">
                                <span>${item.icon}</span>
                                <span>${item.label}</span>
                            </button>
                        `)}
                    </div>
                `}
            </div>
        `;
    }

    /* ------------------------------------------------------------------ */
    /*  Mobile menu                                                       */
    /* ------------------------------------------------------------------ */
    function MobileMenu({ view, navigate, open, onClose }) {
        if (!open) return null;

        return html`
            <div class="lg:hidden fixed inset-0 z-50">
                <!-- Backdrop -->
                <div class="absolute inset-0 bg-black/30" onClick=${onClose} />

                <!-- Slide-in panel -->
                <div class="absolute top-0 right-0 w-64 h-full bg-white shadow-xl flex flex-col fade-in">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-4 h-14 border-b border-gray-200">
                        <span class="text-sm font-semibold text-gray-900 font-heading">Menu</span>
                        <button onClick=${onClose}
                            class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-all duration-150">
                            <${CloseIcon} />
                        </button>
                    </div>

                    <!-- Nav items -->
                    <div class="flex-1 overflow-y-auto py-2 sidebar-scroll">
                        <!-- Primary items -->
                        ${PRIMARY_NAV.map(item => html`
                            <button key=${item.id}
                                onClick=${() => { navigate(item.id); onClose(); }}
                                class="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-all duration-150
                                    ${view === item.id
                                        ? "bg-brand-50 text-brand-700 font-medium border-l-2 border-brand-600"
                                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900 border-l-2 border-transparent"}">
                                <span>${item.icon}</span>
                                <span>${item.label}</span>
                            </button>
                        `)}

                        <!-- Scenarios group label -->
                        <div class="px-4 pt-4 pb-1">
                            <span class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Scenarios</span>
                        </div>
                        ${SCENARIO_NAV.map(item => html`
                            <button key=${item.id}
                                onClick=${() => { navigate(item.id); onClose(); }}
                                class="w-full flex items-center gap-3 px-4 pl-6 py-2.5 text-sm transition-all duration-150
                                    ${view === item.id
                                        ? "bg-brand-50 text-brand-700 font-medium border-l-2 border-brand-600"
                                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900 border-l-2 border-transparent"}">
                                <span>${item.icon}</span>
                                <span>${item.label}</span>
                            </button>
                        `)}

                        <!-- Divider -->
                        <div class="my-2 border-t border-gray-100" />

                        <!-- Assistant -->
                        <button
                            onClick=${() => { navigate(ASSISTANT_NAV.id); onClose(); }}
                            class="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-all duration-150
                                ${view === ASSISTANT_NAV.id
                                    ? "bg-ai-50 text-ai-700 font-medium border-l-2 border-ai-600"
                                    : "text-gray-600 hover:bg-ai-50 hover:text-ai-700 border-l-2 border-transparent"}">
                            <span>${ASSISTANT_NAV.icon}</span>
                            <span>${ASSISTANT_NAV.label}</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /* ------------------------------------------------------------------ */
    /*  Main App                                                          */
    /* ------------------------------------------------------------------ */
    function App() {
        const [view, setView] = useState("dashboard");
        const [viewParams, setViewParams] = useState({});
        const [mobileOpen, setMobileOpen] = useState(false);

        const navigate = useCallback((target, params = {}) => {
            setView(target);
            setViewParams(params);
            window.scrollTo(0, 0);
        }, []);

        // Close mobile menu on resize to desktop
        useEffect(() => {
            const onResize = () => { if (window.innerWidth >= 1024) setMobileOpen(false); };
            window.addEventListener("resize", onResize);
            return () => window.removeEventListener("resize", onResize);
        }, []);

        const renderView = () => {
            switch (view) {
                case "dashboard":
                    return html`<${Dashboard} onNavigate=${navigate} />`;
                case "explorer":
                    return html`<${Explorer} onNavigate=${navigate} />`;
                case "graph":
                    return html`<${GraphExplorer} onNavigate=${navigate} />`;
                case "simulator":
                    return html`<${Simulator} onNavigate=${navigate} initialParams=${viewParams} />`;
                case "results":
                    return html`<${Results}
                        onNavigate=${navigate}
                        scenarioId=${viewParams.scenarioId}
                        result=${viewParams.result}
                        config=${viewParams.config}
                    />`;
                case "comparison":
                    return html`<${Comparison}
                        onNavigate=${navigate}
                        addScenarioId=${viewParams.addScenarioId}
                    />`;
                case "chat":
                    return html`<${Chat} onNavigate=${navigate} />`;
                default:
                    return html`<${Dashboard} onNavigate=${navigate} />`;
            }
        };

        return html`
            <div class="min-h-screen bg-gray-50">
                <!-- Top Navigation -->
                <nav class="bg-white border-b border-gray-200 sticky top-0 z-40">
                    <div class="max-w-7xl mx-auto px-4">
                        <div class="flex items-center justify-between h-14">
                            <!-- Brand -->
                            <div class="flex items-center gap-3 shrink-0">
                                <div class="flex items-center gap-2 cursor-pointer"
                                     onClick=${() => navigate("dashboard")}>
                                    <div class="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
                                        <span class="text-white text-sm font-bold">WT</span>
                                    </div>
                                    <div>
                                        <div class="text-sm font-bold text-gray-900 leading-tight font-heading">Workforce Twin</div>
                                        <div class="text-[11px] text-gray-400 leading-tight tracking-wide">by Etter</div>
                                    </div>
                                </div>
                            </div>

                            <!-- Desktop Nav Links (hidden below lg/1024px) -->
                            <div class="hidden lg:flex items-center gap-1">
                                ${PRIMARY_NAV.map(item => html`
                                    <button key=${item.id}
                                        onClick=${() => navigate(item.id)}
                                        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all duration-150
                                            ${view === item.id
                                                ? "bg-brand-50 text-brand-700 font-medium"
                                                : "text-gray-500 hover:bg-gray-100 hover:text-gray-900"}">
                                        <span>${item.icon}</span>
                                        <span>${item.label}</span>
                                    </button>
                                `)}

                                <!-- Scenarios dropdown (Results + Compare) -->
                                <${ScenariosDropdown} view=${view} navigate=${navigate} />

                                <!-- Divider -->
                                <div class="w-px h-5 bg-gray-200 mx-1" />

                                <!-- Assistant — always visible -->
                                <button
                                    onClick=${() => navigate("chat")}
                                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all duration-150
                                        ${view === "chat"
                                            ? "bg-ai-50 text-ai-700 font-medium"
                                            : "text-gray-500 hover:bg-ai-50 hover:text-ai-700"}">
                                    <span>${ASSISTANT_NAV.icon}</span>
                                    <span>${ASSISTANT_NAV.label}</span>
                                </button>
                            </div>

                            <!-- Right side -->
                            <div class="flex items-center gap-2 shrink-0">
                                <span class="text-xs text-gray-400 hidden sm:inline">Acme Corp</span>
                                <div class="w-7 h-7 bg-gray-200 rounded-full flex items-center justify-center text-xs text-gray-500">
                                    A
                                </div>

                                <!-- Hamburger (visible below lg/1024px) -->
                                <button
                                    onClick=${() => setMobileOpen(true)}
                                    class="lg:hidden ml-1 p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-all duration-150">
                                    <${HamburgerIcon} />
                                </button>
                            </div>
                        </div>
                    </div>
                </nav>

                <!-- Mobile slide-out menu -->
                <${MobileMenu}
                    view=${view}
                    navigate=${navigate}
                    open=${mobileOpen}
                    onClose=${() => setMobileOpen(false)}
                />

                <!-- Main Content -->
                <main class="max-w-7xl mx-auto px-4 py-6">
                    ${renderView()}
                </main>

                <!-- Footer -->
                <footer class="border-t border-gray-200 mt-8">
                    <div class="max-w-7xl mx-auto px-4 py-3 text-center text-xs text-gray-400">
                        Workforce Twin \u2022 Etter
                    </div>
                </footer>
            </div>
        `;
    }

    // Mount the application (ErrorBoundary catches render crashes)
    const root = ReactDOM.createRoot(document.getElementById("root"));
    root.render(html`<${ErrorBoundary}><${App} /></${ErrorBoundary}>`);
})();
