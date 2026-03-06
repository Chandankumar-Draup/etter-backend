import { useState, useMemo } from 'react'
import { useMutation } from '@tanstack/react-query'
import { usePresets } from '../hooks/useOrganization'
import { api } from '../api/client'
import GlassCard from '../components/common/GlassCard'
import TimeSeriesChart from '../components/charts/TimeSeriesChart'
import RadarChart from '../components/charts/RadarChart'
import BarChartHorizontal from '../components/charts/BarChartHorizontal'
import { GitCompare, CheckSquare, Square } from 'lucide-react'
import { clsx } from 'clsx'
import { PresetScenario, ComparisonData } from '../types'

const CHART_COLORS = [
  'hsl(var(--primary))',
  'hsl(var(--accent))',
  'hsl(var(--success))',
  'hsl(var(--warning))',
  'hsl(var(--destructive))',
]

export default function CompareArena() {
  const { data: presets } = usePresets()
  const [selectedPresets, setSelectedPresets] = useState<string[]>(['P1', 'P2', 'P3'])
  const [activeView, setActiveView] = useState<'timeline' | 'matrix' | 'radar'>('matrix')

  const compare = useMutation({
    mutationFn: (configs: any[]) => api.compare(configs),
  })

  const togglePreset = (id: string) => {
    if (selectedPresets.includes(id)) {
      setSelectedPresets(selectedPresets.filter((p) => p !== id))
    } else if (selectedPresets.length < 5) {
      setSelectedPresets([...selectedPresets, id])
    }
  }

  const handleCompare = () => {
    if (selectedPresets.length < 2) return
    compare.mutate(selectedPresets.map((id) => ({ preset_id: id })))
  }

  const data = compare.data as ComparisonData | undefined
  const scenarios = data?.scenarios ?? []

  const getSummary = (s: typeof scenarios[0]) => s.result.summary
  const getTimeline = (s: typeof scenarios[0]) => s.result.timeline

  // Build overlaid timeline data
  const timelineData = useMemo(() => {
    if (!scenarios.length) return []
    const maxLen = Math.max(...scenarios.map((s) => getTimeline(s)?.length ?? 0))
    const points: any[] = []
    for (let i = 0; i < maxLen; i++) {
      const point: any = { month: `M${i + 1}` }
      scenarios.forEach((s, idx) => {
        const t = getTimeline(s)?.[i]
        if (t) {
          point[`hc_${idx}`] = t.headcount
          point[`savings_${idx}`] = t.cumulative_savings
          point[`adoption_${idx}`] = Math.round(t.adoption_rate * 100)
        }
      })
      points.push(point)
    }
    return points
  }, [scenarios])

  // Build radar comparison data
  const radarData = useMemo(() => {
    if (!scenarios.length) return []
    const sm = scenarios.map(getSummary)
    return [
      { subject: 'HC Reduction', ...Object.fromEntries(sm.map((s, i) => [`s${i}`, Math.min(100, (s.total_hc_reduced / Math.max(1, s.initial_headcount)) * 300)])) },
      { subject: 'ROI', ...Object.fromEntries(sm.map((s, i) => [`s${i}`, Math.min(100, Math.max(0, s.roi_pct ?? 0))])) },
      { subject: 'Trust', ...Object.fromEntries(sm.map((s, i) => [`s${i}`, (s.final_trust ?? 0) * 100])) },
      { subject: 'Proficiency', ...Object.fromEntries(sm.map((s, i) => [`s${i}`, (s.final_proficiency ?? 0) * 100])) },
      { subject: 'Net Savings', ...Object.fromEntries(sm.map((s, i) => [`s${i}`, Math.min(100, Math.max(0, s.net_savings / 1e6))])) },
      { subject: 'Speed', ...Object.fromEntries(sm.map((s, i) => [`s${i}`, s.payback_month > 0 ? Math.min(100, (36 / s.payback_month) * 30) : 0])) },
    ]
  }, [scenarios])

  const hcBarData = useMemo(() => {
    return scenarios.map((s) => ({
      name: s.name,
      value: getSummary(s).total_hc_reduced,
    }))
  }, [scenarios])

  return (
    <div className="space-y-6">
      {/* Preset Selection */}
      <GlassCard title="Compare Arena" subtitle="Select 2-5 scenarios to compare side-by-side" icon={<GitCompare className="w-4 h-4" />}>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {presets?.map((p: PresetScenario) => (
            <button
              key={p.id}
              onClick={() => togglePreset(p.id)}
              className={clsx(
                'p-3 rounded-lg text-left transition-all relative',
                selectedPresets.includes(p.id) ? 'bg-primary/15 glow-border' : 'glass hover:bg-muted/50',
                selectedPresets.length >= 5 && !selectedPresets.includes(p.id) && 'opacity-40'
              )}
            >
              <div className="absolute top-2 right-2">
                {selectedPresets.includes(p.id)
                  ? <CheckSquare className="w-4 h-4 text-primary" />
                  : <Square className="w-4 h-4 text-muted-foreground" />}
              </div>
              <div className="text-xs font-medium text-primary">{p.id}</div>
              <div className="text-sm font-medium mt-0.5">{p.name}</div>
              <div className="text-[10px] text-muted-foreground mt-1">{p.description}</div>
            </button>
          ))}
        </div>

        <button
          onClick={handleCompare}
          disabled={selectedPresets.length < 2 || compare.isPending}
          className="mt-4 flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          <GitCompare className="w-4 h-4" />
          {compare.isPending ? 'Comparing...' : `Compare ${selectedPresets.length} Scenarios`}
        </button>
      </GlassCard>

      {/* Results */}
      {scenarios.length > 0 && (
        <>
          {/* Comparison Matrix */}
          <GlassCard title="Comparison Matrix" glow>
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-3">Metric</th>
                    {scenarios.map((s, i) => (
                      <th key={i} className="text-right py-2 px-3">
                        <div className="flex items-center justify-end gap-1.5">
                          <div className="w-2 h-2 rounded-full" style={{ background: CHART_COLORS[i] }} />
                          <span>{s.name}</span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    { label: 'Initial HC', fn: (s: any) => s.initial_headcount },
                    { label: 'Final HC', fn: (s: any) => s.final_headcount },
                    { label: 'HC Reduced', fn: (s: any) => s.total_hc_reduced, highlight: true },
                    { label: 'Investment', fn: (s: any) => `$${(s.total_investment / 1e6).toFixed(1)}M` },
                    { label: 'Savings', fn: (s: any) => `$${(s.total_savings / 1e6).toFixed(1)}M` },
                    { label: 'Net Savings', fn: (s: any) => `$${(s.net_savings / 1e6).toFixed(1)}M`, highlight: true },
                    { label: 'ROI %', fn: (s: any) => `${s.roi_pct ?? 0}%` },
                    { label: 'Payback', fn: (s: any) => s.payback_month > 0 ? `M${s.payback_month}` : 'N/A' },
                    { label: 'Trust', fn: (s: any) => `${((s.final_trust ?? 0) * 100).toFixed(0)}%` },
                    { label: 'Proficiency', fn: (s: any) => `${((s.final_proficiency ?? 0) * 100).toFixed(0)}%` },
                  ].map((row) => (
                    <tr key={row.label} className={clsx('border-b border-border/30', row.highlight && 'bg-primary/5')}>
                      <td className="py-1.5 px-3 label-caps">{row.label}</td>
                      {scenarios.map((s, i) => {
                        const summary = getSummary(s)
                        const val = row.fn(summary)
                        const allVals = scenarios.map((sc) => {
                          const v = row.fn(getSummary(sc))
                          return typeof v === 'number' ? v : parseFloat(String(v).replace(/[^0-9.-]/g, ''))
                        })
                        const isBest = row.highlight && typeof val === 'number' && val === Math.max(...allVals.filter((v) => !isNaN(v)))
                        return (
                          <td key={i} className={clsx('py-1.5 px-3 text-right font-mono', isBest && 'text-primary font-bold')}>
                            {val}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>

          {/* View Toggle */}
          <div className="flex gap-1">
            {[
              { key: 'timeline', label: 'Timeline Overlay' },
              { key: 'radar', label: 'Trade-off Radar' },
              { key: 'matrix', label: 'HC Comparison' },
            ].map((v) => (
              <button
                key={v.key}
                onClick={() => setActiveView(v.key as any)}
                className={clsx(
                  'px-4 py-2 rounded-lg text-xs font-medium transition-all',
                  activeView === v.key ? 'bg-primary/15 text-primary glow-border' : 'glass hover:bg-muted/50'
                )}
              >{v.label}</button>
            ))}
          </div>

          {activeView === 'timeline' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <GlassCard title="Headcount Trajectories" glow>
                <TimeSeriesChart
                  data={timelineData}
                  xKey="month"
                  lines={scenarios.map((s, i) => ({ dataKey: `hc_${i}`, label: s.name, color: CHART_COLORS[i] }))}
                  height={300}
                />
              </GlassCard>
              <GlassCard title="Cumulative Savings" glow>
                <TimeSeriesChart
                  data={timelineData}
                  xKey="month"
                  lines={scenarios.map((s, i) => ({ dataKey: `savings_${i}`, label: s.name, color: CHART_COLORS[i] }))}
                  height={300}
                />
              </GlassCard>
              <GlassCard title="Adoption Rate %" glow>
                <TimeSeriesChart
                  data={timelineData}
                  xKey="month"
                  lines={scenarios.map((s, i) => ({ dataKey: `adoption_${i}`, label: s.name, color: CHART_COLORS[i] }))}
                  height={300}
                />
              </GlassCard>
            </div>
          )}

          {activeView === 'radar' && (
            <GlassCard title="Multi-Dimensional Trade-off" glow>
              <div className="flex justify-center">
                <RadarChart
                  data={radarData}
                  height={400}
                  dataKeys={scenarios.map((s, i) => ({ key: `s${i}`, label: s.name, color: CHART_COLORS[i] }))}
                />
              </div>
            </GlassCard>
          )}

          {activeView === 'matrix' && (
            <GlassCard title="Headcount Reduction by Scenario" glow>
              <BarChartHorizontal
                data={hcBarData}
                bars={[{ dataKey: 'value', label: 'HC Reduced', color: 'hsl(var(--primary))' }]}
                height={Math.max(200, scenarios.length * 50)}
              />
            </GlassCard>
          )}
        </>
      )}
    </div>
  )
}
