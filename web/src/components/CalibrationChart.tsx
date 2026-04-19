import {
  ResponsiveContainer,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  ComposedChart,
} from 'recharts'
import type { Accuracy } from '../types'

interface CalibrationChartProps {
  data: Accuracy['calibration']
}

interface RollingWinRateChartProps {
  data: Accuracy['rolling_win_rate']
}

function CalibrationTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: { payload: { predicted_prob: number; actual_win_rate: number | null; count: number } }[]
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-[#16162a] border border-[#1e1e3a] rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="text-[#a0a0c0] mb-1">Predicted: {(d.predicted_prob * 100).toFixed(0)}%</div>
      {d.actual_win_rate !== null ? (
        <div className="text-[#3ddc84] font-semibold">
          Actual: {(d.actual_win_rate * 100).toFixed(1)}%
        </div>
      ) : (
        <div className="text-[#6b6b8a]">No data</div>
      )}
      <div className="text-[#6b6b8a] mt-0.5">{d.count} trades</div>
    </div>
  )
}

export function CalibrationChart({ data }: CalibrationChartProps) {
  const points = data
    .filter((d) => d.actual_win_rate !== null)
    .map((d) => ({
      ...d,
      x: d.predicted_prob * 100,
      y: (d.actual_win_rate! * 100),
    }))

  // Diagonal reference line data (perfect calibration)
  const diagPoints = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map((v) => ({ x: v, diag: v }))

  if (points.length === 0) {
    return (
      <div className="card p-6 flex items-center justify-center h-64">
        <p className="text-[#6b6b8a] text-sm">Not enough data for calibration chart</p>
      </div>
    )
  }

  return (
    <div className="card p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-[#e2e2f0]">Model Calibration</h3>
        <p className="text-xs text-[#6b6b8a] mt-0.5">
          Predicted probability vs actual win rate — closer to the diagonal is better
        </p>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <ComposedChart data={diagPoints} margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" />
          <XAxis
            dataKey="x"
            type="number"
            domain={[0, 100]}
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e1e3a' }}
            label={{ value: 'Predicted %', position: 'insideBottom', offset: -4, fill: '#6b6b8a', fontSize: 11 }}
          />
          <YAxis
            type="number"
            domain={[0, 100]}
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            label={{ value: 'Actual %', angle: -90, position: 'insideLeft', fill: '#6b6b8a', fontSize: 11 }}
          />
          <Tooltip content={<CalibrationTooltip />} />
          {/* Perfect calibration diagonal */}
          <Line
            data={diagPoints}
            dataKey="diag"
            stroke="#2a2a4a"
            strokeDasharray="4 4"
            dot={false}
            activeDot={false}
            isAnimationActive={false}
          />
          <Scatter
            data={points}
            fill="#9b6dff"
            opacity={0.85}
            shape={(props: { cx?: number; cy?: number }) => (
              <circle
                cx={props.cx ?? 0}
                cy={props.cy ?? 0}
                r={6}
                fill="#9b6dff"
                stroke="#16162a"
                strokeWidth={1.5}
              />
            )}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

export function RollingWinRateChart({ data }: RollingWinRateChartProps) {
  const filtered = data.filter((d) => d.rolling_10_win_rate !== null).map((d) => ({
    trade: d.trade_number,
    winRate: d.rolling_10_win_rate! * 100,
  }))

  if (filtered.length === 0) {
    return (
      <div className="card p-6 flex items-center justify-center h-48">
        <p className="text-[#6b6b8a] text-sm">Need at least 10 settled trades for rolling win rate</p>
      </div>
    )
  }

  return (
    <div className="card p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-[#e2e2f0]">Rolling 10-Trade Win Rate</h3>
        <p className="text-xs text-[#6b6b8a] mt-0.5">Win rate over a sliding 10-trade window</p>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={filtered} margin={{ top: 4, right: 16, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" vertical={false} />
          <XAxis
            dataKey="trade"
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e1e3a' }}
            label={{ value: 'Trade #', position: 'insideBottom', offset: -4, fill: '#6b6b8a', fontSize: 11 }}
          />
          <YAxis
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              background: '#16162a',
              border: '1px solid #1e1e3a',
              borderRadius: '8px',
              fontSize: 12,
              color: '#e2e2f0',
            }}
            formatter={(value: number) => [`${value.toFixed(1)}%`, 'Win Rate']}
          />
          <ReferenceLine y={50} stroke="#2a2a4a" strokeDasharray="4 4" />
          <Line
            type="monotone"
            dataKey="winRate"
            stroke="#9b6dff"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#9b6dff', stroke: '#16162a', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
