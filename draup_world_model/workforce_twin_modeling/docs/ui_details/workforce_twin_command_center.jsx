import { useState, useEffect, useMemo } from "react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  ComposedChart, Area, Line,
} from "recharts";
import {
  Users, Zap, TrendingUp, Target, AlertTriangle, Shield, Brain,
  DollarSign, Layers, Cpu, Sparkles, Activity, Menu, Sun, Moon,
  ChevronRight, BarChart3, Eye, GitBranch, MessageCircle
} from "lucide-react";

/* ═══════════════════════════════════════════════════════════════════════════
   THEME SYSTEM — Full dark/light via `t` prop propagation
   ═══════════════════════════════════════════════════════════════════════════ */
const THEMES = {
  dark: {
    bg: "#0b1120", card: "#131b2e", border: "#1e2d42", surface: "#1a2332",
    text: "#f1f5f9", muted: "#7c8ba1",
    primary: "#07c8d4", accent: "#8b5cf6", success: "#10b981",
    warning: "#f59e0b", destructive: "#ef4444", pink: "#ec4899",
  },
  light: {
    bg: "#f5f7fa", card: "#ffffff", border: "#e2e8f0", surface: "#f1f5f9",
    text: "#0f172a", muted: "#64748b",
    primary: "#0891b2", accent: "#7c3aed", success: "#059669",
    warning: "#d97706", destructive: "#dc2626", pink: "#db2777",
  },
};

// Fixed semantic colors — consistent across themes
const S = {
  realized: "#10b981", achievable: "#07c8d4", ceiling: "#8b5cf6",
  humanGray: "#5c6b7f",
  fnClaims: "#07c8d4", fnTech: "#8b5cf6", fnFin: "#f59e0b", fnPpl: "#10b981",
};

/* ═══════════════════════════════════════════════════════════════════════════
   REAL DATA — All numbers from the simulation engine
   ═══════════════════════════════════════════════════════════════════════════ */
const THREE_LAYER = { l1: 56.43, l2: 51.31, l3: 9.52, adoptGap: 41.79, capGap: 5.13 };

const FUNCTIONS = [
  { name: "Claims", color: S.fnClaims, hc: 540, gap: 14966916, risk: 51 },
  { name: "Technology", color: S.fnTech, hc: 405, gap: 11382597, risk: 33 },
  { name: "Finance", color: S.fnFin, hc: 239, gap: 6023606, risk: 47 },
  { name: "People", color: S.fnPpl, hc: 186, gap: 4214968, risk: 39 },
];

const HUMAN_SYS = [
  { fn: "Claims", color: S.fnClaims, prof: 25, ready: 45, trust: 35, mult: 0.34 },
  { fn: "Technology", color: S.fnTech, prof: 60, ready: 70, trust: 65, mult: 0.65 },
  { fn: "Finance", color: S.fnFin, prof: 30, ready: 50, trust: 40, mult: 0.39 },
  { fn: "People", color: S.fnPpl, prof: 20, ready: 55, trust: 45, mult: 0.37 },
];

const TOP_OPPS = [
  { role: "Claims Intake Specialist", fn: "Claims", savings: 3430440, fte: 71.5 },
  { role: "Sr Software Engineer", fn: "Technology", savings: 2534726, fte: 22.0 },
  { role: "Claims Adjuster", fn: "Claims", savings: 2453464, fte: 44.6 },
  { role: "Software Engineer", fn: "Technology", savings: 2331855, fte: 25.3 },
  { role: "Claims Data Entry Clerk", fn: "Claims", savings: 1606241, fte: 42.3 },
  { role: "IT Support Specialist", fn: "Technology", savings: 1500798, fte: 30.1 },
];

const CAT_DATA = [
  { cat: "Directive", realized: 10, opp: 80 },
  { cat: "Feedback Loop", realized: 9, opp: 76 },
  { cat: "Task Iteration", realized: 8, opp: 42 },
  { cat: "Validation", realized: 9, opp: 36 },
  { cat: "Learning", realized: 7, opp: 33 },
  { cat: "Negligibility", realized: 2, opp: 3 },
];

/* ─── Trajectory data from stage4_scenario_overlay.csv (P2 Balanced) ───
   current = baseline workload capacity (flat at ~95, slight natural decay)
   augmented = AI-assisted projection (starts low ~10, S-curve climbing to meet current)
   savings  = cumulative monthly savings as green bars growing over time
   Real source: adoption%, net_$, headcount, productivity from P2 columns  */
const TRAJECTORY = [
  { month: "Jan",  current: 95, augmented: 12, savings: 5  },
  { month: "Feb",  current: 94, augmented: 15, savings: 8  },
  { month: "Mar",  current: 95, augmented: 25, savings: 14 },
  { month: "Apr",  current: 93, augmented: 28, savings: 16 },
  { month: "May",  current: 94, augmented: 32, savings: 22 },
  { month: "Jun",  current: 96, augmented: 42, savings: 32 },
  { month: "Jul",  current: 94, augmented: 44, savings: 38 },
  { month: "Aug",  current: 93, augmented: 47, savings: 42 },
  { month: "Sep",  current: 95, augmented: 50, savings: 46 },
];

const RADAR = [
  { axis: "Claims", current: 34, target: 70 },
  { axis: "Technology", current: 65, target: 70 },
  { axis: "Finance", current: 39, target: 70 },
  { axis: "People", current: 37, target: 70 },
  { axis: "Proficiency", current: 34, target: 60 },
  { axis: "Trust", current: 46, target: 65 },
];

const RISK = [
  { name: "Low Risk", value: 18, color: "#10b981" },
  { name: "Medium", value: 15, color: "#f59e0b" },
  { name: "High Risk", value: 12, color: "#ef4444" },
  { name: "Critical", value: 5, color: "#ec4899" },
];

/* ═══════════════════════════════════════════════════════════════════════════
   KPI CARD — UPPERCASE label → monospace number → colored delta → icon
   ═══════════════════════════════════════════════════════════════════════════ */
function KPICard({ label, value, delta, deltaColor, icon: Icon, delay = 0, t }) {
  const [vis, setVis] = useState(false);
  useEffect(() => { const id = setTimeout(() => setVis(true), delay); return () => clearTimeout(id); }, [delay]);
  return (
    <div style={{
      background: t.card, border: `1px solid ${t.border}`, borderRadius: "0.75rem",
      padding: "20px 20px 16px", position: "relative", overflow: "hidden",
      opacity: vis ? 1 : 0, transform: vis ? "translateY(0)" : "translateY(10px)",
      transition: "all 0.35s ease",
    }}>
      <div style={{
        position: "absolute", top: 14, right: 14, background: t.surface,
        borderRadius: "0.5rem", width: 36, height: 36,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}><Icon size={17} color={t.muted} /></div>
      <div style={{ fontSize: 11, fontWeight: 500, letterSpacing: "0.06em", textTransform: "uppercase", color: t.muted, marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 700, color: t.text, fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.1, marginBottom: 6 }}>{value}</div>
      <div style={{ fontSize: 12, color: deltaColor || t.primary }}>{delta}</div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   CHART CARD — Standard wrapper: title + subtitle + icon + children
   ═══════════════════════════════════════════════════════════════════════════ */
function ChartCard({ title, subtitle, icon: Icon, children, t, style = {}, glowBorder = false }) {
  return (
    <div style={{
      background: t.card, borderRadius: "0.75rem", padding: 20,
      position: "relative",
      // Prototype: featured charts get a subtle cyan glow border
      border: glowBorder ? `1px solid ${t.primary}44` : `1px solid ${t.border}`,
      boxShadow: glowBorder ? `0 0 20px -8px ${t.primary}30` : "none",
      ...style,
    }}>
      {Icon && <div style={{
        position: "absolute", top: 16, right: 16, background: t.surface,
        borderRadius: "0.5rem", width: 32, height: 32,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}><Icon size={15} color={t.muted} /></div>}
      <div style={{ fontSize: 15, fontWeight: 700, color: t.text, marginBottom: 3 }}>{title}</div>
      <div style={{ fontSize: 12, color: t.muted, marginBottom: 16 }}>{subtitle}</div>
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   WORKLOAD TRAJECTORY — Animated area+bar composite chart
   Matches prototype Image 2 exactly:
   • Cyan solid area at top = current baseline workload capacity
   • Purple dashed line rising = AI-augmented projection (S-curve)
   • Green bars growing = cumulative savings increasing over time
   • The area between cyan line and purple line = the "gap" narrowing
   Real data: stage4_scenario_overlay.csv → P2 Balanced scenario
   ═══════════════════════════════════════════════════════════════════════════ */
function WorkloadTrajectory({ t }) {
  // Animate: reveal data points one by one for draw effect
  const [visibleCount, setVisibleCount] = useState(0);
  useEffect(() => {
    if (visibleCount < TRAJECTORY.length) {
      const id = setTimeout(() => setVisibleCount(v => v + 1), 120);
      return () => clearTimeout(id);
    }
  }, [visibleCount]);

  const animData = useMemo(
    () => TRAJECTORY.slice(0, visibleCount),
    [visibleCount]
  );

  // Custom gradient definitions for the area fills
  const chartId = "traj-grad";

  return (
    <div style={{ position: "relative" }}>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={animData} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
          <defs>
            {/* Cyan area gradient (current baseline) — solid at top */}
            <linearGradient id={`${chartId}-current`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={S.achievable} stopOpacity={0.35} />
              <stop offset="100%" stopColor={S.achievable} stopOpacity={0.05} />
            </linearGradient>
            {/* Purple area gradient (augmented projection) — fills from bottom */}
            <linearGradient id={`${chartId}-augmented`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={S.ceiling} stopOpacity={0.4} />
              <stop offset="100%" stopColor={S.ceiling} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={t.border} vertical={false} />
          <XAxis
            dataKey="month"
            tick={{ fill: t.muted, fontSize: 11 }}
            axisLine={{ stroke: t.border }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: t.muted, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => v}
          />

          {/* Layer 1: Cyan area — current baseline (flat ~95) */}
          <Area
            type="monotone" dataKey="current" name="Current Baseline"
            stroke={S.achievable} strokeWidth={2.5}
            fill={`url(#${chartId}-current)`}
            dot={false}
            isAnimationActive={false}
          />

          {/* Layer 2: Purple area — AI-augmented projection (S-curve rising) */}
          <Area
            type="monotone" dataKey="augmented" name="AI-Augmented"
            stroke={S.ceiling} strokeWidth={2.5}
            strokeDasharray="8 4"
            fill={`url(#${chartId}-augmented)`}
            dot={false}
            isAnimationActive={false}
          />

          {/* Layer 3: Green bars — cumulative savings (growing) */}
          <Bar
            dataKey="savings" name="Savings Index"
            fill={S.realized}
            radius={[4, 4, 0, 0]}
            barSize={28}
            isAnimationActive={false}
            opacity={0.85}
          />

          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div style={{
                  background: "#131b2e", border: "1px solid #1e2d42",
                  borderRadius: 8, padding: "12px 16px", fontSize: 12,
                  boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
                }}>
                  <div style={{ color: "#f1f5f9", fontWeight: 600, marginBottom: 6 }}>{label}</div>
                  {payload.map((p, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 3 }}>
                      <div style={{ width: 8, height: 8, borderRadius: 2, background: p.color }} />
                      <span style={{ color: "#7c8ba1" }}>{p.name}:</span>
                      <span style={{ color: "#f1f5f9", fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}>{p.value}</span>
                    </div>
                  ))}
                </div>
              );
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            formatter={v => <span style={{ color: t.muted }}>{v}</span>}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Three-layer annotation strip below the chart */}
      <div style={{
        display: "flex", gap: 0, marginTop: 4, fontSize: 10, fontWeight: 500,
        fontFamily: "'JetBrains Mono', monospace",
      }}>
        {[
          { w: 17, c: S.realized, l: `Realized ${THREE_LAYER.l3}%`, s: "solid", money: "$8.7M" },
          { w: 40, c: S.achievable, l: `Adoption Gap ${THREE_LAYER.adoptGap}%`, s: "dashed", money: "$36.6M" },
          { w: 10, c: S.ceiling, l: `Cap. Gap`, s: "dashed", money: "$4.9M" },
          { w: 33, c: S.humanGray, l: `Human Essential`, s: "solid", money: "" },
        ].map((seg, i) => (
          <div key={i} style={{
            width: `${seg.w}%`, textAlign: "center",
            borderTop: `2px ${seg.s} ${seg.c}`, paddingTop: 6,
          }}>
            <div style={{ color: seg.c, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{seg.l}</div>
            {seg.money && <div style={{ color: seg.c, fontSize: 11, fontWeight: 700, marginTop: 1 }}>{seg.money}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   TOOLTIP — Consistent across all other Recharts
   ═══════════════════════════════════════════════════════════════════════════ */
function Tip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#131b2e", border: "1px solid #1e2d42", borderRadius: 8,
      padding: "10px 14px", fontSize: 12, boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
    }}>
      {label && <div style={{ color: "#f1f5f9", fontWeight: 600, marginBottom: 4 }}>{label}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || "#7c8ba1", marginTop: 2 }}>
          {p.name}: <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: "#f1f5f9" }}>
            {typeof p.value === "number" ? p.value.toFixed(1) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   MAIN — Command Center
   ═══════════════════════════════════════════════════════════════════════════ */
export default function App() {
  const [dark, setDark] = useState(true);
  const [sidebarOpen, setSidebar] = useState(true);
  const [page, setPage] = useState("Command Center");
  const t = dark ? THEMES.dark : THEMES.light;
  const maxGap = Math.max(...FUNCTIONS.map(f => f.gap));
  const maxSav = Math.max(...TOP_OPPS.map(o => o.savings));

  const nav = [
    { label: "Command Center", icon: BarChart3 },
    { label: "Current State", icon: Eye },
    { label: "Graph View", icon: GitBranch },
    { label: "Workflows", icon: Activity },
    { label: "Simulation", icon: Zap },
    { label: "Compare", icon: Target },
    { label: "Twin AI", icon: MessageCircle },
  ];

  return (
    <div style={{
      display: "flex", height: "100vh", background: t.bg, color: t.text,
      fontFamily: "Inter, system-ui, sans-serif", overflow: "hidden",
    }}>
      {/* ── TOP GLOW BAR ── */}
      <div style={{
        position: "fixed", top: 0, left: 0, right: 0, height: 2, zIndex: 100,
        background: "linear-gradient(90deg, transparent 5%, #f59e0b 25%, #07c8d4 50%, #8b5cf6 75%, transparent 95%)",
        opacity: 0.7,
      }} />

      {/* ── SIDEBAR ── */}
      <div style={{
        width: sidebarOpen ? 220 : 58, flexShrink: 0, background: t.card,
        borderRight: `1px solid ${t.border}`, display: "flex", flexDirection: "column",
        transition: "width 0.2s ease", zIndex: 50, overflow: "hidden",
      }}>
        <div style={{ padding: sidebarOpen ? "18px 14px" : "18px 13px", display: "flex", alignItems: "center", gap: 10, borderBottom: `1px solid ${t.border}` }}>
          <div style={{
            width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
            background: `linear-gradient(135deg, ${S.achievable}, ${S.ceiling})`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, fontWeight: 700, color: "#fff",
          }}>W</div>
          {sidebarOpen && <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: t.text, whiteSpace: "nowrap" }}>Workforce Twin</div>
            <div style={{ fontSize: 9, fontWeight: 600, color: t.muted, letterSpacing: "0.12em", textTransform: "uppercase" }}>BY ETTER</div>
          </div>}
        </div>
        <div style={{ padding: "10px 6px", flex: 1 }}>
          {nav.map(n => {
            const on = n.label === page;
            return (
              <div key={n.label} onClick={() => setPage(n.label)} style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: sidebarOpen ? "9px 12px" : "9px 0",
                justifyContent: sidebarOpen ? "flex-start" : "center",
                borderRadius: "0.5rem", cursor: "pointer", marginBottom: 2,
                background: on ? `${t.primary}20` : "transparent",
                color: on ? t.text : t.muted, fontSize: 13, fontWeight: on ? 600 : 400,
              }}>
                <n.icon size={18} color={on ? t.primary : t.muted} />
                {sidebarOpen && <span style={{ whiteSpace: "nowrap" }}>{n.label}</span>}
              </div>
            );
          })}
        </div>
        <div onClick={() => setSidebar(!sidebarOpen)} style={{
          padding: 14, borderTop: `1px solid ${t.border}`, cursor: "pointer",
          fontSize: 12, color: t.muted, display: "flex", alignItems: "center",
          justifyContent: sidebarOpen ? "flex-start" : "center", gap: 6,
        }}>
          <ChevronRight size={14} style={{ transform: sidebarOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
          {sidebarOpen && "Collapse"}
        </div>
      </div>

      {/* ── MAIN ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Header */}
        <div style={{
          height: 54, display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 24px", borderBottom: `1px solid ${t.border}`, flexShrink: 0, background: t.card,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Menu size={20} color={t.muted} style={{ cursor: "pointer" }} onClick={() => setSidebar(!sidebarOpen)} />
            <span style={{ fontSize: 15, fontWeight: 700, color: t.text }}>{page}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div onClick={() => setDark(!dark)} style={{
              cursor: "pointer", padding: 6, borderRadius: 6, background: t.surface,
              display: "flex", alignItems: "center",
            }}>
              {dark ? <Sun size={16} color={t.muted} /> : <Moon size={16} color={t.muted} />}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 600, color: S.realized }}>
              <span className="pulseDot" style={{ width: 8, height: 8, borderRadius: "50%", background: S.realized, display: "inline-block" }} />
              LIVE
            </div>
          </div>
        </div>

        {/* ── SCROLLABLE CONTENT ── */}
        <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
          <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: t.text }}>
            Organization <span style={{ color: t.primary }}>Digital Twin</span>
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 22, marginTop: 4 }}>
            <span style={{ fontSize: 12, color: t.muted }}>Real-time workforce intelligence — 1,370 employees across 4 functions</span>
            <span style={{
              fontSize: 10, padding: "2px 10px", borderRadius: 9999,
              background: `${S.realized}18`, color: S.realized, fontWeight: 600,
              display: "inline-flex", alignItems: "center", gap: 4,
            }}><span style={{ width: 5, height: 5, borderRadius: "50%", background: S.realized, display: "inline-block" }} /> Live Sync</span>
          </div>

          {/* ═══ KPI GRID (4×2) ═══ */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 22 }}>
            <KPICard t={t} label="Total Headcount" value="1,370" delta="37 roles • 4 functions" deltaColor={t.primary} icon={Users} delay={0} />
            <KPICard t={t} label="Annual Cost" value="$91.1M" delta="$66.5K avg / employee" deltaColor={t.muted} icon={DollarSign} delay={60} />
            <KPICard t={t} label="Realized Automation" value="9.5%" delta="Ceiling: 56.4% — massive gap" deltaColor={t.primary} icon={Zap} delay={120} />
            <KPICard t={t} label="Unrealized Value" value="$41.5M" delta="572.7 FTE equivalent ↑" deltaColor={S.realized} icon={TrendingUp} delay={180} />
            <KPICard t={t} label={'Adoption Gap "Free Money"'} value="$36.6M" delta="41.8% achievable but unused" deltaColor={t.warning} icon={Target} delay={240} />
            <KPICard t={t} label="At-Risk Roles" value="37" delta="100% redesign candidates" deltaColor={t.warning} icon={AlertTriangle} delay={300} />
            <KPICard t={t} label="Compliance Tasks" value="87" delta="15% of 581 — cannot automate" deltaColor={t.muted} icon={Shield} delay={360} />
            <KPICard t={t} label="Skill Inventory" value="692" delta="152 sunrise skills emerging ↑" deltaColor={S.realized} icon={Brain} delay={420} />
          </div>

          {/* ═══ SECTION B: WORKLOAD TRAJECTORY + CAPABILITY RADAR (2-col like prototype) ═══ */}
          <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 14, marginBottom: 22 }}>
            {/* Animated Workload Trajectory — replaces static Three-Layer bars */}
            <ChartCard t={t} title="Workload Trajectory"
              subtitle="Current vs AI-augmented projection with savings"
              icon={Activity} glowBorder={true}>
              <WorkloadTrajectory t={t} />
            </ChartCard>

            {/* Capability Radar — same position as prototype */}
            <ChartCard t={t} title="Capability Radar" subtitle="Current vs target skills" icon={Target}>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={RADAR}>
                  <PolarGrid stroke={t.border} />
                  <PolarAngleAxis dataKey="axis" tick={{ fill: t.muted, fontSize: 11 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Current" dataKey="current" stroke={t.primary} fill={t.primary} fillOpacity={0.15} strokeWidth={2} />
                  <Radar name="Target" dataKey="target" stroke={t.accent} fill="none" strokeWidth={2} strokeDasharray="6 3" />
                  <Tooltip content={<Tip />} />
                  <Legend wrapperStyle={{ fontSize: 11 }} formatter={v => <span style={{ color: t.muted }}>{v}</span>} />
                </RadarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          {/* ═══ SECTIONS C-H: 2-Column Grid ═══ */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 22 }}>

            {/* C: Function Overview */}
            <ChartCard t={t} title="Function Overview" subtitle="Fractal breakdown — adoption gap by function" icon={Layers}>
              {FUNCTIONS.map(f => {
                const rc = f.risk > 50 ? t.destructive : f.risk > 40 ? t.warning : S.realized;
                return (
                  <div key={f.name} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 0", borderBottom: `1px solid ${t.border}22` }}>
                    <div style={{ width: 10, height: 10, borderRadius: "50%", background: f.color, flexShrink: 0 }} />
                    <div style={{ width: 85, fontSize: 13, color: t.text, fontWeight: 500 }}>{f.name}</div>
                    <div style={{ width: 40, fontSize: 12, color: t.muted, fontFamily: "'JetBrains Mono', monospace", textAlign: "right" }}>{f.hc}</div>
                    <div style={{ flex: 1, height: 7, background: t.surface, borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ width: `${(f.gap / maxGap) * 100}%`, height: "100%", background: f.color, borderRadius: 4, transition: "width 0.8s" }} />
                    </div>
                    <div style={{ width: 70, fontSize: 13, color: t.primary, fontFamily: "'JetBrains Mono', monospace", textAlign: "right", fontWeight: 600 }}>
                      ${(f.gap / 1e6).toFixed(1)}M
                    </div>
                    <div style={{
                      fontSize: 11, padding: "2px 7px", borderRadius: 9999,
                      border: `1px solid ${rc}44`, color: rc, fontWeight: 600,
                      fontFamily: "'JetBrains Mono', monospace",
                    }}>R:{f.risk}</div>
                  </div>
                );
              })}
            </ChartCard>

            {/* D: Risk Distribution Donut */}
            <ChartCard t={t} title="Scenario Risk Distribution" subtitle="Risk across 50-scenario catalog" icon={AlertTriangle}>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={RISK} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={52} outerRadius={82} paddingAngle={3} strokeWidth={0}>
                    {RISK.map((d, i) => <Cell key={i} fill={d.color} />)}
                  </Pie>
                  <Tooltip content={<Tip />} />
                  <Legend wrapperStyle={{ fontSize: 11 }} formatter={v => <span style={{ color: t.muted }}>{v}</span>} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* E: Top Opportunities */}
            <ChartCard t={t} title="Top Savings Opportunities" subtitle="Biggest adoption gap roles" icon={Zap}>
              {TOP_OPPS.map((o, i) => (
                <div key={o.role} style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 0", borderBottom: `1px solid ${t.border}22` }}>
                  <div style={{ width: 18, fontSize: 12, color: t.muted, fontFamily: "'JetBrains Mono', monospace", textAlign: "right" }}>{i + 1}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, color: t.text, fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{o.role}</div>
                    <div style={{ fontSize: 11, color: t.muted }}>{o.fn}</div>
                  </div>
                  <div style={{ width: 65, fontSize: 13, color: S.realized, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", textAlign: "right" }}>
                    ${(o.savings / 1e6).toFixed(1)}M
                  </div>
                  <div style={{ width: 100, height: 7, background: t.surface, borderRadius: 4, overflow: "hidden" }}>
                    <div style={{
                      width: `${(o.savings / maxSav) * 100}%`, height: "100%", borderRadius: 4,
                      background: `linear-gradient(90deg, ${t.primary}, ${S.realized})`, transition: "width 1s",
                    }} />
                  </div>
                  <div style={{ width: 55, fontSize: 11, color: t.muted, fontFamily: "'JetBrains Mono', monospace", textAlign: "right" }}>{o.fte} FTE</div>
                </div>
              ))}
            </ChartCard>

            {/* F: Automation by Category */}
            <ChartCard t={t} title="Automation by Task Category" subtitle="Realized vs opportunity gap by task type" icon={Cpu}>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={CAT_DATA} layout="vertical" margin={{ left: 0, right: 16, top: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={t.border} horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: t.muted, fontSize: 10 }} tickFormatter={v => `${v}%`} />
                  <YAxis type="category" dataKey="cat" width={88} tick={{ fill: t.muted, fontSize: 11 }} />
                  <Bar dataKey="realized" stackId="s" fill={t.accent} name="Realized" />
                  <Bar dataKey="opp" stackId="s" fill={t.primary} name="Opportunity" radius={[0, 4, 4, 0]} />
                  <Tooltip content={<Tip />} />
                  <Legend wrapperStyle={{ fontSize: 11 }} formatter={v => <span style={{ color: t.muted }}>{v}</span>} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* G: Human System Dashboard */}
            <ChartCard t={t} title="Transformation Readiness" subtitle="Human system — the binding constraint" icon={Brain}>
              <div style={{ display: "flex", gap: 8, paddingLeft: 100, marginBottom: 6 }}>
                {["Proficiency", "Readiness", "Trust"].map(h => (
                  <div key={h} style={{ flex: 1, fontSize: 10, color: t.muted }}>{h}</div>
                ))}
                <div style={{ width: 54, textAlign: "center", fontSize: 10, color: t.muted }}>Mult.</div>
              </div>
              {HUMAN_SYS.map(h => {
                const mc = h.mult >= 0.5 ? S.realized : h.mult >= 0.35 ? t.warning : t.destructive;
                return (
                  <div key={h.fn} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${t.border}22` }}>
                    <div style={{ width: 10, height: 10, borderRadius: "50%", background: h.color, flexShrink: 0 }} />
                    <div style={{ width: 78, fontSize: 13, color: t.text, fontWeight: 500 }}>{h.fn}</div>
                    {[h.prof, h.ready, h.trust].map((v, j) => (
                      <div key={j} style={{ flex: 1 }}>
                        <div style={{ height: 6, background: t.surface, borderRadius: 3, overflow: "hidden" }}>
                          <div style={{ width: `${v}%`, height: "100%", borderRadius: 3, background: v > 50 ? S.realized : v > 30 ? t.warning : t.destructive, transition: "width 0.8s" }} />
                        </div>
                        <div style={{ fontSize: 11, color: t.muted, fontFamily: "'JetBrains Mono', monospace", marginTop: 2 }}>{v}</div>
                      </div>
                    ))}
                    <div style={{ width: 54, textAlign: "center" }}>
                      <div style={{ fontSize: 15, fontWeight: 700, color: mc, fontFamily: "'JetBrains Mono', monospace" }}>{h.mult.toFixed(2)}</div>
                      <div style={{ fontSize: 9, color: t.muted }}>{h.mult >= 0.5 ? "✓ Ready" : "⚠ Low"}</div>
                    </div>
                  </div>
                );
              })}
              <div style={{ marginTop: 10, padding: "7px 12px", borderRadius: 8, background: `${t.warning}11`, border: `1px solid ${t.warning}22`, fontSize: 11, color: t.warning }}>
                ⚠ 3 of 4 functions below 0.5 threshold — human system is the binding constraint
              </div>
            </ChartCard>

            {/* H: (empty slot or additional chart can go here) */}
          </div>

          {/* ═══ AI INSIGHT STRIP ═══ */}
          <div style={{
            background: `linear-gradient(135deg, ${t.card}, ${t.accent}08)`,
            border: `1px solid ${t.border}`, borderLeft: `3px solid ${t.accent}`,
            borderRadius: "0.75rem", padding: "16px 22px",
            display: "flex", alignItems: "flex-start", gap: 14,
          }}>
            <Sparkles size={20} color={t.accent} style={{ flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, color: t.text, lineHeight: 1.7 }}>
                <strong>Claims</strong> has the largest adoption gap (<span style={{ color: t.primary, fontFamily: "'JetBrains Mono', monospace" }}>$15.0M/yr</span>) but the lowest readiness (<span style={{ color: t.warning, fontFamily: "'JetBrains Mono', monospace" }}>36%</span>). <strong>Technology</strong> has 3× higher readiness at 66% — consider starting there. The <strong>"Adoption Gap Only"</strong> scenario (SC-1.5) can recover <span style={{ color: S.realized, fontFamily: "'JetBrains Mono', monospace" }}>$9.1M</span> using tools you already pay for.
              </div>
              <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
                {[
                  { l: "Explore Claims", c: t.primary },
                  { l: "Run SC-1.5", c: S.realized },
                  { l: "Ask Nova", c: t.accent },
                ].map(b => (
                  <button key={b.l} style={{
                    background: "transparent", border: `1px solid ${b.c}44`, color: b.c,
                    padding: "5px 14px", borderRadius: 6, fontSize: 12, fontWeight: 600,
                    cursor: "pointer", display: "flex", alignItems: "center", gap: 4,
                    fontFamily: "Inter, system-ui, sans-serif",
                  }}>{b.l} <ChevronRight size={12} /></button>
                ))}
              </div>
            </div>
          </div>
          <div style={{ height: 40 }} />
        </div>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');
        @keyframes pulsing { 0%,100%{opacity:1} 50%{opacity:0.3} }
        .pulseDot { animation: pulsing 2s infinite ease-in-out; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        button:hover { filter: brightness(1.2); }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e2d4266; border-radius: 3px; }
      `}</style>
    </div>
  );
}
