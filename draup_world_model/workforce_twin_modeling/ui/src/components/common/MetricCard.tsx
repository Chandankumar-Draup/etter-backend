import { ReactNode, useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'

interface MetricCardProps {
  label: string
  value: number | string
  format?: 'number' | 'currency' | 'percent' | 'string'
  delta?: number
  deltaLabel?: string
  icon?: ReactNode
  delay?: number
  colorClass?: string
}

function formatValue(value: number | string, format: string): string {
  if (typeof value === 'string') return value
  switch (format) {
    case 'currency':
      if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
      if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`
      return `$${value.toFixed(0)}`
    case 'percent':
      return `${value.toFixed(1)}%`
    default:
      return value.toLocaleString()
  }
}

export default function MetricCard({
  label, value, format = 'number', delta, deltaLabel, icon, delay = 0, colorClass,
}: MetricCardProps) {
  const [displayValue, setDisplayValue] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const animated = useRef(false)

  useEffect(() => {
    if (typeof value !== 'number' || animated.current) {
      setDisplayValue(typeof value === 'number' ? value : 0)
      return
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !animated.current) {
        animated.current = true
        const duration = 1200
        const start = performance.now()
        const animate = (now: number) => {
          const t = Math.min((now - start) / duration, 1)
          const eased = 1 - Math.pow(1 - t, 4) // easeOutQuart
          setDisplayValue(Math.round(value * eased * 10) / 10)
          if (t < 1) requestAnimationFrame(animate)
          else setDisplayValue(value)
        }
        requestAnimationFrame(animate)
      }
    })
    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [value])

  return (
    <div
      ref={ref}
      className="glass p-5 animate-fade-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between">
        <span className="label-caps">{label}</span>
        {icon && (
          <div className={clsx(
            'flex items-center justify-center w-9 h-9 rounded-lg',
            colorClass || 'bg-primary/10 text-primary'
          )}>
            {icon}
          </div>
        )}
      </div>
      <div className="mt-2">
        <span className="stat-value">
          {typeof value === 'string' ? value : formatValue(displayValue, format)}
        </span>
      </div>
      {delta !== undefined && (
        <div className="mt-1.5 flex items-center gap-1">
          <span className={clsx(
            'text-xs font-medium',
            delta > 0 ? 'text-success' : delta < 0 ? 'text-destructive' : 'text-muted-foreground'
          )}>
            {delta > 0 ? '+' : ''}{typeof delta === 'number' && format === 'currency'
              ? formatValue(delta, 'currency')
              : format === 'percent'
                ? `${delta.toFixed(1)}%`
                : delta.toLocaleString()}
          </span>
          {deltaLabel && <span className="text-[10px] text-muted-foreground">{deltaLabel}</span>}
        </div>
      )}
    </div>
  )
}
