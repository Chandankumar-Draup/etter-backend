import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts'

interface BarChartHorizontalProps {
  data: { name: string; [key: string]: unknown }[]
  bars: { dataKey: string; label: string; color: string; stackId?: string }[]
  height?: number
}

const TOOLTIP_STYLE = {
  backgroundColor: 'hsl(222, 47%, 9%)',
  border: '1px solid hsl(222, 30%, 16%)',
  borderRadius: '8px',
  fontSize: '12px',
}

export default function BarChartHorizontal({ data, bars, height = 300 }: BarChartHorizontalProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(222, 30%, 16%)" horizontal={false} />
        <XAxis type="number" tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 10 }} />
        <YAxis
          dataKey="name"
          type="category"
          tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 11 }}
          width={130}
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: '11px' }} />
        {bars.map((bar) => (
          <Bar
            key={bar.dataKey}
            dataKey={bar.dataKey}
            name={bar.label}
            fill={bar.color}
            stackId={bar.stackId}
            radius={bar.stackId ? undefined : [0, 4, 4, 0] as any}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
