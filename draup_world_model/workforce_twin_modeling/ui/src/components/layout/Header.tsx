import { Sun, Moon, Activity } from 'lucide-react'

interface HeaderProps {
  title: string
  subtitle?: string
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}

export default function Header({ title, subtitle, theme, onToggleTheme }: HeaderProps) {
  return (
    <header className="flex items-center justify-between h-14 px-6 border-b border-border bg-card/40 backdrop-blur-xl">
      <div>
        <h1 className="text-base font-bold text-foreground">{title}</h1>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-4">
        {/* Live indicator */}
        <div className="flex items-center gap-1.5 text-xs text-success">
          <Activity className="w-3.5 h-3.5 animate-pulse" />
          <span className="font-medium">LIVE</span>
        </div>
        {/* Theme toggle */}
        <button
          onClick={onToggleTheme}
          className="flex items-center justify-center w-8 h-8 rounded-lg bg-muted hover:bg-muted/80 transition-colors"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-muted-foreground" />
          ) : (
            <Moon className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
      </div>
    </header>
  )
}
