import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { clsx } from 'clsx'
import {
  ResponsiveContainer, ComposedChart, Bar, Cell,
  XAxis, YAxis, Tooltip, PieChart, Pie,
} from 'recharts'
import {
  Target, RefreshCw, Zap, GraduationCap, Users, DollarSign,
  GitMerge, Brain, Shield, ChevronRight, ArrowDown, Play,
} from 'lucide-react'
import { CascadeResult } from '../../types'

// ─── Animated Number Counter ───
function AnimatedNumber({ value, decimals = 0, prefix = '', suffix = '', className = '' }: {
  value: number; decimals?: number; prefix?: string; suffix?: string; className?: string
}) {
  const [display, setDisplay] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const animated = useRef(false)

  useEffect(() => {
    animated.current = false
    setDisplay(0)
  }, [value])

  useEffect(() => {
    if (animated.current) return
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !animated.current) {
        animated.current = true
        const duration = 1400
        const start = performance.now()
        const tick = (now: number) => {
          const t = Math.min((now - start) / duration, 1)
          const eased = 1 - Math.pow(1 - t, 4)
          setDisplay(value * eased)
          if (t < 1) requestAnimationFrame(tick)
          else setDisplay(value)
        }
        requestAnimationFrame(tick)
      }
    })
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [value])

  const formatted = decimals > 0
    ? display.toFixed(decimals)
    : Math.round(display).toLocaleString()

  return <span ref={ref} className={className}>{prefix}{formatted}{suffix}</span>
}

function FormattedAnimatedNumber({ value, formatter, className = '' }: {
  value: number; formatter: (v: number) => string; className?: string
}) {
  const [display, setDisplay] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const animated = useRef(false)

  useEffect(() => { animated.current = false; setDisplay(0) }, [value])

  useEffect(() => {
    if (animated.current) return
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !animated.current) {
        animated.current = true
        const duration = 1400
        const start = performance.now()
        const tick = (now: number) => {
          const t = Math.min((now - start) / duration, 1)
          const eased = 1 - Math.pow(1 - t, 4)
          setDisplay(value * eased)
          if (t < 1) requestAnimationFrame(tick)
          else setDisplay(value)
        }
        requestAnimationFrame(tick)
      }
    })
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [value])

  return <span ref={ref} className={className}>{formatter(display)}</span>
}

function HeroMetric({ label, value, decimals = 0, prefix = '', suffix = '', color = '', icon, formatter }: {
  label: string; value: number; decimals?: number; prefix?: string; suffix?: string
  color?: string; icon?: React.ReactNode; formatter?: (v: number) => string
}) {
  return (
    <div className="glass-inner p-3 rounded-xl cascade-chip-enter">
      <div className="flex items-center justify-between mb-1">
        <div className="label-xs">{label}</div>
        {icon && <div className={clsx('text-muted-foreground/50', color)}>{icon}</div>}
      </div>
      <div className={clsx('text-xl font-bold font-mono', color)}>
        {formatter ? (
          <FormattedAnimatedNumber value={value} formatter={formatter} className={color} />
        ) : (
          <AnimatedNumber value={value} decimals={decimals} prefix={prefix} suffix={suffix} className={color} />
        )}
      </div>
    </div>
  )
}

// ─── Step definitions ───
const CASCADE_STEPS = [
  { key: 'scope', num: 1, label: 'Scope', icon: Target, color: 'hsl(187, 94%, 43%)' },
  { key: 'reclassification', num: 2, label: 'Reclassify', icon: RefreshCw, color: 'hsl(265, 80%, 60%)' },
  { key: 'capacity', num: 3, label: 'Capacity', icon: Zap, color: 'hsl(38, 92%, 50%)' },
  { key: 'skills', num: 4, label: 'Skills', icon: GraduationCap, color: 'hsl(160, 84%, 39%)' },
  { key: 'workforce', num: 5, label: 'Workforce', icon: Users, color: 'hsl(350, 89%, 60%)' },
  { key: 'financial', num: 6, label: 'Financial', icon: DollarSign, color: 'hsl(187, 94%, 43%)' },
  { key: 'structural', num: 7, label: 'Structural', icon: GitMerge, color: 'hsl(265, 80%, 60%)' },
  { key: 'human', num: 8, label: 'Human', icon: Brain, color: 'hsl(38, 92%, 50%)' },
  { key: 'risk', num: 9, label: 'Risk', icon: Shield, color: 'hsl(350, 89%, 60%)' },
] as const

const TOOLTIP_STYLE = {
  backgroundColor: 'hsl(222, 47%, 9%)',
  border: '1px solid hsl(222, 30%, 16%)',
  borderRadius: '8px',
  padding: '8px 12px',
  fontSize: '11px',
  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
}

interface CascadeViewProps {
  cascade: CascadeResult
}

export default function CascadeView({ cascade }: CascadeViewProps) {
  // activeStep = which step's detail panel is shown (independent of animation)
  const [activeStep, setActiveStep] = useState(0)
  // revealedStep = how far the cascade animation has progressed (-1 = none revealed)
  const [revealedStep, setRevealedStep] = useState(-1)
  const [isPlaying, setIsPlaying] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const s1 = cascade.step1_scope
  const s2 = cascade.step2_reclassification
  const s3 = cascade.step3_capacity
  const s4 = cascade.step4_skills
  const s5 = cascade.step5_workforce
  const s6 = cascade.step6_financial
  const s7 = cascade.step7_structural
  const s8 = cascade.step8_human_system
  const s9 = cascade.step9_risk

  // Key metric for each step card
  const stepMetrics = useMemo(() => [
    { value: s1.total_headcount.toLocaleString(), sub: 'headcount' },
    { value: `${s2.tasks_to_ai + s2.tasks_to_human_ai}`, sub: 'reclassified' },
    { value: `${Math.round(s3.total_net_freed_hours).toLocaleString()}`, sub: 'hrs freed' },
    { value: `${s4.net_skill_gap}`, sub: 'skill gap' },
    { value: `-${s5.total_reducible_ftes}`, sub: 'FTEs' },
    { value: `$${(s6.net_annual / 1e6).toFixed(1)}M`, sub: 'net annual' },
    { value: `${(s7.total_roles_redesign ?? 0) + (s7.total_roles_elimination ?? 0)}`, sub: 'roles affected' },
    { value: `${s8.change_burden_score}`, sub: 'burden score' },
    { value: s9.overall_risk_level, sub: `${s9.risks?.length ?? 0} risks` },
  ], [s1, s2, s3, s4, s5, s6, s7, s8, s9])

  // Auto-play on mount
  useEffect(() => {
    setRevealedStep(-1)
    setIsPlaying(true)
    let step = 0
    const play = () => {
      setRevealedStep(step)
      step++
      if (step < 9) {
        timerRef.current = setTimeout(play, 400)
      } else {
        setIsPlaying(false)
      }
    }
    timerRef.current = setTimeout(play, 300)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [cascade])

  const handleReplay = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setRevealedStep(-1)
    setIsPlaying(true)
    let step = 0
    const play = () => {
      setRevealedStep(step)
      step++
      if (step < 9) {
        timerRef.current = setTimeout(play, 400)
      } else {
        setIsPlaying(false)
      }
    }
    timerRef.current = setTimeout(play, 300)
  }, [])

  const handleStepClick = useCallback((idx: number) => {
    // Stop animation if playing, reveal all steps
    if (isPlaying && timerRef.current) {
      clearTimeout(timerRef.current)
      setIsPlaying(false)
      setRevealedStep(8)
    }
    // Only change detail panel, NOT the cascade animation
    setActiveStep(idx)
  }, [isPlaying])

  // ─── Chart data ───
  const reclassData = [
    { name: 'AI', value: s2.tasks_to_ai, fill: 'hsl(187, 94%, 43%)' },
    { name: 'Human+AI', value: s2.tasks_to_human_ai, fill: 'hsl(265, 80%, 60%)' },
    { name: 'Unchanged', value: s2.tasks_unchanged, fill: 'hsl(215, 20%, 35%)' },
  ]

  const roleCapData = (s3.role_capacities ?? [])
    .sort((a: any, b: any) => b.freed_pct - a.freed_pct)
    .slice(0, 8)
    .map((rc: any) => ({ name: rc.role_name?.split(' ').slice(0, 3).join(' '), freed: rc.freed_pct, hc: rc.headcount }))

  const workforceData = (s5.role_impacts ?? [])
    .filter((ri: any) => ri.reducible_ftes > 0)
    .sort((a: any, b: any) => b.reducible_ftes - a.reducible_ftes)
    .slice(0, 8)
    .map((ri: any) => ({ name: ri.role_name?.split(' ').slice(0, 3).join(' '), current: ri.current_hc, projected: ri.projected_hc }))

  // ─── Detail panels ───
  const renderDetail = () => {
    const stepDef = CASCADE_STEPS[activeStep]

    switch (stepDef.key) {
      case 'scope':
        return (
          <div className="cascade-detail-enter">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <HeroMetric label="Total Headcount" value={s1.total_headcount} icon={<Users className="w-4 h-4" />} />
              <HeroMetric label="Tasks in Scope" value={s1.total_tasks_in_scope} icon={<Target className="w-4 h-4" />} />
              <HeroMetric label="Addressable" value={s1.addressable_tasks} icon={<Zap className="w-4 h-4" />} color="text-success" />
              <HeroMetric label="Compliance Protected" value={s1.compliance_protected} icon={<Shield className="w-4 h-4" />} color="text-warning" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass-inner p-4 rounded-xl">
                <div className="label-xs mb-2">Functions Affected ({s1.functions_affected?.length ?? 0})</div>
                <div className="flex flex-wrap gap-1.5">
                  {(s1.functions_affected ?? []).map((f: string, i: number) => (
                    <span key={f} className="cascade-chip-enter text-[11px] bg-primary/10 text-primary px-3 py-1 rounded-full font-medium"
                      style={{ animationDelay: `${i * 60}ms` }}>{f}</span>
                  ))}
                </div>
              </div>
              <div className="glass-inner p-4 rounded-xl">
                <div className="label-xs mb-2">Roles in Scope ({s1.affected_roles?.length ?? 0})</div>
                <div className="grid grid-cols-2 gap-1">
                  {(s1.affected_roles ?? []).slice(0, 10).map((r: string, i: number) => (
                    <span key={r} className="cascade-chip-enter text-[10px] text-muted-foreground truncate"
                      style={{ animationDelay: `${i * 40}ms` }}>{r}</span>
                  ))}
                  {(s1.affected_roles?.length ?? 0) > 10 && (
                    <span className="text-[10px] text-primary">+{s1.affected_roles.length - 10} more</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )

      case 'reclassification':
        return (
          <div className="cascade-detail-enter">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <HeroMetric label="Tasks → AI" value={s2.tasks_to_ai} color="text-primary" icon={<Zap className="w-4 h-4" />} />
              <HeroMetric label="Tasks → Human+AI" value={s2.tasks_to_human_ai} color="text-accent" icon={<Users className="w-4 h-4" />} />
              <HeroMetric label="Unchanged" value={s2.tasks_unchanged} icon={<RefreshCw className="w-4 h-4" />} />
              <HeroMetric label="Freed Hrs/Person" value={s2.total_freed_hours_per_person} decimals={1} suffix="h" color="text-success" icon={<Zap className="w-4 h-4" />} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass-inner p-4 rounded-xl">
                <div className="label-xs mb-2">Task Distribution</div>
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie data={reclassData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                      innerRadius={45} outerRadius={70} paddingAngle={3} strokeWidth={0}
                      animationBegin={0} animationDuration={1200}>
                      {reclassData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                    </Pie>
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex justify-center gap-4 mt-1">
                  {reclassData.map((d) => (
                    <div key={d.name} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      <span className="w-2 h-2 rounded-full" style={{ background: d.fill }} />
                      {d.name} ({d.value})
                    </div>
                  ))}
                </div>
              </div>
              <div className="glass-inner p-4 rounded-xl">
                <div className="label-xs mb-2">Top Reclassified Tasks</div>
                <div className="space-y-1.5 max-h-[200px] overflow-y-auto custom-scrollbar">
                  {(s2.reclassified_tasks ?? [])
                    .filter((t: any) => t.new_state !== t.previous_state)
                    .slice(0, 10)
                    .map((t: any, i: number) => (
                      <div key={i} className="cascade-chip-enter flex items-center gap-2 text-[11px]"
                        style={{ animationDelay: `${i * 50}ms` }}>
                        <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0',
                          t.new_state === 'ai_automated' ? 'bg-primary' : 'bg-accent')} />
                        <span className="truncate flex-1 text-muted-foreground">{t.task_name}</span>
                        <span className="font-mono text-[10px] text-primary shrink-0">{t.freed_hours.toFixed(1)}h</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>
        )

      case 'capacity':
        return (
          <div className="cascade-detail-enter">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <HeroMetric label="Gross Freed" value={s3.total_gross_freed_hours} suffix=" hrs" icon={<Zap className="w-4 h-4" />} />
              <HeroMetric label="Net Freed" value={s3.total_net_freed_hours} suffix=" hrs" color="text-success" icon={<Zap className="w-4 h-4" />} />
              <HeroMetric label="Absorption" value={s3.absorption_factor * 100} suffix="%" icon={<RefreshCw className="w-4 h-4" />} />
              <HeroMetric label="Dampening" value={s3.dampening_ratio * 100} decimals={1} suffix="%" icon={<ArrowDown className="w-4 h-4" />} />
            </div>
            {roleCapData.length > 0 && (
              <div className="glass-inner p-4 rounded-xl">
                <div className="label-xs mb-2">Capacity Freed by Role</div>
                <ResponsiveContainer width="100%" height={220}>
                  <ComposedChart data={roleCapData} layout="vertical" margin={{ left: 10, right: 20 }}>
                    <XAxis type="number" tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 10 }}
                      tickFormatter={(v: number) => `${v}%`} />
                    <YAxis type="category" dataKey="name" width={120}
                      tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 10 }} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [`${v.toFixed(1)}%`, 'Freed']} />
                    <Bar dataKey="freed" radius={[0, 4, 4, 0]} animationBegin={200} animationDuration={1200}>
                      {roleCapData.map((_: any, i: number) => (
                        <Cell key={i} fill={`hsl(187, 94%, ${43 + i * 4}%)`} fillOpacity={0.85} />
                      ))}
                    </Bar>
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )

      case 'skills':
        return (
          <div className="cascade-detail-enter">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              <HeroMetric label="Net Skill Gap" value={s4.net_skill_gap} icon={<GraduationCap className="w-4 h-4" />} />
              <HeroMetric label="Sunset Skills" value={s4.sunset_skills?.length ?? 0} color="text-destructive" icon={<ArrowDown className="w-4 h-4" />} />
              <HeroMetric label="Sunrise Skills" value={s4.sunrise_skills?.length ?? 0} color="text-success" icon={<Zap className="w-4 h-4" />} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass-inner p-4 rounded-xl">
                <div className="label-xs text-destructive mb-3">Declining Skills</div>
                <div className="space-y-2">
                  {(s4.sunset_skills ?? []).map((s: any, i: number) => (
                    <div key={s.skill_name} className="cascade-chip-enter flex items-center gap-2"
                      style={{ animationDelay: `${i * 80}ms` }}>
                      <div className="w-6 h-6 rounded-full bg-destructive/15 flex items-center justify-center">
                        <ArrowDown className="w-3 h-3 text-destructive" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[12px] font-medium truncate">{s.skill_name}</div>
                        <div className="text-[10px] text-muted-foreground truncate">{s.reason}</div>
                      </div>
                    </div>
                  ))}
                  {(s4.sunset_skills ?? []).length === 0 && <div className="text-[11px] text-muted-foreground">None identified</div>}
                </div>
              </div>
              <div className="glass-inner p-4 rounded-xl">
                <div className="label-xs text-success mb-3">Emerging Skills</div>
                <div className="space-y-2">
                  {(s4.sunrise_skills ?? []).map((s: any, i: number) => (
                    <div key={s.skill_name} className="cascade-chip-enter flex items-center gap-2"
                      style={{ animationDelay: `${i * 80}ms` }}>
                      <div className="w-6 h-6 rounded-full bg-success/15 flex items-center justify-center">
                        <Zap className="w-3 h-3 text-success" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[12px] font-medium truncate">{s.skill_name}</div>
                        <div className="text-[10px] text-muted-foreground truncate">{s.reason}</div>
                      </div>
                    </div>
                  ))}
                  {(s4.sunrise_skills ?? []).length === 0 && <div className="text-[11px] text-muted-foreground">None identified</div>}
                </div>
              </div>
            </div>
          </div>
        )

      case 'workforce':
        return (
          <div className="cascade-detail-enter">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <HeroMetric label="Current HC" value={s5.total_current_hc} icon={<Users className="w-4 h-4" />} />
              <HeroMetric label="Projected HC" value={s5.total_projected_hc} color="text-primary" icon={<Users className="w-4 h-4" />} />
              <HeroMetric label="Reducible FTEs" value={s5.total_reducible_ftes} color="text-destructive" icon={<ArrowDown className="w-4 h-4" />} />
              <HeroMetric label="Reduction" value={s5.total_reduction_pct} suffix="%" color="text-warning" icon={<Target className="w-4 h-4" />} />
            </div>
            <div className="glass-inner p-1 rounded-full mb-4 inline-flex">
              <span className="text-[10px] font-medium text-primary bg-primary/10 px-3 py-1 rounded-full">
                Policy: {s5.policy_applied?.replace(/_/g, ' ')}
              </span>
            </div>
            {workforceData.length > 0 && (
              <div className="glass-inner p-4 rounded-xl">
                <div className="label-xs mb-2">Role-Level Impact</div>
                <ResponsiveContainer width="100%" height={220}>
                  <ComposedChart data={workforceData} layout="vertical" margin={{ left: 10, right: 20 }}>
                    <XAxis type="number" tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 10 }} />
                    <YAxis type="category" dataKey="name" width={120} tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 10 }} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Bar dataKey="current" name="Current" fill="hsl(215, 20%, 35%)" radius={[0, 4, 4, 0]} animationBegin={0} animationDuration={1000} />
                    <Bar dataKey="projected" name="Projected" fill="hsl(187, 94%, 43%)" radius={[0, 4, 4, 0]} animationBegin={300} animationDuration={1000} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )

      case 'financial': {
        const fmtM = (v: number) => `$${(v / 1e6).toFixed(2)}M`
        return (
          <div className="cascade-detail-enter">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
              <HeroMetric label="Total Investment" value={s6.total_investment} formatter={fmtM} icon={<DollarSign className="w-4 h-4" />} />
              <HeroMetric label="Annual Savings" value={s6.total_savings_annual} formatter={fmtM} color="text-success" icon={<DollarSign className="w-4 h-4" />} />
              <HeroMetric label="Net Annual" value={s6.net_annual} formatter={fmtM} color={s6.net_annual >= 0 ? 'text-success' : 'text-destructive'} icon={<DollarSign className="w-4 h-4" />} />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
              <HeroMetric label="ROI" value={s6.roi_pct} suffix="%" color="text-primary" icon={<Target className="w-4 h-4" />} />
              <HeroMetric label="Payback" value={s6.payback_months > 0 ? s6.payback_months : 0} suffix={s6.payback_months > 0 ? ' mo' : ''} formatter={s6.payback_months <= 0 ? () => 'N/A' : undefined} icon={<Zap className="w-4 h-4" />} />
            </div>
            <div className="glass-inner p-4 rounded-xl">
              <div className="label-xs mb-3">Investment Breakdown</div>
              <div className="space-y-3">
                {[
                  { label: 'License Cost', value: s6.license_cost_annual ?? 0, color: 'hsl(187, 94%, 43%)' },
                  { label: 'Training Cost', value: s6.training_cost ?? 0, color: 'hsl(265, 80%, 60%)' },
                  { label: 'Change Mgmt', value: s6.change_management_cost ?? 0, color: 'hsl(38, 92%, 50%)' },
                ].map((item, i) => {
                  const pct = s6.total_investment > 0 ? (item.value / s6.total_investment) * 100 : 0
                  return (
                    <div key={item.label} className="cascade-chip-enter" style={{ animationDelay: `${i * 100}ms` }}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] text-muted-foreground">{item.label}</span>
                        <span className="text-[11px] font-mono">${(item.value / 1e3).toFixed(0)}K</span>
                      </div>
                      <div className="h-2 bg-muted/50 rounded-full overflow-hidden">
                        <div className="h-full rounded-full cascade-bar-fill" style={{ '--bar-width': `${pct}%`, background: item.color } as any} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )
      }

      case 'structural':
        return (
          <div className="cascade-detail-enter">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass-inner p-4 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-6 h-6 rounded-full bg-amber-500/15 flex items-center justify-center">
                    <GitMerge className="w-3 h-3 text-amber-500" />
                  </div>
                  <div className="label-xs text-amber-500">Redesign Candidates</div>
                  <span className="ml-auto text-sm font-bold font-mono">{s7.redesign_candidates?.length ?? 0}</span>
                </div>
                <div className="space-y-2">
                  {(s7.redesign_candidates ?? []).slice(0, 8).map((r: any, i: number) => (
                    <div key={i} className="cascade-chip-enter flex items-center gap-2 p-2 rounded-lg bg-amber-500/5"
                      style={{ animationDelay: `${i * 80}ms` }}>
                      <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                      <span className="text-[11px] text-muted-foreground truncate">{r.role_name || r.role_id || JSON.stringify(r)}</span>
                    </div>
                  ))}
                  {(s7.redesign_candidates ?? []).length === 0 && <div className="text-[11px] text-muted-foreground p-2">None identified</div>}
                </div>
              </div>
              <div className="glass-inner p-4 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-6 h-6 rounded-full bg-destructive/15 flex items-center justify-center">
                    <Target className="w-3 h-3 text-destructive" />
                  </div>
                  <div className="label-xs text-destructive">Elimination Candidates</div>
                  <span className="ml-auto text-sm font-bold font-mono">{s7.elimination_candidates?.length ?? 0}</span>
                </div>
                <div className="space-y-2">
                  {(s7.elimination_candidates ?? []).slice(0, 8).map((r: any, i: number) => (
                    <div key={i} className="cascade-chip-enter flex items-center gap-2 p-2 rounded-lg bg-destructive/5"
                      style={{ animationDelay: `${i * 80}ms` }}>
                      <span className="w-2 h-2 rounded-full bg-destructive shrink-0" />
                      <span className="text-[11px] text-muted-foreground truncate">{r.role_name || r.role_id || JSON.stringify(r)}</span>
                    </div>
                  ))}
                  {(s7.elimination_candidates ?? []).length === 0 && <div className="text-[11px] text-muted-foreground p-2">None identified</div>}
                </div>
              </div>
            </div>
          </div>
        )

      case 'human':
        return (
          <div className="cascade-detail-enter">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
              <HeroMetric label="Change Burden" value={s8.change_burden_score} icon={<Brain className="w-4 h-4" />}
                color={s8.change_burden_score > 60 ? 'text-destructive' : s8.change_burden_score > 30 ? 'text-warning' : 'text-success'} />
              {[
                { label: 'Proficiency', dir: s8.proficiency_direction },
                { label: 'Readiness', dir: s8.readiness_direction },
                { label: 'Trust', dir: s8.trust_direction },
                { label: 'Capital', dir: s8.political_capital_direction },
              ].map((item) => (
                <div key={item.label} className="glass-inner p-3 rounded-xl cascade-chip-enter">
                  <div className="label-xs mb-1">{item.label}</div>
                  <div className={clsx('text-sm font-bold capitalize',
                    item.dir === 'up' ? 'text-success' : item.dir === 'down' ? 'text-destructive' : 'text-warning'
                  )}>
                    {item.dir === 'up' ? '↑ Increase' : item.dir === 'down' ? '↓ Decrease' : '→ Stable'}
                  </div>
                </div>
              ))}
            </div>
            {s8.narrative && (
              <div className="glass-inner p-4 rounded-xl cascade-chip-enter" style={{ animationDelay: '200ms' }}>
                <div className="label-xs mb-2">Narrative Assessment</div>
                <p className="text-[12px] text-muted-foreground leading-relaxed">{s8.narrative}</p>
              </div>
            )}
          </div>
        )

      case 'risk':
        return (
          <div className="cascade-detail-enter">
            <div className="flex items-center gap-3 mb-4">
              <div className={clsx(
                'px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider',
                s9.overall_risk_level === 'high' ? 'bg-destructive/15 text-destructive cascade-pulse-red' :
                s9.overall_risk_level === 'medium' ? 'bg-amber-500/15 text-amber-500 cascade-pulse-amber' :
                'bg-emerald-500/15 text-emerald-500'
              )}>
                {s9.overall_risk_level} risk
              </div>
              <span className="text-xs text-muted-foreground">{s9.risks?.length ?? 0} risk(s) identified</span>
            </div>
            <div className="space-y-2">
              {(s9.risks ?? []).map((r: any, i: number) => (
                <div key={i} className="cascade-chip-enter glass-inner p-4 rounded-xl" style={{ animationDelay: `${i * 100}ms` }}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={clsx(
                      'text-[9px] font-bold uppercase px-2 py-0.5 rounded-full',
                      r.severity === 'high' ? 'bg-destructive/15 text-destructive' :
                      r.severity === 'medium' ? 'bg-amber-500/15 text-amber-500' :
                      'bg-emerald-500/15 text-emerald-500'
                    )}>{r.severity}</span>
                    <span className="text-[12px] font-semibold">{r.risk_type}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground mb-1">{r.description}</div>
                  {r.mitigation && (
                    <div className="text-[10px] text-primary/80 mt-2 p-2 rounded-lg bg-primary/5">Mitigation: {r.mitigation}</div>
                  )}
                </div>
              ))}
              {(s9.risks ?? []).length === 0 && <div className="text-[11px] text-muted-foreground glass-inner p-4 rounded-xl">No risks identified</div>}
            </div>
          </div>
        )
    }
  }

  return (
    <div className="space-y-4">
      {/* ─── Cascade Animation Strip ─── */}
      <div className="glass p-5 rounded-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
            <Zap className="w-3 h-3" />
            9-Step Cascade Propagation
          </div>
          <button onClick={handleReplay} disabled={isPlaying}
            className={clsx('flex items-center gap-1 text-[10px] px-2.5 py-1 rounded-lg transition-all',
              isPlaying ? 'text-muted-foreground/50' : 'text-primary hover:bg-primary/10 cursor-pointer')}>
            <Play className="w-3 h-3" />
            Replay
          </button>
        </div>

        {/* Step cards — cascade animation */}
        <div className="flex items-center gap-0 overflow-x-auto custom-scrollbar pb-2">
          {CASCADE_STEPS.map((step, idx) => {
            const Icon = step.icon
            const isRevealed = idx <= revealedStep
            const isSelected = idx === activeStep
            const metric = stepMetrics[idx]

            return (
              <div key={step.key} className="flex items-center shrink-0">
                {/* Step card */}
                <button
                  onClick={() => handleStepClick(idx)}
                  className={clsx(
                    'relative flex flex-col items-center p-3 rounded-xl min-w-[90px] transition-all duration-500 cursor-pointer border',
                    isRevealed
                      ? 'cascade-card-reveal opacity-100 scale-100'
                      : 'opacity-0 scale-75',
                    isSelected
                      ? 'border-primary/40 bg-primary/10 shadow-lg shadow-primary/10'
                      : 'border-transparent hover:bg-card/60',
                  )}
                  style={{ animationDelay: isRevealed ? '0ms' : undefined }}
                >
                  {/* Step number badge */}
                  <div className="absolute -top-1.5 -left-1 w-4 h-4 rounded-full text-[8px] font-bold flex items-center justify-center"
                    style={{ background: step.color, color: 'hsl(222, 47%, 6%)' }}>
                    {step.num}
                  </div>

                  <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-1.5"
                    style={{ background: `${step.color}20` }}>
                    <Icon className="w-4 h-4" style={{ color: step.color }} />
                  </div>

                  <div className={clsx('text-[10px] font-semibold whitespace-nowrap mb-1',
                    isSelected ? 'text-foreground' : 'text-muted-foreground')}>
                    {step.label}
                  </div>

                  {/* Key metric */}
                  <div className="text-[13px] font-bold font-mono" style={{ color: step.color }}>
                    {metric.value}
                  </div>
                  <div className="text-[8px] text-muted-foreground uppercase tracking-wider">
                    {metric.sub}
                  </div>
                </button>

                {/* Arrow connector */}
                {idx < 8 && (
                  <div className={clsx(
                    'flex items-center mx-0.5 transition-all duration-500',
                    idx < revealedStep ? 'opacity-100 scale-x-100' : 'opacity-0 scale-x-0',
                  )}>
                    <ChevronRight className="w-4 h-4 text-primary/40" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* ─── Detail Panel (independent of cascade animation) ─── */}
      <div className="glass p-5 rounded-xl" key={activeStep}>
        <div className="flex items-center gap-3 mb-4">
          {(() => {
            const step = CASCADE_STEPS[activeStep]
            const Icon = step.icon
            return (
              <>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${step.color}20` }}>
                  <Icon className="w-4 h-4" style={{ color: step.color }} />
                </div>
                <div>
                  <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">Step {step.num} of 9</div>
                  <div className="text-sm font-semibold">{step.label}</div>
                </div>
                {/* Step nav pills */}
                <div className="ml-auto flex items-center gap-1">
                  {CASCADE_STEPS.map((s, i) => (
                    <button key={s.key} onClick={() => setActiveStep(i)}
                      className={clsx('w-2 h-2 rounded-full transition-all',
                        i === activeStep ? 'bg-primary scale-125' : 'bg-muted-foreground/30 hover:bg-muted-foreground/60')} />
                  ))}
                </div>
              </>
            )
          })()}
        </div>
        {renderDetail()}
      </div>
    </div>
  )
}
