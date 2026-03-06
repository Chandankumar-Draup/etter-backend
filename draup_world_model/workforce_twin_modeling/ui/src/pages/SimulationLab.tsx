import { useState, useMemo, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import { usePresets, useTools, useFunctions } from '../hooks/useOrganization'
import { api } from '../api/client'
import GlassCard from '../components/common/GlassCard'
import MetricCard from '../components/common/MetricCard'
import TimeSeriesChart from '../components/charts/TimeSeriesChart'
import RadarChart from '../components/charts/RadarChart'
import {
  Activity, Play, Settings, TrendingUp, Users, DollarSign, Brain,
  Shield, Zap, ChevronLeft, ChevronRight, Layers, ChevronDown, ChevronUp,
  Wrench, Target, Wallet, Cpu, BarChart3, UserCog, Building2, GraduationCap,
  GitMerge, RefreshCw, Pause, Combine, ListOrdered, SlidersHorizontal,
  FlaskConical, Scale, Swords, MoreHorizontal, Info, ArrowRight,
} from 'lucide-react'
import { clsx } from 'clsx'
import { SimulationResult, PresetScenario } from '../types'
import CascadeView from '../components/simulation/CascadeView'

const TABS = [
  { key: 'headcount', label: 'Headcount', icon: Users },
  { key: 'financial', label: 'Financial', icon: DollarSign },
  { key: 'adoption', label: 'Adoption & Human System', icon: TrendingUp },
  { key: 'cascade', label: 'Cascade', icon: Layers },
  { key: 'trace', label: 'Trace Explorer', icon: Settings },
]

// ─── Stimulus type definitions with per-type field visibility ───
// status: 'ready' = fully functional, 'beta' = runs but uses preset approximation, 'coming_soon' = needs engine work
interface StimulusTypeDef {
  value: string; label: string; icon: any; desc: string; question: string
  fields: Record<string, boolean>
  defaults: { policy: string; absorption: number; adoptAlpha: number; enableExpansion?: boolean; enableExtension?: boolean }
  category: 'primary' | 'extended'
  status: 'ready' | 'beta' | 'coming_soon'
  noTools?: boolean // if true, send empty tools (no tool deployment)
}

const STIMULUS_TYPES: StimulusTypeDef[] = [
  // ─── Primary (Row 1 & 2) ───
  {
    value: 'technology_injection', label: 'Technology Injection', icon: Wrench,
    desc: 'Deploy new AI tools to functions',
    question: 'Which tools do you want to deploy, and where?',
    fields: { tools: true, scope: true, policy: true, absorption: true, training: true },
    defaults: { policy: 'moderate_reduction', absorption: 0.35, adoptAlpha: 0.6 },
    category: 'primary', status: 'ready',
  },
  {
    value: 'headcount_target', label: 'Headcount Target', icon: Target,
    desc: 'Inverse solve: finds the adoption rate that achieves your HC reduction target',
    question: 'Set your HC reduction target — engine solves for the adoption rate needed.',
    fields: { hcTarget: true, scope: true, policy: true, tools: true },
    defaults: { policy: 'active_reduction', absorption: 0.25, adoptAlpha: 0.7 },
    category: 'primary', status: 'ready',
  },
  {
    value: 'budget_constraint', label: 'Budget Constraint', icon: Wallet,
    desc: 'Inverse solve: finds the maximum adoption rate within your budget',
    question: 'Set your budget — engine finds the highest adoption affordable.',
    fields: { budget: true, scope: true, tools: true, policy: true },
    defaults: { policy: 'moderate_reduction', absorption: 0.35, adoptAlpha: 0.5 },
    category: 'primary', status: 'ready',
  },
  {
    value: 'automation_target', label: 'Automation Target', icon: Cpu,
    desc: 'Inverse solve: finds the adoption rate that achieves your automation target',
    question: 'Set your automation target — engine solves for the adoption rate needed.',
    fields: { autoTarget: true, scope: true, tools: true, absorption: true },
    defaults: { policy: 'moderate_reduction', absorption: 0.30, adoptAlpha: 0.7 },
    category: 'primary', status: 'ready',
  },
  {
    value: 'output_target', label: 'Output Target', icon: BarChart3,
    desc: 'Simulate with balanced adoption to maintain output levels',
    question: 'Set output target — engine simulates balanced adoption to maintain productivity.',
    fields: { outputTarget: true, scope: true, tools: true, policy: true },
    defaults: { policy: 'moderate_reduction', absorption: 0.35, adoptAlpha: 0.6 },
    category: 'primary', status: 'beta',
  },
  {
    value: 'role_transformation', label: 'Role Redesign', icon: UserCog,
    desc: 'Simulate tool deployment focused on specific roles',
    question: 'Which roles do you want to redesign with AI augmentation?',
    fields: { scope: true, tools: true, training: true },
    defaults: { policy: 'no_layoffs', absorption: 0.20, adoptAlpha: 0.5 },
    category: 'primary', status: 'ready',
  },
  {
    value: 'function_transformation', label: 'Function Overhaul', icon: Building2,
    desc: 'Multi-phase transformation with adopt + expand + extend',
    question: 'Which functions are being transformed? (All 3 S-curve phases enabled)',
    fields: { scope: true, tools: true, policy: true, training: true, absorption: true },
    defaults: { policy: 'moderate_reduction', absorption: 0.30, adoptAlpha: 0.7, enableExpansion: true, enableExtension: true },
    category: 'primary', status: 'ready',
  },
  {
    value: 'skill_intervention', label: 'Skill Intervention', icon: GraduationCap,
    desc: 'Reskilling program — training cost only, no new tools deployed',
    question: 'What is the scope and investment for reskilling? (No tools deployed)',
    fields: { scope: true, training: true, policy: true },
    defaults: { policy: 'no_layoffs', absorption: 0.40, adoptAlpha: 0.4 },
    category: 'primary', status: 'ready', noTools: true,
  },
  {
    value: 'org_restructuring', label: 'Org Restructuring', icon: GitMerge,
    desc: 'Simulate rapid redeployment across restructured functions',
    question: 'Which functions or roles are being restructured?',
    fields: { scope: true, policy: true, absorption: true, training: true },
    defaults: { policy: 'rapid_redeployment', absorption: 0.25, adoptAlpha: 0.6 },
    category: 'primary', status: 'beta',
  },
  {
    value: 'adoption_gap_only', label: 'Adoption Gap', icon: RefreshCw,
    desc: 'Improve adoption of already-deployed tools — no new licenses',
    question: 'Which functions should close the adoption gap on existing tools?',
    fields: { scope: true, policy: true, training: true, absorption: true },
    defaults: { policy: 'natural_attrition', absorption: 0.40, adoptAlpha: 0.5 },
    category: 'primary', status: 'ready', noTools: true,
  },
  // ─── Extended (Show More) ───
  {
    value: 'baseline', label: 'Baseline / Do Nothing', icon: Pause,
    desc: 'Zero adoption — measures cost of inaction over time',
    question: 'Select scope to see what happens with zero adoption (cost of inaction).',
    fields: { scope: true },
    defaults: { policy: 'no_layoffs', absorption: 0.40, adoptAlpha: 0.0 },
    category: 'extended', status: 'ready', noTools: true,
  },
  {
    value: 'composite', label: 'Composite Program', icon: Combine,
    desc: 'Multi-workstream: all 3 S-curve phases with tools + training',
    question: 'Configure a multi-workstream transformation program.',
    fields: { tools: true, scope: true, policy: true, training: true, absorption: true },
    defaults: { policy: 'moderate_reduction', absorption: 0.30, adoptAlpha: 0.7, enableExpansion: true, enableExtension: true },
    category: 'extended', status: 'ready',
  },
  {
    value: 'sequencing', label: 'Sequencing', icon: ListOrdered,
    desc: 'Phased vs parallel deployment — needs multi-run engine support',
    question: 'Function sequencing requires multi-run support (coming soon).',
    fields: { scope: true, tools: true, policy: true, absorption: true },
    defaults: { policy: 'moderate_reduction', absorption: 0.35, adoptAlpha: 0.6 },
    category: 'extended', status: 'coming_soon',
  },
  {
    value: 'sensitivity', label: 'Sensitivity Analysis', icon: SlidersHorizontal,
    desc: 'Parameter sweep — needs multi-run engine support',
    question: 'Sensitivity analysis requires parameter sweep support (coming soon).',
    fields: { scope: true, tools: true, policy: true, absorption: true },
    defaults: { policy: 'moderate_reduction', absorption: 0.35, adoptAlpha: 0.6 },
    category: 'extended', status: 'coming_soon',
  },
  {
    value: 'stress_test', label: 'Stress Test', icon: FlaskConical,
    desc: 'Simulate with extreme parameters — max adoption, aggressive policy',
    question: 'Stress test: runs with 90% adoption ceiling + active reduction. What breaks?',
    fields: { scope: true, tools: true, policy: true, absorption: true },
    defaults: { policy: 'active_reduction', absorption: 0.20, adoptAlpha: 0.9 },
    category: 'extended', status: 'ready',
  },
  {
    value: 'regulatory', label: 'Regulatory Change', icon: Scale,
    desc: 'Compliance-driven transformation with moderate pace',
    question: 'Which functions are affected by regulatory changes?',
    fields: { scope: true, policy: true, training: true, absorption: true },
    defaults: { policy: 'moderate_reduction', absorption: 0.35, adoptAlpha: 0.5 },
    category: 'extended', status: 'beta',
  },
  {
    value: 'competitive', label: 'Competitive Pressure', icon: Swords,
    desc: 'Inverse solve: finds the adoption rate to match competitor automation levels',
    question: 'Set competitor automation level — engine solves for the adoption rate to match.',
    fields: { autoTarget: true, scope: true, tools: true, policy: true, absorption: true },
    defaults: { policy: 'active_reduction', absorption: 0.25, adoptAlpha: 0.8 },
    category: 'extended', status: 'ready',
  },
]

const POLICIES = [
  { value: 'no_layoffs', label: 'No Layoffs', desc: 'Redirect freed capacity' },
  { value: 'natural_attrition', label: 'Natural Attrition', desc: 'Voluntary turnover only' },
  { value: 'moderate_reduction', label: 'Moderate Reduction', desc: 'Balanced approach' },
  { value: 'active_reduction', label: 'Active Reduction', desc: 'Aggressive cuts' },
  { value: 'rapid_redeployment', label: 'Rapid Redeployment', desc: 'Fast transitions' },
]

/** Info tooltip — hover to reveal explanation */
function InfoTip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex ml-1 cursor-help">
      <Info className="w-3 h-3 text-muted-foreground/50 group-hover:text-primary transition-colors" />
      <span className="info-tooltip">
        {text}
      </span>
    </span>
  )
}

// Parameter explanations
const PARAM_TIPS: Record<string, string> = {
  absorption: 'Fraction of freed hours re-absorbed by adjacent tasks (0% = all freed hours become savings, 60% = most hours go to other work)',
  adoptionCeiling: 'Maximum adoption rate the S-curve can reach. Higher = more aggressive rollout. 0% = baseline/do nothing scenario.',
  timeHorizon: 'How many months to simulate forward. Longer horizons show full S-curve maturity and payback.',
  trainingCost: 'Per-person cost for AI tool training, change management workshops, and reskilling programs.',
  policy: 'How freed capacity translates to headcount changes. Ranges from "no layoffs" (redeployment only) to "active reduction" (immediate cuts).',
  hcTarget: 'Target headcount reduction percentage. The inverse solver will find the adoption rate needed to achieve this.',
  budget: 'Maximum total investment budget. The solver finds the highest adoption rate affordable within this constraint.',
  autoTarget: 'Target percentage of tasks to be automated. The solver finds the adoption rate needed to reach this level.',
  outputTarget: 'Productivity level to maintain during transformation (100% = current output, 80% = allow 20% temporary dip).',
  resistance: 'How strongly organizational culture resists change. Higher values mean adoption slows faster under stress.',
  trustBuild: 'How quickly employees build trust in AI tools after seeing positive results. Faster = quicker adoption recovery.',
  hcDelay: 'Months between headcount decisions. Longer delays = more cautious approach, headcount changes in larger batches.',
  aiError: 'Simulate an AI system failure at a specific month to test organizational resilience and trust recovery.',
  scope: 'Select which functions are affected by this transformation. "All" applies org-wide.',
  tools: 'AI tools being deployed in this scenario. Each tool has specific task categories it can address.',
}

/** Compact slider with optional info tooltip */
function Slider({ label, value, min, max, step, onChange, unit = '', format, tip }: {
  label: string; value: number; min: number; max: number; step: number
  onChange: (v: number) => void; unit?: string; format?: (v: number) => string; tip?: string
}) {
  const display = format ? format(value) : `${value}${unit}`
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-muted-foreground flex items-center">
          {label}
          {tip && <InfoTip text={tip} />}
        </span>
        <span className="font-mono text-foreground font-medium">{display}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-primary h-1.5" />
    </div>
  )
}

export default function SimulationLab() {
  const { data: presets } = usePresets()
  const { data: tools } = useTools()
  const { data: functions } = useFunctions()
  const [activeTab, setActiveTab] = useState('headcount')
  const [traceMonth, setTraceMonth] = useState(1)

  // Mode
  const [mode, setMode] = useState<'preset' | 'custom'>('preset')
  const [selectedPreset, setSelectedPreset] = useState('P2')

  // Stimulus
  const [stimulusType, setStimulusType] = useState('technology_injection')
  const [selectedTools, setSelectedTools] = useState<string[]>(['Microsoft Copilot'])
  const [targetFunctions, setTargetFunctions] = useState<string[]>([])
  const [policy, setPolicy] = useState('moderate_reduction')
  const [absorptionFactor, setAbsorptionFactor] = useState(0.35)
  const [trainingCost, setTrainingCost] = useState(2000)
  const [timeHorizon, setTimeHorizon] = useState(36)
  // Type-specific inputs
  const [hcTargetPct, setHcTargetPct] = useState(15)
  const [budgetAmount, setBudgetAmount] = useState(2000000)
  const [autoTargetPct, setAutoTargetPct] = useState(35)
  const [outputTargetPct, setOutputTargetPct] = useState(100)
  // S-Curve (simplified)
  const [adoptAlpha, setAdoptAlpha] = useState(0.6)
  const [enableExpansion, setEnableExpansion] = useState(false)
  const [enableExtension, setEnableExtension] = useState(false)
  // Toggle states
  const [showMoreTypes, setShowMoreTypes] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  // Key feedback overrides (only the 4 most impactful)
  const [resistanceSensitivity, setResistanceSensitivity] = useState(0.4)
  const [trustBuildRate, setTrustBuildRate] = useState(2.0)
  const [hcDecisionDelay, setHcDecisionDelay] = useState(6)
  const [aiErrorMonth, setAiErrorMonth] = useState<number | null>(null)

  const currentType = STIMULUS_TYPES.find((s) => s.value === stimulusType)!
  const fields = currentType.fields

  // When stimulus type changes, apply defaults
  const handleStimulusChange = (newType: string) => {
    const st = STIMULUS_TYPES.find((s) => s.value === newType)!
    setStimulusType(newType)
    setPolicy(st.defaults.policy)
    setAbsorptionFactor(st.defaults.absorption)
    setAdoptAlpha(st.defaults.adoptAlpha)
    setEnableExpansion(st.defaults.enableExpansion ?? false)
    setEnableExtension(st.defaults.enableExtension ?? false)
    // Clear tools for non-tool types
    if (!st.fields.tools) setSelectedTools([])
  }

  const resultsRef = useRef<HTMLDivElement>(null)

  const simulate = useMutation({
    mutationFn: (config: any) => {
      if (mode === 'preset') return api.simulatePreset(selectedPreset)
      return api.simulate(config)
    },
    onSuccess: () => {
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 100)
    },
  })

  const handleRun = () => {
    if (mode === 'preset') {
      simulate.mutate({})
      return
    }

    // Build feedback overrides (only if changed from defaults)
    const fbOverrides: Record<string, unknown> = {}
    if (resistanceSensitivity !== 0.4) fbOverrides.resistance_sensitivity = resistanceSensitivity
    if (trustBuildRate !== 2.0) fbOverrides.trust_build_rate = trustBuildRate
    if (hcDecisionDelay !== 6) fbOverrides.hc_decision_delay_months = hcDecisionDelay
    if (aiErrorMonth !== null) fbOverrides.ai_error_month = aiErrorMonth

    // Determine tools: empty for noTools types, user selection or default for others
    const toolsToSend = currentType.noTools
      ? []
      : selectedTools.length > 0 ? selectedTools : ['Microsoft Copilot']

    // Build inverse solve target fields based on stimulus type
    const inverseTargets: Record<string, unknown> = {}
    if (stimulusType === 'headcount_target') inverseTargets.target_hc_reduction_pct = hcTargetPct
    if (stimulusType === 'budget_constraint') inverseTargets.target_budget_amount = budgetAmount
    if (stimulusType === 'automation_target' || stimulusType === 'competitive') {
      inverseTargets.target_automation_pct = autoTargetPct
    }

    simulate.mutate({
      stimulus_name: currentType.label,
      stimulus_type: stimulusType,
      tools: toolsToSend,
      target_functions: targetFunctions.length > 0 ? targetFunctions : undefined,
      policy,
      absorption_factor: absorptionFactor,
      training_cost_per_person: trainingCost,
      time_horizon_months: timeHorizon,
      hc_review_frequency: 3,
      adoption: { alpha: adoptAlpha, k: 0.3, midpoint: 4, delay_months: 0 },
      expansion: enableExpansion ? { alpha: 0.3, k: 0.25, midpoint: 6, delay_months: 6 } : undefined,
      extension: enableExtension ? { alpha: 0.2, k: 0.2, midpoint: 8, delay_months: 12 } : undefined,
      feedback: Object.keys(fbOverrides).length > 0 ? fbOverrides : undefined,
      ...inverseTargets,
      trace: true,
    })
  }

  const result = simulate.data as SimulationResult | undefined

  // Chart data
  const headcountData = useMemo(() => {
    if (!result?.timeline) return []
    return result.timeline.map((t) => ({
      month: `M${t.month}`, headcount: t.headcount, hc_reduced: t.cumulative_hc_reduced,
    }))
  }, [result])

  const financialData = useMemo(() => {
    if (!result?.timeline) return []
    return result.timeline.map((t) => ({
      month: `M${t.month}`, cumulative_savings: t.cumulative_savings,
      cumulative_investment: t.cumulative_investment,
      net: t.cumulative_savings - t.cumulative_investment,
    }))
  }, [result])

  const adoptionData = useMemo(() => {
    if (!result?.timeline) return []
    return result.timeline.map((t) => ({
      month: `M${t.month}`,
      adoption: Math.round(t.adoption_rate * 100),
      proficiency: Math.round(t.proficiency),
      trust: Math.round(t.trust),
      readiness: Math.round(t.readiness),
    }))
  }, [result])

  const radarData = useMemo(() => {
    if (!result?.summary) return []
    const s = result.summary
    return [
      { subject: 'HC Reduction', value: Math.min(100, (s.total_hc_reduced / Math.max(1, s.initial_headcount)) * 100 * 3) },
      { subject: 'ROI', value: Math.min(100, Math.max(0, s.roi_pct ?? 0)) },
      { subject: 'Trust', value: s.final_trust ?? 0 },
      { subject: 'Proficiency', value: s.final_proficiency ?? 0 },
      { subject: 'Adoption', value: (s.peak_adoption ?? 0) * 100 },
      { subject: 'Payback Speed', value: Math.min(100, s.payback_month > 0 ? (36 / s.payback_month) * 30 : 0) },
    ]
  }, [result])

  const currentTrace = useMemo(() => {
    if (!result?.timeline) return null
    return result.timeline.find((t) => t.month === traceMonth) ?? null
  }, [result, traceMonth])

  return (
    <div className="space-y-6">
      <GlassCard title="Simulation Lab" subtitle="What-if scenario modeling with feedback loops" icon={<Activity className="w-4 h-4" />}>
        {/* Mode Toggle */}
        <div className="flex gap-2 mb-4">
          <button onClick={() => setMode('preset')}
            className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-all',
              mode === 'preset' ? 'bg-primary text-primary-foreground' : 'glass')}>
            Presets
          </button>
          <button onClick={() => setMode('custom')}
            className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-all',
              mode === 'custom' ? 'bg-primary text-primary-foreground' : 'glass')}>
            Custom
          </button>
        </div>

        {mode === 'preset' ? (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {presets?.map((p: PresetScenario) => (
              <button key={p.id} onClick={() => setSelectedPreset(p.id)}
                className={clsx('p-3 rounded-lg text-left transition-all',
                  selectedPreset === p.id ? 'bg-primary/15 glow-border' : 'glass hover:bg-muted/50')}>
                <div className="text-xs font-medium text-primary">{p.id}</div>
                <div className="text-sm font-medium mt-0.5">{p.name}</div>
                <div className="text-[10px] text-muted-foreground mt-1">{p.description}</div>
              </button>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {/* ─── Step 1: Choose Stimulus Type (card grid with Show More) ─── */}
            <div>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                What kind of change are you simulating?
              </div>
              {/* Primary types — always visible */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                {STIMULUS_TYPES.filter((st) => st.category === 'primary').map((st) => {
                  const Icon = st.icon
                  const active = stimulusType === st.value
                  const isDisabled = st.status === 'coming_soon'
                  return (
                    <button key={st.value} onClick={() => !isDisabled && handleStimulusChange(st.value)}
                      className={clsx(
                        'p-2.5 rounded-lg text-left transition-all border relative',
                        isDisabled && 'opacity-50 cursor-not-allowed',
                        active ? 'bg-primary/10 border-primary/40 glow-border' : 'border-border/30 hover:bg-muted/40'
                      )}>
                      {st.status !== 'ready' && (
                        <span className={clsx(
                          'absolute top-1.5 right-1.5 text-[8px] font-bold uppercase px-1.5 py-0.5 rounded-full',
                          st.status === 'beta' ? 'bg-amber-500/15 text-amber-500' : 'bg-muted text-muted-foreground'
                        )}>
                          {st.status === 'beta' ? 'Beta' : 'Soon'}
                        </span>
                      )}
                      <Icon className={clsx('w-4 h-4 mb-1', active ? 'text-primary' : 'text-muted-foreground')} />
                      <div className={clsx('text-[11px] font-semibold leading-tight', active && 'text-primary')}>{st.label}</div>
                      <div className="text-[9px] text-muted-foreground mt-0.5 leading-tight">{st.desc}</div>
                    </button>
                  )
                })}
              </div>

              {/* Extended types — toggled */}
              {showMoreTypes && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mt-2 pt-2 border-t border-border/20">
                  {STIMULUS_TYPES.filter((st) => st.category === 'extended').map((st) => {
                    const Icon = st.icon
                    const active = stimulusType === st.value
                    const isDisabled = st.status === 'coming_soon'
                    return (
                      <button key={st.value} onClick={() => !isDisabled && handleStimulusChange(st.value)}
                        className={clsx(
                          'p-2.5 rounded-lg text-left transition-all border relative',
                          isDisabled && 'opacity-50 cursor-not-allowed',
                          active ? 'bg-primary/10 border-primary/40 glow-border' : 'border-border/30 hover:bg-muted/40'
                        )}>
                        {st.status !== 'ready' && (
                          <span className={clsx(
                            'absolute top-1.5 right-1.5 text-[8px] font-bold uppercase px-1.5 py-0.5 rounded-full',
                            st.status === 'beta' ? 'bg-amber-500/15 text-amber-500' : 'bg-muted text-muted-foreground'
                          )}>
                            {st.status === 'beta' ? 'Beta' : 'Soon'}
                          </span>
                        )}
                        <Icon className={clsx('w-4 h-4 mb-1', active ? 'text-primary' : 'text-muted-foreground')} />
                        <div className={clsx('text-[11px] font-semibold leading-tight', active && 'text-primary')}>{st.label}</div>
                        <div className="text-[9px] text-muted-foreground mt-0.5 leading-tight">{st.desc}</div>
                      </button>
                    )
                  })}
                </div>
              )}

              {/* Show More / Less toggle */}
              <button onClick={() => setShowMoreTypes(!showMoreTypes)}
                className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-primary transition-colors">
                <MoreHorizontal className="w-3.5 h-3.5" />
                <span>{showMoreTypes ? 'Show Less' : `Show More (${STIMULUS_TYPES.filter((s) => s.category === 'extended').length} advanced types)`}</span>
                {showMoreTypes ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>
            </div>

            {/* ─── Step 2: Context-specific configuration ─── */}
            <div className="border border-border/40 rounded-xl p-5 space-y-5">
              {/* Question header */}
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                  {(() => { const Icon = currentType.icon; return <Icon className="w-4 h-4 text-primary" /> })()}
                </div>
                <div>
                  <div className="text-[12px] font-semibold text-foreground">{currentType.question}</div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">{currentType.desc}</div>
                </div>
              </div>

              {(() => {
                const hasCol1 = !!(fields.hcTarget || fields.budget || fields.autoTarget || fields.outputTarget || fields.tools)
                return (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {/* Column 1: Type-specific primary input */}
                    {hasCol1 && (
                      <div className="space-y-4">
                        <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                          <Target className="w-3 h-3" />
                          Target Parameters
                        </div>
                        {fields.hcTarget && (
                          <Slider label="HC Reduction Target" value={hcTargetPct} min={5} max={50} step={5}
                            onChange={setHcTargetPct} format={(v) => `${v}%`} tip={PARAM_TIPS.hcTarget} />
                        )}
                        {fields.budget && (
                          <Slider label="Total Budget" value={budgetAmount} min={500000} max={10000000} step={500000}
                            onChange={setBudgetAmount} format={(v) => `$${(v / 1e6).toFixed(1)}M`} tip={PARAM_TIPS.budget} />
                        )}
                        {fields.autoTarget && (
                          <Slider label="Target Automation %" value={autoTargetPct} min={10} max={60} step={5}
                            onChange={setAutoTargetPct} format={(v) => `${v}%`} tip={PARAM_TIPS.autoTarget} />
                        )}
                        {fields.outputTarget && (
                          <Slider label="Output to Maintain" value={outputTargetPct} min={80} max={120} step={5}
                            onChange={setOutputTargetPct} format={(v) => `${v}%`} tip={PARAM_TIPS.outputTarget} />
                        )}
                        {fields.tools && (
                          <div>
                            <div className="flex items-center gap-1.5 mb-2">
                              <label className="label-caps">Tools</label>
                              <InfoTip text={PARAM_TIPS.tools} />
                            </div>
                            <div className="space-y-1 max-h-[140px] overflow-y-auto custom-scrollbar pr-1 glass-inner rounded-lg p-2">
                              {tools?.map((t: any) => (
                                <label key={t.tool_id} className="flex items-center gap-2 text-[11px] cursor-pointer hover:bg-primary/5 rounded-md px-2 py-1 transition-colors">
                                  <input type="checkbox" checked={selectedTools.includes(t.tool_name)}
                                    onChange={(e) => {
                                      if (e.target.checked) setSelectedTools([...selectedTools, t.tool_name])
                                      else setSelectedTools(selectedTools.filter((n) => n !== t.tool_name))
                                    }} className="accent-primary rounded" />
                                  <span>{t.tool_name}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Target Scope */}
                    {fields.scope && (
                      <div>
                        <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5 mb-4">
                          <Layers className="w-3 h-3" />
                          Scope
                          <InfoTip text={PARAM_TIPS.scope} />
                        </div>
                        <div className="space-y-1 max-h-[200px] overflow-y-auto custom-scrollbar pr-1 glass-inner rounded-lg p-2">
                          <label className="flex items-center gap-2 text-[11px] cursor-pointer hover:bg-primary/5 rounded-md px-2 py-1.5 transition-colors">
                            <input type="checkbox" checked={targetFunctions.length === 0}
                              onChange={() => setTargetFunctions([])} className="accent-primary rounded" />
                            <span className="font-medium text-primary">All Functions</span>
                          </label>
                          <div className="border-t border-border/20 my-1" />
                          {functions?.map((f: any) => (
                            <label key={f.name} className="flex items-center gap-2 text-[11px] cursor-pointer hover:bg-primary/5 rounded-md px-2 py-1.5 transition-colors">
                              <input type="checkbox" checked={targetFunctions.includes(f.name)}
                                onChange={(e) => {
                                  if (e.target.checked) setTargetFunctions([...targetFunctions, f.name])
                                  else setTargetFunctions(targetFunctions.filter((n) => n !== f.name))
                                }} className="accent-primary rounded" />
                              {f.name}
                            </label>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Policy + Simulation Parameters */}
                    <div className="space-y-4">
                      <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <Settings className="w-3 h-3" />
                        Simulation Parameters
                      </div>

                      {fields.policy && (
                        <div>
                          <div className="flex items-center gap-1.5 mb-1.5">
                            <label className="text-[11px] text-muted-foreground">HC Policy</label>
                            <InfoTip text={PARAM_TIPS.policy} />
                          </div>
                          <select value={policy} onChange={(e) => setPolicy(e.target.value)}
                            className="w-full text-xs bg-muted border border-border rounded-lg px-3 py-2.5 text-foreground focus:border-primary/50 focus:outline-none transition-colors">
                            {POLICIES.map((p) => (
                              <option key={p.value} value={p.value}>{p.label} — {p.desc}</option>
                            ))}
                          </select>
                        </div>
                      )}

                      {fields.absorption && (
                        <Slider label="Absorption Factor" value={absorptionFactor} min={0} max={0.6} step={0.05}
                          onChange={setAbsorptionFactor} format={(v) => `${(v * 100).toFixed(0)}%`} tip={PARAM_TIPS.absorption} />
                      )}

                      {fields.training && (
                        <Slider label="Training Cost / Person" value={trainingCost} min={500} max={10000} step={500}
                          onChange={setTrainingCost} format={(v) => `$${v.toLocaleString()}`} tip={PARAM_TIPS.trainingCost} />
                      )}

                      <Slider label="Adoption Ceiling" value={adoptAlpha} min={currentType.noTools && currentType.defaults.adoptAlpha === 0 ? 0 : 0.1} max={0.95} step={0.05}
                        onChange={setAdoptAlpha} format={(v) => v === 0 ? '0% (baseline)' : `${(v * 100).toFixed(0)}%`} tip={PARAM_TIPS.adoptionCeiling} />

                      <Slider label="Time Horizon" value={timeHorizon} min={12} max={60} step={6}
                        onChange={setTimeHorizon} unit=" months" tip={PARAM_TIPS.timeHorizon} />
                    </div>
                  </div>
                )
              })()}
            </div>

            {/* ─── Step 3: Advanced (collapsed, only key params) ─── */}
            <button onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-[11px] text-muted-foreground hover:text-foreground transition-colors group">
              <div className={clsx('w-5 h-5 rounded-md bg-muted/50 flex items-center justify-center transition-colors group-hover:bg-primary/10',
                showAdvanced && 'bg-primary/10')}>
                {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </div>
              <span>Advanced Settings</span>
              <span className="text-[9px] text-muted-foreground/60">(phases, feedback tuning, error injection)</span>
            </button>

            {showAdvanced && (
              <div className="border border-border/30 rounded-xl p-5 space-y-5">
                {/* Multi-phase toggles */}
                <div>
                  <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                    <TrendingUp className="w-3 h-3" />
                    Adoption Phases
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <label className="flex items-center gap-2 text-[11px] glass-inner rounded-lg px-3 py-2 opacity-60">
                      <input type="checkbox" checked disabled className="accent-primary rounded" />
                      <span>Phase 1: Adopt</span>
                      <span className="text-[9px] text-primary">(always on)</span>
                    </label>
                    <label className="flex items-center gap-2 text-[11px] cursor-pointer glass-inner rounded-lg px-3 py-2 hover:bg-primary/5 transition-colors">
                      <input type="checkbox" checked={enableExpansion}
                        onChange={(e) => setEnableExpansion(e.target.checked)} className="accent-primary rounded" />
                      <span>Phase 2: Expand</span>
                    </label>
                    <label className="flex items-center gap-2 text-[11px] cursor-pointer glass-inner rounded-lg px-3 py-2 hover:bg-primary/5 transition-colors">
                      <input type="checkbox" checked={enableExtension}
                        onChange={(e) => setEnableExtension(e.target.checked)} className="accent-primary rounded" />
                      <span>Phase 3: Extend (workflow automation)</span>
                    </label>
                  </div>
                </div>

                <div className="border-t border-border/20" />

                {/* Key feedback tuning — only 4 parameters */}
                <div>
                  <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                    <Activity className="w-3 h-3" />
                    Feedback Loop Tuning
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
                    <Slider label="Change Resistance" value={resistanceSensitivity} min={0} max={1} step={0.1}
                      onChange={setResistanceSensitivity}
                      format={(v) => v <= 0.2 ? 'Low' : v <= 0.5 ? 'Medium' : v <= 0.7 ? 'High' : 'Very High'}
                      tip={PARAM_TIPS.resistance} />
                    <Slider label="Trust Build Speed" value={trustBuildRate} min={0.5} max={5} step={0.5}
                      onChange={setTrustBuildRate}
                      format={(v) => v <= 1 ? 'Slow' : v <= 2.5 ? 'Normal' : v <= 4 ? 'Fast' : 'Very Fast'}
                      tip={PARAM_TIPS.trustBuild} />
                    <Slider label="HC Decision Delay" value={hcDecisionDelay} min={0} max={18} step={3}
                      onChange={setHcDecisionDelay} unit=" months" tip={PARAM_TIPS.hcDelay} />
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <input type="checkbox" checked={aiErrorMonth !== null}
                          onChange={(e) => setAiErrorMonth(e.target.checked ? 7 : null)} className="accent-primary rounded" />
                        <span className="text-[11px]">Inject AI Error Event</span>
                        <InfoTip text={PARAM_TIPS.aiError} />
                      </div>
                      {aiErrorMonth !== null && (
                        <div className="mt-2">
                          <Slider label="Error at month" value={aiErrorMonth} min={1} max={36} step={1}
                            onChange={setAiErrorMonth} />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="mt-4 flex items-center gap-3">
          <button onClick={handleRun} disabled={simulate.isPending || (mode === 'custom' && currentType.status === 'coming_soon')}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity">
            <Play className="w-4 h-4" />
            {simulate.isPending ? 'Simulating...' : 'Run Simulation'}
          </button>
          {mode === 'custom' && currentType.status === 'coming_soon' && (
            <span className="text-[11px] text-muted-foreground">This type requires multi-run engine support (coming soon)</span>
          )}
          {mode === 'custom' && currentType.status === 'beta' && (
            <span className="text-[11px] text-amber-500">Beta — uses preset approximation, not exact constraint solving</span>
          )}
        </div>

        {simulate.isError && (
          <div className="mt-3 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs">
            {(simulate.error as Error)?.message || 'Simulation failed.'}
          </div>
        )}
      </GlassCard>

      {/* ─── Results ─── */}
      {result && (
        <>
          <div ref={resultsRef} className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <MetricCard label="Initial HC" value={result.summary.initial_headcount} delay={0} />
            <MetricCard label="Final HC" value={result.summary.final_headcount} delay={60} />
            <MetricCard label="HC Reduced" value={result.summary.total_hc_reduced} delay={120} />
            <MetricCard label="Net Savings" value={result.summary.net_savings} format="currency" delay={180} />
            <MetricCard label="Payback" value={result.summary.payback_month > 0 ? `M${result.summary.payback_month}` : 'N/A'} delay={240} />
            <MetricCard label="ROI" value={result.summary.roi_pct ?? 0} format="percent" delay={300} />
          </div>

          {/* Inverse solve result banner */}
          {result.inverse_solve && (
            <div className={clsx(
              'rounded-lg px-4 py-3 text-sm border',
              result.inverse_solve.solved
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
            )}>
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium">
                    {result.inverse_solve.solved ? 'Target Achieved' : 'Target Not Fully Achievable'}
                  </span>
                  <span className="ml-2 opacity-75">
                    Target: {result.inverse_solve.target_value.toLocaleString()}
                    {' → '}Achieved: {result.inverse_solve.achieved_value.toLocaleString()}
                    {' '}({result.inverse_solve.error_pct.toFixed(1)}% error)
                  </span>
                </div>
                <div className="text-xs opacity-60">
                  Solved alpha: {result.inverse_solve.solved_alpha.toFixed(3)}
                  {' | '}{result.inverse_solve.iterations} iterations
                  {' | '}Range: [{result.inverse_solve.feasibility_range[0].toFixed(1)}, {result.inverse_solve.feasibility_range[1].toFixed(1)}]
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-1 overflow-x-auto pb-1">
            {TABS.map((tab) => {
              const Icon = tab.icon
              return (
                <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                  className={clsx(
                    'flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
                    activeTab === tab.key ? 'bg-primary/15 text-primary glow-border' : 'glass hover:bg-muted/50'
                  )}>
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              )
            })}
          </div>

          {activeTab === 'headcount' && (
            <div className="space-y-4">
              {/* ─── Compact KPI Strip ─── */}
              <div className="glass p-4 rounded-xl">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  {/* Flow: Current → Reduced → Final */}
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4 text-primary" />
                      <div>
                        <div className="text-[9px] text-muted-foreground uppercase tracking-wider">Current</div>
                        <div className="text-lg font-bold font-mono text-primary">{result.summary.initial_headcount.toLocaleString()}</div>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-destructive/40" />
                    <div>
                      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">Reduced</div>
                      <div className="text-lg font-bold font-mono text-destructive">-{result.summary.total_hc_reduced.toLocaleString()}</div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-success/40" />
                    <div>
                      <div className="text-[9px] text-muted-foreground uppercase tracking-wider">Final</div>
                      <div className="text-lg font-bold font-mono text-success">{result.summary.final_headcount.toLocaleString()}</div>
                    </div>
                  </div>

                  {/* Key metrics */}
                  <div className="flex items-center gap-5 text-[11px]">
                    <span className="flex items-center gap-1.5">
                      <DollarSign className="w-3.5 h-3.5 text-success" />
                      <span className="text-muted-foreground">Net Savings:</span>
                      <span className="font-mono font-bold text-success">${(result.summary.net_savings / 1e6).toFixed(1)}M</span>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-warning" />
                      <span className="text-muted-foreground">Payback:</span>
                      <span className="font-mono font-bold">{result.summary.payback_month > 0 ? `Month ${result.summary.payback_month}` : 'N/A'}</span>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <TrendingUp className="w-3.5 h-3.5 text-primary" />
                      <span className="text-muted-foreground">ROI:</span>
                      <span className="font-mono font-bold text-primary">{(result.summary.roi_pct ?? 0).toFixed(0)}%</span>
                    </span>
                  </div>
                </div>
              </div>

              {/* ─── Charts row ─── */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2">
                  <GlassCard title="Headcount Over Time" glow>
                    <TimeSeriesChart data={headcountData} xKey="month"
                      lines={[
                        { dataKey: 'headcount', label: 'Active HC', color: 'hsl(var(--primary))' },
                        { dataKey: 'hc_reduced', label: 'Cumulative Reduced', color: 'hsl(var(--destructive))', type: 'area' },
                      ]} height={340} />
                  </GlassCard>
                </div>
                <GlassCard title="Simulation Profile">
                  <RadarChart data={radarData} dataKeys={[{ key: 'value', label: 'Score', color: 'hsl(var(--primary))' }]} height={300} />
                </GlassCard>
              </div>
            </div>
          )}

          {activeTab === 'financial' && (
            <GlassCard title="Cumulative Financial Impact" glow>
              <TimeSeriesChart data={financialData} xKey="month"
                lines={[
                  { dataKey: 'cumulative_savings', label: 'Savings', color: 'hsl(var(--success))' },
                  { dataKey: 'cumulative_investment', label: 'Investment', color: 'hsl(var(--destructive))' },
                  { dataKey: 'net', label: 'Net', color: 'hsl(var(--primary))', dashed: true },
                ]} height={360}
                referenceLines={result.summary.payback_month > 0 ? [{ x: `M${result.summary.payback_month}`, label: 'Payback' }] : []} />
            </GlassCard>
          )}

          {activeTab === 'adoption' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2">
                <GlassCard title="Adoption & Human System Dynamics" glow>
                  <TimeSeriesChart data={adoptionData} xKey="month"
                    lines={[
                      { dataKey: 'adoption', label: 'Adoption %', color: 'hsl(var(--primary))' },
                      { dataKey: 'proficiency', label: 'Proficiency', color: 'hsl(var(--accent))' },
                      { dataKey: 'trust', label: 'Trust', color: 'hsl(var(--success))' },
                      { dataKey: 'readiness', label: 'Readiness', color: 'hsl(var(--warning))' },
                    ]} height={360} />
                </GlassCard>
              </div>
              <GlassCard title="Final State">
                <div className="space-y-4 py-2">
                  {[
                    { label: 'Adoption', value: (result.summary.peak_adoption ?? 0) * 100, color: 'primary' },
                    { label: 'Trust', value: result.summary.final_trust ?? 0, color: 'success' },
                    { label: 'Proficiency', value: result.summary.final_proficiency ?? 0, color: 'accent' },
                    { label: 'Readiness', value: result.summary.final_readiness ?? 0, color: 'warning' },
                  ].map((m) => (
                    <div key={m.label}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="label-caps">{m.label}</span>
                        <span className="font-mono">{m.value.toFixed(0)}%</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div className="h-full rounded-full"
                          style={{ width: `${Math.min(100, m.value)}%`, background: `hsl(var(--${m.color}))` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </GlassCard>
            </div>
          )}

          {activeTab === 'cascade' && result.cascade && (
            <CascadeView cascade={result.cascade} />
          )}

          {activeTab === 'trace' && result.timeline && (
            <GlassCard title="Month-by-Month Trace" subtitle="Inspect simulation state at each timestep" glow icon={<Settings className="w-4 h-4" />}>
              <div className="flex items-center gap-3 mb-4">
                <button onClick={() => setTraceMonth(Math.max(1, traceMonth - 1))} className="glass p-1.5 rounded-lg">
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <div className="flex-1">
                  <input type="range" min={1} max={result.timeline.length} value={traceMonth}
                    onChange={(e) => setTraceMonth(parseInt(e.target.value))} className="w-full accent-primary" />
                </div>
                <button onClick={() => setTraceMonth(Math.min(result.timeline.length, traceMonth + 1))} className="glass p-1.5 rounded-lg">
                  <ChevronRight className="w-4 h-4" />
                </button>
                <span className="text-sm font-mono font-medium min-w-[48px] text-center">M{traceMonth}</span>
              </div>

              {currentTrace && (
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                  {[
                    { label: 'Headcount', value: currentTrace.headcount, icon: Users },
                    { label: 'Adoption', value: `${Math.round(currentTrace.adoption_rate * 100)}%`, icon: TrendingUp },
                    { label: 'Proficiency', value: `${Math.round(currentTrace.proficiency)}%`, icon: Brain },
                    { label: 'Trust', value: `${Math.round(currentTrace.trust)}%`, icon: Shield },
                    { label: 'Cum. Savings', value: `$${(currentTrace.cumulative_savings / 1e6).toFixed(1)}M`, icon: DollarSign },
                    { label: 'Cum. Invest', value: `$${(currentTrace.cumulative_investment / 1e6).toFixed(1)}M`, icon: Zap },
                    { label: 'HC Reduced', value: currentTrace.cumulative_hc_reduced, icon: Users },
                    { label: 'Hours Freed', value: Math.round(currentTrace.hours_freed_this_month ?? 0), icon: Layers },
                  ].map((item) => {
                    const Icon = item.icon
                    return (
                      <div key={item.label} className="glass p-3 rounded-lg">
                        <div className="flex items-center gap-1.5 mb-1">
                          <Icon className="w-3 h-3 text-muted-foreground" />
                          <span className="label-caps text-[9px]">{item.label}</span>
                        </div>
                        <div className="text-lg font-bold font-mono">{item.value}</div>
                      </div>
                    )
                  })}
                </div>
              )}
            </GlassCard>
          )}
        </>
      )}
    </div>
  )
}
