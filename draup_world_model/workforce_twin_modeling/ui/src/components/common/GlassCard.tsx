import { clsx } from 'clsx'
import { ReactNode } from 'react'

interface GlassCardProps {
  children: ReactNode
  className?: string
  glow?: boolean
  title?: string
  subtitle?: string
  icon?: ReactNode
  delay?: number
}

export default function GlassCard({
  children, className, glow, title, subtitle, icon, delay = 0,
}: GlassCardProps) {
  return (
    <div
      className={clsx(
        'glass p-5 animate-fade-in',
        glow && 'glow-border',
        className,
      )}
      style={{ animationDelay: `${delay}ms` }}
    >
      {(title || icon) && (
        <div className="flex items-start justify-between mb-4">
          <div>
            {title && <h3 className="section-header">{title}</h3>}
            {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
          </div>
          {icon && <div className="text-primary">{icon}</div>}
        </div>
      )}
      {children}
    </div>
  )
}
