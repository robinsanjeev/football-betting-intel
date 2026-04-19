import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  BarChart,
  Bar,
  Cell,
} from 'recharts'
import type { Performance } from '../types'

interface CumulativePnlChartProps {
  data: Performance['cumulative_pnl']
}

interface WinLossChartProps {
  counts: Performance['win_loss_counts']
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { value: number; color: string }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  const val = payload[0].value
  return (
    <div className="bg-[#16162a] border border-[#1e1e3a] rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="text-[#a0a0c0] mb-1">{label}</div>
      <div className={`font-mono font-semibold ${val >= 0 ? 'text-[#3ddc84]' : 'text-[#e84040]'}`}>
        {val >= 0 ? '+' : ''}${val.toFixed(2)}
      </div>
    </div>
  )
}

export function CumulativePnlChart({ data }: CumulativePnlChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="card p-6 flex items-center justify-center h-64">
        <p className="text-[#6b6b8a] text-sm">No PnL data yet</p>
      </div>
    )
  }

  const lastValue = data[data.length - 1]?.pnl ?? 0
  const lineColor = lastValue >= 0 ? '#3ddc84' : '#e84040'

  const formatted = data.map((d) => ({
    ...d,
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  }))

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-[#e2e2f0] mb-4">Cumulative PnL</h3>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={formatted} margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e1e3a' }}
          />
          <YAxis
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `$${v}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="#2a2a4a" strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="pnl"
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: lineColor, stroke: '#16162a', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

const WIN_LOSS_COLORS: Record<string, string> = {
  WIN: '#3ddc84',
  LOSE: '#e84040',
  PENDING: '#f5d623',
}

export function WinLossChart({ counts }: WinLossChartProps) {
  const data = [
    { name: 'WIN', value: counts.WIN },
    { name: 'LOSE', value: counts.LOSE },
    { name: 'PENDING', value: counts.PENDING },
  ].filter((d) => d.value > 0)

  if (data.length === 0) {
    return (
      <div className="card p-6 flex items-center justify-center h-40">
        <p className="text-[#6b6b8a] text-sm">No trade results yet</p>
      </div>
    )
  }

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-[#e2e2f0] mb-4">Win / Loss Breakdown</h3>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e1e3a' }}
          />
          <YAxis
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            contentStyle={{
              background: '#16162a',
              border: '1px solid #1e1e3a',
              borderRadius: '8px',
              fontSize: 12,
              color: '#e2e2f0',
            }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={WIN_LOSS_COLORS[entry.name] ?? '#9b6dff'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
