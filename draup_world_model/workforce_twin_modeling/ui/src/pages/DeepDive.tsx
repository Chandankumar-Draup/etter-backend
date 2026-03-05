import { useState } from 'react'
import { GitCompare, GitBranch, BarChart3 } from 'lucide-react'
import { clsx } from 'clsx'
import CompareArena from './CompareArena'
import CascadeExplorer from './CascadeExplorer'
import ScenarioCatalog from './ScenarioCatalog'

const TABS = [
  { id: 'compare', label: 'Compare', icon: GitCompare, desc: 'Side-by-side scenario analysis' },
  { id: 'cascade', label: 'Cascade', icon: GitBranch, desc: '9-step impact engine' },
  { id: 'scenarios', label: 'Scenarios', icon: BarChart3, desc: 'Pre-built scenario catalog' },
] as const

type TabId = typeof TABS[number]['id']

export default function DeepDive() {
  const [activeTab, setActiveTab] = useState<TabId>('compare')

  return (
    <div className="space-y-5">
      {/* Tab Selector */}
      <div className="flex items-center gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm transition-all duration-200 border',
              activeTab === tab.id
                ? 'bg-primary/10 text-primary border-primary/30 glow-border'
                : 'bg-muted/20 text-muted-foreground border-border/30 hover:bg-muted/40 hover:text-foreground'
            )}
          >
            <tab.icon className="w-4 h-4" />
            <span className="font-medium">{tab.label}</span>
            <span className="hidden sm:inline text-[10px] text-muted-foreground/60 ml-1">{tab.desc}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'compare' && <CompareArena />}
        {activeTab === 'cascade' && <CascadeExplorer />}
        {activeTab === 'scenarios' && <ScenarioCatalog />}
      </div>
    </div>
  )
}
