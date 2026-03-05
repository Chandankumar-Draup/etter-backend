import { NavLink } from 'react-router-dom'
import { useState } from 'react'
import {
  LayoutDashboard, Search, FlaskConical, Sparkles,
  Layers, ChevronLeft, ChevronRight, Zap,
} from 'lucide-react'
import { clsx } from 'clsx'

const NAV_MAIN = [
  { to: '/', icon: LayoutDashboard, label: 'Pulse' },
  { to: '/explorer', icon: Search, label: 'Explorer' },
  { to: '/simulation', icon: FlaskConical, label: 'Simulation' },
  { to: '/nova', icon: Sparkles, label: 'Nova' },
]

const NAV_ADVANCED = [
  { to: '/deep-dive', icon: Layers, label: 'Deep Dive' },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={clsx(
        'h-screen sticky top-0 flex flex-col border-r border-border bg-card/80 backdrop-blur-xl transition-all duration-300',
        collapsed ? 'w-[58px]' : 'w-[220px]'
      )}
    >
      {/* Brand */}
      <div className="flex items-center gap-2 px-4 h-14 border-b border-border">
        <Zap className="w-5 h-5 text-primary flex-shrink-0" />
        {!collapsed && (
          <span className="text-sm font-bold gradient-text whitespace-nowrap">
            Workforce Twin
          </span>
        )}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 py-3 px-2 flex flex-col">
        <div className="space-y-1">
          {NAV_MAIN.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary glow-border'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )
              }
            >
              <Icon className="w-[18px] h-[18px] flex-shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </NavLink>
          ))}
        </div>

        {/* Separator */}
        <div className="my-4 mx-3 border-t border-border/40" />

        {/* Advanced Section */}
        {!collapsed && (
          <div className="px-3 mb-2">
            <span className="text-[9px] font-medium uppercase tracking-widest text-muted-foreground/50">Advanced</span>
          </div>
        )}
        <div className="space-y-1">
          {NAV_ADVANCED.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-primary/10 text-primary glow-border'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )
              }
            >
              <Icon className="w-[18px] h-[18px] flex-shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-t border-border text-muted-foreground hover:text-foreground transition-colors"
      >
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </aside>
  )
}
