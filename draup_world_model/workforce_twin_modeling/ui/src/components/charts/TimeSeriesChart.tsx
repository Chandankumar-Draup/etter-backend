import {
  ResponsiveContainer, ComposedChart, Line, Area, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts'

interface LineConfig {
  dataKey: string
  label: string
  color: string
  type?: 'line' | 'area' | 'bar'
  dashed?: boolean
  opacity?: number
}

interface TimeSeriesChartProps {
  data: Record<string, unknown>[]
  lines: LineConfig[]
  xKey?: string
  xLabel?: string
  yLabel?: string
  height?: number
  referenceLines?: { x?: number | string; y?: number; label: string; color?: string }[]
  onClick?: (data: Record<string, unknown>) => void
}

const TOOLTIP_STYLE = {
  backgroundColor: 'hsl(222, 47%, 9%)',
  border: '1px solid hsl(222, 30%, 16%)',
  borderRadius: '8px',
  padding: '12px 16px',
  fontSize: '12px',
  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
}

export default function TimeSeriesChart({
  data, lines, xKey = 'month', xLabel, yLabel, height = 300,
  referenceLines = [], onClick,
}: TimeSeriesChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} onClick={onClick ? (e: any) => e?.activePayload && onClick(e.activePayload[0]?.payload) : undefined}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(222, 30%, 16%)" />
        <XAxis
          dataKey={xKey}
          tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 11 }}
          label={xLabel ? { value: xLabel, position: 'insideBottom', fill: 'hsl(215, 20%, 55%)', fontSize: 11 } : undefined}
        />
        <YAxis
          tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 11 }}
          label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fill: 'hsl(215, 20%, 55%)', fontSize: 11 } : undefined}
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend
          wrapperStyle={{ fontSize: '11px', fontFamily: 'JetBrains Mono, monospace' }}
        />
        {referenceLines.map((rl, i) => (
          <ReferenceLine
            key={i}
            x={rl.x} y={rl.y}
            stroke={rl.color || 'hsl(38, 92%, 50%)'}
            strokeDasharray="5 5"
            label={{ value: rl.label, fill: 'hsl(215, 20%, 55%)', fontSize: 10 }}
          />
        ))}
        {lines.map((line) => {
          if (line.type === 'area') {
            return (
              <Area
                key={line.dataKey}
                type="monotone"
                dataKey={line.dataKey}
                name={line.label}
                stroke={line.color}
                fill={line.color}
                fillOpacity={line.opacity ?? 0.15}
                strokeWidth={2}
                strokeDasharray={line.dashed ? '8 4' : undefined}
              />
            )
          }
          if (line.type === 'bar') {
            return (
              <Bar
                key={line.dataKey}
                dataKey={line.dataKey}
                name={line.label}
                fill={line.color}
                opacity={line.opacity ?? 0.85}
                radius={[4, 4, 0, 0] as any}
              />
            )
          }
          return (
            <Line
              key={line.dataKey}
              type="monotone"
              dataKey={line.dataKey}
              name={line.label}
              stroke={line.color}
              strokeWidth={2}
              dot={false}
              strokeDasharray={line.dashed ? '8 4' : undefined}
            />
          )
        })}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
