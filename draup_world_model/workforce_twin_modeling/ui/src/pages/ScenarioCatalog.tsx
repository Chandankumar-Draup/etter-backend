import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import GlassCard from '../components/common/GlassCard'
import MetricCard from '../components/common/MetricCard'
import { BookOpen, Play, Filter, CheckSquare, Square, ChevronDown, ChevronUp } from 'lucide-react'
import { clsx } from 'clsx'

interface CatalogScenario {
  scenario_id: string
  scenario_name: string
  scenario_family: string
  direction: string
  tools: string
  target_functions: string
  hc_policy: string
  alpha_adopt: string
  time_horizon_months: string
}

interface ScenarioRunResult {
  scenario_id: string
  scenario_name: string
  family: string
  status: string
  error?: string
  hc_reduced: number
  final_hc: number
  net_savings: number
  total_investment: number
  total_savings: number
  payback_month: number
  final_proficiency: number
  final_trust: number
}

export default function ScenarioCatalog() {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [familyFilter, setFamilyFilter] = useState<string>('all')
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<string>('scenario_id')
  const [sortAsc, setSortAsc] = useState(true)

  const { data: catalog, isLoading, isError, error } = useQuery({
    queryKey: ['catalog'],
    queryFn: () => api.catalog(),
  })

  const runBatch = useMutation({
    mutationFn: (ids: string[]) => api.runScenarios(ids),
  })

  const scenarios = (Array.isArray(catalog) ? catalog : catalog?.scenarios ?? []) as CatalogScenario[]
  const families = [...new Set(scenarios.map((s) => s.scenario_family))].sort()

  const filtered = familyFilter === 'all'
    ? scenarios
    : scenarios.filter((s) => s.scenario_family === familyFilter)

  const sorted = [...filtered].sort((a, b) => {
    const aVal = (a as any)[sortKey] ?? ''
    const bVal = (b as any)[sortKey] ?? ''
    const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true })
    return sortAsc ? cmp : -cmp
  })

  const toggleSelect = (id: string) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedIds(next)
  }

  const toggleAll = () => {
    if (selectedIds.size === filtered.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(filtered.map((s) => s.scenario_id)))
  }

  const handleSort = (key: string) => {
    if (sortKey === key) setSortAsc(!sortAsc)
    else { setSortKey(key); setSortAsc(true) }
  }

  const handleRunSelected = () => {
    if (selectedIds.size === 0) return
    runBatch.mutate([...selectedIds])
  }

  const batchData = runBatch.data as any
  const results = (Array.isArray(batchData) ? batchData : batchData?.results ?? []) as ScenarioRunResult[]
  const resultMap = new Map(results.map((r) => [r.scenario_id, r]))

  const SortIcon = ({ col }: { col: string }) => {
    if (sortKey !== col) return null
    return sortAsc ? <ChevronUp className="w-3 h-3 inline" /> : <ChevronDown className="w-3 h-3 inline" />
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="glass p-8 text-center">
          <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Loading catalog...</p>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="glass p-8 text-center max-w-md">
          <BookOpen className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-foreground mb-2">Backend Unavailable</h3>
          <p className="text-sm text-muted-foreground">
            Could not connect to the API server. Make sure the backend is running on port 8000.
          </p>
          <p className="text-xs text-muted-foreground/60 mt-2 font-mono">
            {(error as Error)?.message}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <GlassCard title="Scenario Catalog" subtitle="40 pre-configured simulation scenarios" icon={<BookOpen className="w-4 h-4" />}>
        <div className="flex flex-wrap items-center gap-3">
          {/* Family Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-muted-foreground" />
            <select
              value={familyFilter}
              onChange={(e) => setFamilyFilter(e.target.value)}
              className="text-xs bg-muted border border-border rounded-lg px-3 py-1.5 text-foreground"
            >
              <option value="all">All Families ({scenarios.length})</option>
              {families.map((f) => (
                <option key={f} value={f}>{f} ({scenarios.filter((s) => s.scenario_family === f).length})</option>
              ))}
            </select>
          </div>

          <div className="flex-1" />

          <span className="text-xs text-muted-foreground">{selectedIds.size} selected</span>

          <button
            onClick={handleRunSelected}
            disabled={selectedIds.size === 0 || runBatch.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            <Play className="w-3.5 h-3.5" />
            {runBatch.isPending ? 'Running...' : `Run ${selectedIds.size} Scenario${selectedIds.size !== 1 ? 's' : ''}`}
          </button>
        </div>
      </GlassCard>

      {/* Results Summary */}
      {results.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <MetricCard label="Executed" value={results.length} delay={0} />
          <MetricCard label="Passed" value={results.filter((r) => r.status === 'pass').length} delay={60} />
          <MetricCard label="Failed" value={results.filter((r) => r.status === 'fail').length} delay={120} />
          <MetricCard label="Avg HC Reduced" value={Math.round(results.filter((r) => r.status === 'pass').reduce((s, r) => s + r.hc_reduced, 0) / Math.max(1, results.filter((r) => r.status === 'pass').length))} delay={180} />
          <MetricCard label="Avg Net Savings" value={results.filter((r) => r.status === 'pass').reduce((s, r) => s + r.net_savings, 0) / Math.max(1, results.filter((r) => r.status === 'pass').length)} format="currency" delay={240} />
        </div>
      )}

      {/* Catalog Table */}
      <GlassCard>
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-2 w-8">
                  <button onClick={toggleAll} className="text-muted-foreground hover:text-foreground">
                    {selectedIds.size === filtered.length && filtered.length > 0
                      ? <CheckSquare className="w-3.5 h-3.5" />
                      : <Square className="w-3.5 h-3.5" />}
                  </button>
                </th>
                {[
                  { key: 'scenario_id', label: 'ID' },
                  { key: 'scenario_name', label: 'Name' },
                  { key: 'scenario_family', label: 'Family' },
                  { key: 'direction', label: 'Dir' },
                  { key: 'tools', label: 'Tools' },
                  { key: 'hc_policy', label: 'Policy' },
                  { key: 'alpha_adopt', label: 'α' },
                  { key: 'time_horizon_months', label: 'Horizon' },
                ].map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="text-left py-2 px-2 cursor-pointer hover:text-primary select-none whitespace-nowrap"
                  >
                    {col.label} <SortIcon col={col.key} />
                  </th>
                ))}
                {results.length > 0 && (
                  <>
                    <th className="text-right py-2 px-2">HC↓</th>
                    <th className="text-right py-2 px-2">Net $M</th>
                    <th className="text-right py-2 px-2">Status</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {sorted.map((s) => {
                const r = resultMap.get(s.scenario_id)
                return (
                  <tr
                    key={s.scenario_id}
                    onClick={() => setExpandedRow(expandedRow === s.scenario_id ? null : s.scenario_id)}
                    className={clsx(
                      'border-b border-border/30 cursor-pointer transition-colors',
                      selectedIds.has(s.scenario_id) ? 'bg-primary/5' : 'hover:bg-muted/30',
                      r?.status === 'fail' && 'bg-destructive/5'
                    )}
                  >
                    <td className="py-1.5 px-2" onClick={(e) => { e.stopPropagation(); toggleSelect(s.scenario_id) }}>
                      {selectedIds.has(s.scenario_id)
                        ? <CheckSquare className="w-3.5 h-3.5 text-primary" />
                        : <Square className="w-3.5 h-3.5 text-muted-foreground" />}
                    </td>
                    <td className="py-1.5 px-2 font-mono text-primary">{s.scenario_id}</td>
                    <td className="py-1.5 px-2 font-medium max-w-[200px] truncate">{s.scenario_name}</td>
                    <td className="py-1.5 px-2">
                      <span className="px-1.5 py-0.5 rounded bg-muted text-[10px]">{s.scenario_family}</span>
                    </td>
                    <td className="py-1.5 px-2">{s.direction}</td>
                    <td className="py-1.5 px-2 max-w-[120px] truncate">{s.tools}</td>
                    <td className="py-1.5 px-2">{s.hc_policy}</td>
                    <td className="py-1.5 px-2 font-mono">{s.alpha_adopt}</td>
                    <td className="py-1.5 px-2 font-mono">{s.time_horizon_months}mo</td>
                    {results.length > 0 && (
                      <>
                        <td className="py-1.5 px-2 text-right font-mono">{r ? r.hc_reduced : '—'}</td>
                        <td className="py-1.5 px-2 text-right font-mono">{r ? `${(r.net_savings / 1e6).toFixed(1)}` : '—'}</td>
                        <td className="py-1.5 px-2 text-right">
                          {r && (
                            <span className={clsx(
                              'px-1.5 py-0.5 rounded text-[10px] font-medium',
                              r.status === 'pass' ? 'bg-success/15 text-success' : 'bg-destructive/15 text-destructive'
                            )}>{r.status}</span>
                          )}
                        </td>
                      </>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  )
}
