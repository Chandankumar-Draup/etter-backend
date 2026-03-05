import { useSnapshot, useFunctions } from '../hooks/useOrganization'
import MetricCard from '../components/common/MetricCard'
import GlassCard from '../components/common/GlassCard'
import BarChartHorizontal from '../components/charts/BarChartHorizontal'
import RadarChartComponent from '../components/charts/RadarChart'
import {
  Users, DollarSign, Cpu, Target, AlertTriangle,
  Shield, Lightbulb, TrendingUp, Sparkles,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { OrgGap, FunctionGap } from '../types'

export default function Dashboard() {
  const { data: snapshot, isLoading } = useSnapshot()
  const { data: functions } = useFunctions()
  const navigate = useNavigate()

  if (isLoading || !snapshot) {
    return <LoadingState />
  }

  const snap = snapshot as OrgGap
  const atRiskRoles = snap.functions.reduce(
    (acc: number, f: FunctionGap) => acc + f.roles.filter((r) => r.redesign_candidate).length, 0
  )

  // Three-layer data for function bars
  const funcBarData = snap.functions.map((f: FunctionGap) => ({
    name: f.function,
    'Realized (L3)': Math.round(f.weighted_l3),
    'Adoption Gap': Math.round(f.weighted_l2 - f.weighted_l3),
    'Capability Gap': Math.round(f.weighted_l1 - f.weighted_l2),
    headcount: f.headcount,
  }))

  // Radar data for human readiness
  const radarData = snap.functions.map((f: FunctionGap) => ({
    subject: f.function,
    proficiency: f.ai_proficiency,
    readiness: f.change_readiness,
    trust: f.trust_level,
  }))

  // Top opportunities
  const topOpps = snap.top_roles_by_savings?.slice(0, 5) || []

  return (
    <div className="space-y-6">
      {/* KPI Grid — 4 columns */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Total Headcount"
          value={snap.headcount}
          icon={<Users className="w-[17px] h-[17px]" />}
          delay={0}
        />
        <MetricCard
          label="Annual Cost"
          value={snap.annual_cost}
          format="currency"
          icon={<DollarSign className="w-[17px] h-[17px]" />}
          delay={60}
        />
        <MetricCard
          label="Realized Automation"
          value={snap.weighted_l3}
          format="percent"
          delta={snap.weighted_l1 - snap.weighted_l3}
          deltaLabel="gap to ceiling"
          icon={<Cpu className="w-[17px] h-[17px]" />}
          delay={120}
        />
        <MetricCard
          label="Unrealized Value"
          value={snap.full_gap_savings}
          format="currency"
          icon={<Target className="w-[17px] h-[17px]" />}
          delay={180}
          colorClass="bg-warning/10 text-warning"
        />
      </div>

      {/* Second KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Adoption Gap"
          value={snap.adoption_gap_savings}
          format="currency"
          delta={snap.adoption_gap_fte}
          deltaLabel="FTEs freeable"
          icon={<Lightbulb className="w-[17px] h-[17px]" />}
          delay={240}
          colorClass="bg-chart-1/10 text-chart-1"
        />
        <MetricCard
          label="At-Risk Roles"
          value={atRiskRoles}
          icon={<AlertTriangle className="w-[17px] h-[17px]" />}
          delay={300}
          colorClass="bg-destructive/10 text-destructive"
        />
        <MetricCard
          label="Compliance Tasks"
          value={snap.compliance_tasks}
          icon={<Shield className="w-[17px] h-[17px]" />}
          delay={360}
        />
        <MetricCard
          label="Total Skills"
          value={snap.total_tasks}
          delta={snap.total_tasks - snap.compliance_tasks}
          deltaLabel="automatable"
          icon={<TrendingUp className="w-[17px] h-[17px]" />}
          delay={420}
        />
      </div>

      {/* Charts Grid — 3:2 ratio */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Function Three-Layer Analysis */}
        <GlassCard
          className="lg:col-span-3"
          title="Automation Potential by Function"
          subtitle="Three-layer gap analysis — L3 (realized) vs L2 (achievable) vs L1 (ceiling)"
          glow
          icon={<TrendingUp className="w-4 h-4" />}
        >
          <BarChartHorizontal
            data={funcBarData}
            bars={[
              { dataKey: 'Realized (L3)', label: 'Realized', color: 'hsl(160, 84%, 39%)', stackId: 'gap' },
              { dataKey: 'Adoption Gap', label: 'Adoption Gap', color: 'hsl(187, 94%, 43%)', stackId: 'gap' },
              { dataKey: 'Capability Gap', label: 'Capability Gap', color: 'hsl(265, 80%, 60%)', stackId: 'gap' },
            ]}
            height={220}
          />
          {/* Three-Layer Legend Strip */}
          <div className="grid grid-cols-4 gap-3 mt-4">
            {[
              { label: 'Realized', value: `${snap.weighted_l3.toFixed(1)}%`, color: 'border-success', desc: 'Currently automated' },
              { label: 'Adoption Gap', value: `${(snap.weighted_l2 - snap.weighted_l3).toFixed(1)}%`, color: 'border-chart-1', desc: `$${(snap.adoption_gap_savings / 1e6).toFixed(1)}M value` },
              { label: 'Capability Gap', value: `${(snap.weighted_l1 - snap.weighted_l2).toFixed(1)}%`, color: 'border-accent', desc: 'Needs new tools' },
              { label: 'Human Essential', value: `${(100 - snap.weighted_l1).toFixed(1)}%`, color: 'border-muted-foreground', desc: 'Non-automatable' },
            ].map((item) => (
              <div key={item.label} className={`border-t-2 ${item.color} pt-2`}>
                <div className="label-caps">{item.label}</div>
                <div className="text-lg font-bold font-mono mt-0.5">{item.value}</div>
                <div className="text-[10px] text-muted-foreground">{item.desc}</div>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* Capability Radar */}
        <GlassCard
          className="lg:col-span-2"
          title="Transformation Readiness"
          subtitle="AI proficiency, change readiness, and trust by function"
          icon={<Sparkles className="w-4 h-4" />}
        >
          <RadarChartComponent
            data={radarData}
            dataKeys={[
              { key: 'proficiency', label: 'AI Proficiency', color: 'hsl(187, 94%, 43%)' },
              { key: 'readiness', label: 'Readiness', color: 'hsl(265, 80%, 60%)' },
              { key: 'trust', label: 'Trust', color: 'hsl(160, 84%, 39%)' },
            ]}
            height={260}
          />
        </GlassCard>
      </div>

      {/* Bottom Grid — Function Overview + Top Opportunities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Function Overview */}
        <GlassCard title="Function Overview" icon={<Users className="w-4 h-4" />}>
          <div className="space-y-3">
            {snap.functions.map((f: FunctionGap, i: number) => {
              const riskRoles = f.roles.filter((r) => r.redesign_candidate).length
              return (
                <button
                  key={f.function}
                  className="w-full flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors text-left"
                  onClick={() => navigate(`/explorer?function=${f.function}`)}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-8 rounded-full`}
                      style={{ backgroundColor: ['hsl(187,94%,43%)', 'hsl(265,80%,60%)', 'hsl(38,92%,50%)', 'hsl(160,84%,39%)'][i % 4] }}
                    />
                    <div>
                      <div className="text-sm font-medium">{f.function}</div>
                      <div className="text-xs text-muted-foreground">
                        {f.headcount} HC &middot; {f.roles.length} roles
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-sm font-mono font-medium">${(f.full_gap_savings / 1e6).toFixed(1)}M</div>
                      <div className="text-[10px] text-muted-foreground">gap savings</div>
                    </div>
                    {riskRoles > 0 && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-destructive/10 text-destructive border border-destructive/30">
                        {riskRoles} at-risk
                      </span>
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </GlassCard>

        {/* Top Savings Opportunities */}
        <GlassCard title="Top Savings Opportunities" subtitle="Ranked by full gap savings potential" icon={<DollarSign className="w-4 h-4" />}>
          <div className="space-y-2">
            {topOpps.map((opp: any, i: number) => {
              const maxSavings = topOpps[0]?.full_savings || 1
              const pct = (Number(opp.full_savings) / Number(maxSavings)) * 100
              return (
                <div key={opp.role_id || i} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-4 font-mono">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium truncate">{opp.role_name}</span>
                      <span className="text-xs font-mono text-primary">${(opp.full_savings / 1e6).toFixed(2)}M</span>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                        style={{ width: `${pct}%`, transition: 'width 0.8s ease-out' }}
                      />
                    </div>
                    <div className="flex justify-between mt-0.5">
                      <span className="text-[10px] text-muted-foreground">{opp.function}</span>
                      <span className="text-[10px] text-muted-foreground">{opp.headcount} HC</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </GlassCard>
      </div>

      {/* AI Insight Strip */}
      <div
        className="glass p-5 border-l-[3px] border-l-accent"
        style={{ background: 'linear-gradient(135deg, hsl(var(--card)) 0%, hsl(var(--accent) / 0.06) 100%)' }}
      >
        <div className="flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm">
              <span className="text-foreground font-medium">Insight:</span>{' '}
              <span className="text-muted-foreground">
                The <span className="text-primary font-medium">adoption gap</span> of ${(snap.adoption_gap_savings / 1e6).toFixed(1)}M
                represents deployed tools that are underutilized. This is{' '}
                <span className="text-warning font-medium">"free money"</span> — no new procurement needed,
                just better adoption of existing technology.
              </span>
            </p>
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => navigate('/explorer')}
                className="text-xs px-3 py-1.5 rounded-lg border border-accent/30 text-accent hover:bg-accent/10 transition-colors"
              >
                Explore Gaps
              </button>
              <button
                onClick={() => navigate('/simulation')}
                className="text-xs px-3 py-1.5 rounded-lg border border-primary/30 text-primary hover:bg-primary/10 transition-colors"
              >
                Run Simulation
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="glass p-5 animate-pulse">
            <div className="h-3 w-20 bg-muted rounded mb-3" />
            <div className="h-8 w-24 bg-muted rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}
