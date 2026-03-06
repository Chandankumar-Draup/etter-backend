import {
  ResponsiveContainer, RadarChart as RChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis, Legend,
} from 'recharts'

interface RadarChartProps {
  data: { subject: string; [key: string]: unknown }[]
  dataKeys: { key: string; label: string; color: string; fill?: boolean }[]
  height?: number
}

export default function RadarChartComponent({ data, dataKeys, height = 300 }: RadarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RChart data={data}>
        <PolarGrid stroke="hsl(222, 30%, 16%)" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 10 }}
        />
        <PolarRadiusAxis tick={{ fill: 'hsl(215, 20%, 55%)', fontSize: 9 }} />
        {dataKeys.map((dk) => (
          <Radar
            key={dk.key}
            name={dk.label}
            dataKey={dk.key}
            stroke={dk.color}
            fill={dk.fill !== false ? dk.color : 'none'}
            fillOpacity={dk.fill !== false ? 0.2 : 0}
            strokeWidth={2}
          />
        ))}
        <Legend wrapperStyle={{ fontSize: '11px' }} />
      </RChart>
    </ResponsiveContainer>
  )
}
