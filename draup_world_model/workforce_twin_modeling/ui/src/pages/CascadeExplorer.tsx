import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useTools, useFunctions } from '../hooks/useOrganization'
import { api } from '../api/client'
import GlassCard from '../components/common/GlassCard'
import MetricCard from '../components/common/MetricCard'
import { GitBranch, Play, Layers, Cpu, Users, DollarSign, Shield, AlertTriangle, Brain } from 'lucide-react'
import { clsx } from 'clsx'
import { CascadeResult } from '../types'

const STEP_LABELS = [
  { key: 'step1_scope', label: 'Scope', icon: Layers, desc: 'What is affected' },
  { key: 'step2_reclassification', label: 'Reclassify', icon: Cpu, desc: 'Task state changes' },
  { key: 'step3_capacity', label: 'Capacity', icon: GitBranch, desc: 'Hours freed' },
  { key: 'step4_skills', label: 'Skills', icon: Brain, desc: 'Sunrise/sunset' },
  { key: 'step5_workforce', label: 'Workforce', icon: Users, desc: 'Headcount impact' },
  { key: 'step6_financial', label: 'Financial', icon: DollarSign, desc: 'Investment vs savings' },
  { key: 'step7_structural', label: 'Structural', icon: Layers, desc: 'Role redesign' },
  { key: 'step8_human_system', label: 'Human', icon: Brain, desc: 'Change burden' },
  { key: 'step9_risk', label: 'Risk', icon: AlertTriangle, desc: 'Risk assessment' },
]

export default function CascadeExplorer() {
  const { data: tools } = useTools()
  const { data: functions } = useFunctions()
  const [selectedTools, setSelectedTools] = useState<string[]>(['Microsoft Copilot'])
  const [selectedFunctions, setSelectedFunctions] = useState<string[]>([])
  const [policy, setPolicy] = useState('moderate_reduction')
  const [absorption, setAbsorption] = useState(0.35)
  const [activeStep, setActiveStep] = useState<string | null>(null)

  const cascade = useMutation({
    mutationFn: (config: any) => api.cascade(config),
  })

  const handleRun = () => {
    cascade.mutate({
      stimulus_name: 'Technology Injection',
      tools: selectedTools,
      target_functions: selectedFunctions.length > 0 ? selectedFunctions : undefined,
      policy,
      absorption_factor: absorption,
    })
  }

  const result = cascade.data as CascadeResult | undefined

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <GlassCard title="Stimulus Configuration" subtitle="Define the technology intervention" icon={<GitBranch className="w-4 h-4" />}>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Tools */}
          <div>
            <label className="label-caps block mb-2">Tools</label>
            <div className="space-y-1">
              {tools?.map((t: any) => (
                <label key={t.tool_id} className="flex items-center gap-2 text-xs cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedTools.includes(t.tool_name)}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedTools([...selectedTools, t.tool_name])
                      else setSelectedTools(selectedTools.filter((n) => n !== t.tool_name))
                    }}
                    className="accent-primary"
                  />
                  {t.tool_name}
                </label>
              ))}
            </div>
          </div>

          {/* Scope */}
          <div>
            <label className="label-caps block mb-2">Scope</label>
            <div className="space-y-1">
              {functions?.map((f: any) => (
                <label key={f.name} className="flex items-center gap-2 text-xs cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedFunctions.includes(f.name)}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedFunctions([...selectedFunctions, f.name])
                      else setSelectedFunctions(selectedFunctions.filter((n) => n !== f.name))
                    }}
                    className="accent-primary"
                  />
                  {f.name} ({f.headcount} HC)
                </label>
              ))}
              <p className="text-[10px] text-muted-foreground mt-1">None selected = all functions</p>
            </div>
          </div>

          {/* Policy */}
          <div>
            <label className="label-caps block mb-2">HC Policy</label>
            <select
              value={policy}
              onChange={(e) => setPolicy(e.target.value)}
              className="w-full text-xs bg-muted border border-border rounded-lg px-3 py-2 text-foreground"
            >
              <option value="no_layoffs">No Layoffs</option>
              <option value="natural_attrition">Natural Attrition</option>
              <option value="moderate_reduction">Moderate Reduction</option>
              <option value="active_reduction">Active Reduction</option>
              <option value="rapid_redeployment">Rapid Redeployment</option>
            </select>
          </div>

          {/* Absorption */}
          <div>
            <label className="label-caps block mb-2">
              Absorption: {(absorption * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min={0} max={0.8} step={0.05}
              value={absorption}
              onChange={(e) => setAbsorption(parseFloat(e.target.value))}
              className="w-full accent-primary"
            />
            <p className="text-[10px] text-muted-foreground mt-1">
              % of freed capacity reabsorbed by remaining staff
            </p>
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={cascade.isPending || selectedTools.length === 0}
          className="mt-4 flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          <Play className="w-4 h-4" />
          {cascade.isPending ? 'Running...' : 'Run Cascade'}
        </button>
      </GlassCard>

      {/* Cascade Pipeline */}
      {result && (
        <>
          {/* 9-Step Pipeline */}
          <div className="flex gap-1 overflow-x-auto pb-2">
            {STEP_LABELS.map((step, i) => {
              const Icon = step.icon
              return (
                <button
                  key={step.key}
                  onClick={() => setActiveStep(activeStep === step.key ? null : step.key)}
                  className={clsx(
                    'flex flex-col items-center gap-1 px-3 py-3 rounded-lg text-center min-w-[80px] transition-all',
                    activeStep === step.key
                      ? 'bg-primary/15 text-primary glow-border'
                      : 'glass hover:bg-muted/50'
                  )}
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-[10px] font-medium">{step.label}</span>
                  <span className="text-[9px] text-muted-foreground">{step.desc}</span>
                </button>
              )
            })}
          </div>

          {/* Summary KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <MetricCard label="In Scope" value={result.step1_scope.total_headcount} delay={0} />
            <MetricCard label="Tasks to AI" value={result.step2_reclassification.tasks_to_ai} delay={60} />
            <MetricCard label="Net Freed Hrs" value={result.step3_capacity.total_net_freed_hours} delay={120} />
            <MetricCard label="HC Reducible" value={result.step5_workforce.total_reducible_ftes} delay={180} />
            <MetricCard label="Net Annual" value={result.step6_financial.net_annual} format="currency" delay={240} />
          </div>

          {/* Step Detail */}
          {activeStep && <StepDetail stepKey={activeStep} result={result} />}
        </>
      )}
    </div>
  )
}

function StepDetail({ stepKey, result }: { stepKey: string; result: CascadeResult }) {
  const stepData = (result as any)[stepKey]
  if (!stepData) return null

  return (
    <GlassCard title={STEP_LABELS.find((s) => s.key === stepKey)?.label} glow>
      {stepKey === 'step1_scope' && (
        <div className="grid grid-cols-3 gap-3 text-xs">
          <div><span className="label-caps">Functions</span><div className="font-mono mt-1">{stepData.functions_affected?.join(', ')}</div></div>
          <div><span className="label-caps">Total Tasks</span><div className="font-mono mt-1">{stepData.total_tasks_in_scope}</div></div>
          <div><span className="label-caps">Addressable</span><div className="font-mono mt-1">{stepData.addressable_tasks}</div></div>
          <div><span className="label-caps">Compliance Protected</span><div className="font-mono mt-1">{stepData.compliance_protected}</div></div>
          <div><span className="label-caps">Headcount</span><div className="font-mono mt-1">{stepData.total_headcount}</div></div>
          <div><span className="label-caps">Hours/Month</span><div className="font-mono mt-1">{stepData.total_hours_month?.toLocaleString()}</div></div>
        </div>
      )}
      {stepKey === 'step5_workforce' && (
        <div className="space-y-3">
          <div className="grid grid-cols-4 gap-3 text-xs">
            <div><span className="label-caps">Current HC</span><div className="stat-value text-lg">{stepData.total_current_hc}</div></div>
            <div><span className="label-caps">Reducible</span><div className="stat-value text-lg text-warning">{stepData.total_reducible_ftes}</div></div>
            <div><span className="label-caps">Projected HC</span><div className="stat-value text-lg text-primary">{stepData.total_projected_hc}</div></div>
            <div><span className="label-caps">Reduction</span><div className="stat-value text-lg text-destructive">{stepData.total_reduction_pct}%</div></div>
          </div>
          <table className="w-full text-[11px]">
            <thead><tr className="border-b border-border"><th className="text-left py-1">Role</th><th className="text-right py-1">Current</th><th className="text-right py-1">Projected</th><th className="text-right py-1">Reduction</th></tr></thead>
            <tbody>
              {stepData.role_impacts?.filter((r: any) => r.reducible_ftes > 0).map((r: any) => (
                <tr key={r.role_id} className="border-b border-border/30">
                  <td className="py-1">{r.role_name}</td>
                  <td className="text-right font-mono">{r.current_hc}</td>
                  <td className="text-right font-mono text-primary">{r.projected_hc}</td>
                  <td className="text-right font-mono text-destructive">-{r.reducible_ftes} ({r.reduction_pct}%)</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {stepKey === 'step6_financial' && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="p-3 bg-destructive/10 rounded-lg"><span className="label-caps">Total Investment</span><div className="text-lg font-bold font-mono text-destructive mt-1">${(stepData.total_investment / 1e6).toFixed(1)}M</div></div>
          <div className="p-3 bg-success/10 rounded-lg"><span className="label-caps">Total Savings</span><div className="text-lg font-bold font-mono text-success mt-1">${(stepData.total_savings_annual / 1e6).toFixed(1)}M</div></div>
          <div className="p-3 bg-primary/10 rounded-lg"><span className="label-caps">Net Annual</span><div className="text-lg font-bold font-mono text-primary mt-1">${(stepData.net_annual / 1e6).toFixed(1)}M</div></div>
          <div><span className="label-caps">ROI</span><div className="text-lg font-bold font-mono mt-1">{stepData.roi_pct}%</div></div>
          <div><span className="label-caps">Payback</span><div className="text-lg font-bold font-mono mt-1">{stepData.payback_months} months</div></div>
        </div>
      )}
      {stepKey === 'step9_risk' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="label-caps">Overall Risk:</span>
            <span className={clsx(
              'px-3 py-1 rounded-full text-xs font-medium border',
              stepData.overall_risk_level === 'high' ? 'bg-destructive/10 text-destructive border-destructive/30' :
              stepData.overall_risk_level === 'medium' ? 'bg-warning/10 text-warning border-warning/30' :
              'bg-success/10 text-success border-success/30'
            )}>{stepData.overall_risk_level?.toUpperCase()}</span>
          </div>
          {stepData.risks?.map((r: any, i: number) => (
            <div key={i} className={clsx(
              'p-3 rounded-lg border-l-[3px]',
              r.severity === 'high' ? 'border-l-destructive bg-destructive/5' :
              r.severity === 'medium' ? 'border-l-warning bg-warning/5' :
              'border-l-success bg-success/5'
            )}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium">{r.risk_type}</span>
                <span className={clsx('text-[10px] px-1.5 py-0.5 rounded',
                  r.severity === 'high' ? 'bg-destructive/20 text-destructive' : 'bg-warning/20 text-warning'
                )}>{r.severity}</span>
              </div>
              <p className="text-[11px] text-muted-foreground">{r.description}</p>
              <p className="text-[11px] text-primary mt-1">{r.mitigation}</p>
            </div>
          ))}
        </div>
      )}
      {/* Generic JSON fallback for other steps */}
      {!['step1_scope', 'step5_workforce', 'step6_financial', 'step9_risk'].includes(stepKey) && (
        <pre className="text-[11px] font-mono text-muted-foreground overflow-x-auto max-h-[400px] custom-scrollbar">
          {JSON.stringify(stepData, null, 2)}
        </pre>
      )}
    </GlassCard>
  )
}
