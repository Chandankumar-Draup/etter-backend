import { useState } from 'react'
import { useSnapshot, useRoleDetail } from '../hooks/useOrganization'
import GlassCard from '../components/common/GlassCard'
import MetricCard from '../components/common/MetricCard'
import BarChartHorizontal from '../components/charts/BarChartHorizontal'
import { ChevronRight, ChevronDown, Search, Users, Layers, Briefcase } from 'lucide-react'
import { clsx } from 'clsx'
import { FunctionGap, RoleGap } from '../types'

export default function Explorer() {
  const { data: snapshot, isLoading } = useSnapshot()
  const [selectedFunction, setSelectedFunction] = useState<string | null>(null)
  const [selectedRole, setSelectedRole] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const { data: roleDetail } = useRoleDetail(selectedRole)

  if (isLoading || !snapshot) {
    return <div className="animate-pulse space-y-4">{[...Array(3)].map((_, i) => <div key={i} className="glass h-20" />)}</div>
  }

  const functions: FunctionGap[] = snapshot.functions
  const selectedFunc = functions.find((f) => f.function === selectedFunction)

  const filteredRoles = selectedFunc?.roles.filter(
    (r: RoleGap) => !searchQuery || r.role_name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Left Panel: Hierarchy Tree */}
      <div className="lg:col-span-4 space-y-4">
        {/* Search */}
        <div className="glass p-3">
          <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 rounded-lg">
            <Search className="w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search roles..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none flex-1"
            />
          </div>
        </div>

        {/* Function Tree */}
        <GlassCard title="Organization Hierarchy" icon={<Layers className="w-4 h-4" />}>
          <div className="space-y-1 max-h-[calc(100vh-280px)] overflow-y-auto custom-scrollbar">
            {functions.map((func) => (
              <div key={func.function}>
                <button
                  onClick={() => {
                    setSelectedFunction(selectedFunction === func.function ? null : func.function)
                    setSelectedRole(null)
                  }}
                  className={clsx(
                    'w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm transition-colors text-left',
                    selectedFunction === func.function
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-muted text-foreground'
                  )}
                >
                  {selectedFunction === func.function
                    ? <ChevronDown className="w-4 h-4 flex-shrink-0" />
                    : <ChevronRight className="w-4 h-4 flex-shrink-0" />}
                  <Users className="w-3.5 h-3.5 flex-shrink-0 text-muted-foreground" />
                  <span className="flex-1 truncate">{func.function}</span>
                  <span className="text-xs text-muted-foreground font-mono">{func.headcount}</span>
                </button>

                {selectedFunction === func.function && (
                  <div className="ml-6 mt-1 space-y-0.5">
                    {filteredRoles.map((role: RoleGap) => (
                      <button
                        key={role.role_id}
                        onClick={() => setSelectedRole(role.role_id)}
                        className={clsx(
                          'w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-colors text-left',
                          selectedRole === role.role_id
                            ? 'bg-accent/10 text-accent glow-border'
                            : 'hover:bg-muted/50 text-muted-foreground'
                        )}
                      >
                        <Briefcase className="w-3 h-3 flex-shrink-0" />
                        <span className="flex-1 truncate">{role.role_name}</span>
                        <span className="font-mono">{role.headcount}</span>
                        {role.redesign_candidate && (
                          <span className="w-1.5 h-1.5 rounded-full bg-destructive" title="Redesign candidate" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* Right Panel: Detail View */}
      <div className="lg:col-span-8 space-y-4">
        {!selectedFunction && (
          <GlassCard className="text-center py-16">
            <Layers className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">Select a function to explore its roles and gap analysis</p>
          </GlassCard>
        )}

        {selectedFunc && !selectedRole && (
          <FunctionDetail func={selectedFunc} />
        )}

        {selectedRole && roleDetail && (
          <RoleDetail role={roleDetail} />
        )}
      </div>
    </div>
  )
}

function FunctionDetail({ func }: { func: FunctionGap }) {
  const roleBarData = func.roles.map((r: RoleGap) => ({
    name: r.role_name.length > 25 ? r.role_name.slice(0, 25) + '...' : r.role_name,
    'Realized': Math.round(r.weighted_l3),
    'Gap': Math.round(r.weighted_l1 - r.weighted_l3),
  }))

  return (
    <div className="space-y-4">
      {/* Function KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Headcount" value={func.headcount} delay={0} />
        <MetricCard label="Annual Cost" value={func.annual_cost} format="currency" delay={60} />
        <MetricCard label="Adoption Gap Savings" value={func.adoption_gap_savings} format="currency" delay={120} />
        <MetricCard label="Full Gap Savings" value={func.full_gap_savings} format="currency" delay={180} />
      </div>

      {/* Three-Layer Chart */}
      <GlassCard title={`${func.function} — Role Automation Potential`} glow>
        <BarChartHorizontal
          data={roleBarData}
          bars={[
            { dataKey: 'Realized', label: 'Realized (L3)', color: 'hsl(160, 84%, 39%)', stackId: 'gap' },
            { dataKey: 'Gap', label: 'Unrealized Gap', color: 'hsl(187, 94%, 43%)', stackId: 'gap' },
          ]}
          height={Math.max(200, func.roles.length * 35)}
        />
      </GlassCard>

      {/* Roles Table */}
      <GlassCard title="Roles" subtitle={`${func.roles.length} roles in ${func.function}`}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-2 label-caps">Role</th>
                <th className="text-right py-2 px-2 label-caps">HC</th>
                <th className="text-right py-2 px-2 label-caps">L1</th>
                <th className="text-right py-2 px-2 label-caps">L3</th>
                <th className="text-right py-2 px-2 label-caps">Gap Savings</th>
                <th className="text-right py-2 px-2 label-caps">Status</th>
              </tr>
            </thead>
            <tbody>
              {func.roles.map((r: RoleGap) => (
                <tr key={r.role_id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="py-2 px-2 font-medium">{r.role_name}</td>
                  <td className="text-right py-2 px-2 font-mono">{r.headcount}</td>
                  <td className="text-right py-2 px-2 font-mono text-accent">{r.weighted_l1.toFixed(1)}%</td>
                  <td className="text-right py-2 px-2 font-mono text-success">{r.weighted_l3.toFixed(1)}%</td>
                  <td className="text-right py-2 px-2 font-mono text-primary">
                    ${(r.full_gap_savings / 1e6).toFixed(2)}M
                  </td>
                  <td className="text-right py-2 px-2">
                    {r.redesign_candidate ? (
                      <span className="px-2 py-0.5 rounded-full bg-destructive/10 text-destructive border border-destructive/30 text-[10px]">
                        Redesign
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full bg-success/10 text-success border border-success/30 text-[10px]">
                        Stable
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  )
}

function RoleDetail({ role }: { role: any }) {
  const [activeTab, setActiveTab] = useState<'overview' | 'tasks' | 'skills'>('overview')
  const tabs = [
    { id: 'overview' as const, label: 'Overview' },
    { id: 'tasks' as const, label: 'Tasks' },
    { id: 'skills' as const, label: 'Skills' },
  ]

  return (
    <div className="space-y-4">
      <GlassCard>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold">{role.role_name}</h2>
            <p className="text-xs text-muted-foreground">
              {role.function} &middot; {role.management_level} &middot; {role.headcount} HC
            </p>
          </div>
          <span className="text-xs font-mono text-primary">{role.role_id}</span>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 border-b border-border">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'overview' && (
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-muted/30 rounded-lg">
              <div className="label-caps mb-1">Automation Score</div>
              <div className="text-xl font-bold font-mono text-primary">{role.automation_score}%</div>
            </div>
            <div className="p-3 bg-muted/30 rounded-lg">
              <div className="label-caps mb-1">Augmentation Score</div>
              <div className="text-xl font-bold font-mono text-accent">{role.augmentation_score}%</div>
            </div>
            <div className="p-3 bg-muted/30 rounded-lg">
              <div className="label-caps mb-1">Avg Salary</div>
              <div className="text-xl font-bold font-mono">${(role.avg_salary / 1000).toFixed(0)}K</div>
            </div>
            <div className="p-3 bg-muted/30 rounded-lg">
              <div className="label-caps mb-1">Annual Cost</div>
              <div className="text-xl font-bold font-mono">${(role.annual_cost / 1e6).toFixed(1)}M</div>
            </div>
          </div>
        )}

        {activeTab === 'tasks' && role.workloads && (
          <div className="space-y-4 max-h-[500px] overflow-y-auto custom-scrollbar">
            {role.workloads.map((wl: any) => (
              <div key={wl.workload_id}>
                <div className="text-xs font-medium mb-2">{wl.workload_name} ({wl.time_pct}%)</div>
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-border/50">
                      <th className="text-left py-1 px-1">Task</th>
                      <th className="text-right py-1 px-1">Category</th>
                      <th className="text-right py-1 px-1">Hrs/mo</th>
                      <th className="text-right py-1 px-1">L1</th>
                      <th className="text-right py-1 px-1">L3</th>
                    </tr>
                  </thead>
                  <tbody>
                    {wl.tasks.map((t: any) => (
                      <tr key={t.task_id} className="border-b border-border/30">
                        <td className="py-1.5 px-1">{t.task_name}</td>
                        <td className="text-right py-1.5 px-1">
                          <span className={clsx(
                            'px-1.5 py-0.5 rounded text-[10px]',
                            t.category === 'directive' ? 'bg-chart-1/20 text-chart-1' :
                            t.category === 'feedback_loop' ? 'bg-chart-2/20 text-chart-2' :
                            t.category === 'negligibility' ? 'bg-muted text-muted-foreground' :
                            'bg-chart-4/20 text-chart-4'
                          )}>{t.category}</span>
                        </td>
                        <td className="text-right py-1.5 px-1 font-mono">{t.effort_hours.toFixed(1)}</td>
                        <td className="text-right py-1.5 px-1 font-mono text-accent">{t.l1.toFixed(0)}%</td>
                        <td className="text-right py-1.5 px-1 font-mono text-success">{t.l3.toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'skills' && role.workloads && (
          <div className="space-y-2 max-h-[500px] overflow-y-auto custom-scrollbar">
            {role.workloads.flatMap((wl: any) => wl.skills || []).map((s: any) => (
              <div key={s.skill_id} className="flex items-center justify-between p-2 bg-muted/20 rounded-lg">
                <div>
                  <span className="text-xs font-medium">{s.skill_name}</span>
                  <div className="text-[10px] text-muted-foreground">
                    Proficiency required: {s.proficiency_required}
                  </div>
                </div>
                <div className="flex gap-1">
                  {s.is_sunrise && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-success/10 text-success border border-success/30">sunrise</span>
                  )}
                  {s.is_sunset && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-destructive/10 text-destructive border border-destructive/30">sunset</span>
                  )}
                  {!s.is_sunrise && !s.is_sunset && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">current</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  )
}
