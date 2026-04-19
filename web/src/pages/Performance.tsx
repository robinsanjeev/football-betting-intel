import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, BarChart2, DollarSign, AlertCircle, Activity } from 'lucide-react'
import { fetchPerformance } from '../api'
import MetricCard from '../components/MetricCard'
import { CumulativePnlChart, WinLossChart } from '../components/PerformanceChart'
import type { Performance as PerformanceData } from '../types'

export default function Performance() {
  const [data, setData] = useState<PerformanceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPerformance()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load performance'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="px-4 md:px-8 py-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-[#e2e2f0]">Performance</h1>
        <p className="text-xs text-[#6b6b8a] mt-1">Track your betting record and returns</p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="loading-spinner" />
          <p className="text-sm text-[#6b6b8a]">Loading performance data…</p>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="card p-6 flex items-start gap-3">
          <AlertCircle size={18} className="text-[#e84040] shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-[#e84040]">Failed to load performance</p>
            <p className="text-xs text-[#6b6b8a] mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Empty / no settled trades */}
      {!loading && !error && data && data.settled_trades === 0 && (
        <div className="card p-12 flex flex-col items-center gap-3 text-center mb-6">
          <div className="w-12 h-12 rounded-full bg-[#9b6dff]/10 flex items-center justify-center">
            <Activity size={22} className="text-[#9b6dff]" />
          </div>
          <p className="text-sm font-medium text-[#e2e2f0]">No settled trades yet</p>
          <p className="text-xs text-[#6b6b8a] max-w-xs">
            Performance metrics will appear once your trades are settled. Keep placing bets!
          </p>
        </div>
      )}

      {!loading && !error && data && (
        <>
          {/* KPI grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
            <MetricCard
              label="Total Trades"
              value={data.total_trades}
              subValue={`${data.settled_trades} settled · ${data.pending_trades} pending`}
              icon={<BarChart2 size={14} />}
              trend="neutral"
              valueColor="text-[#e2e2f0]"
            />
            <MetricCard
              label="Win Rate"
              value={data.settled_trades > 0 ? `${(data.win_rate * 100).toFixed(1)}%` : '—'}
              subValue={data.settled_trades > 0 ? `${data.settled_trades} settled` : 'No data yet'}
              icon={<TrendingUp size={14} />}
              trend={data.win_rate >= 0.5 ? 'positive' : data.win_rate > 0 ? 'negative' : 'neutral'}
            />
            <MetricCard
              label="ROI"
              value={data.settled_trades > 0 ? `${(data.roi * 100).toFixed(1)}%` : '—'}
              subValue={`$${data.total_staked.toFixed(2)} staked`}
              icon={<TrendingUp size={14} />}
              trend={data.roi > 0 ? 'positive' : data.roi < 0 ? 'negative' : 'neutral'}
            />
            <MetricCard
              label="Total PnL"
              value={data.total_pnl !== 0 ? `${data.total_pnl >= 0 ? '+' : ''}$${data.total_pnl.toFixed(2)}` : '$0.00'}
              icon={<DollarSign size={14} />}
              trend={data.total_pnl > 0 ? 'positive' : data.total_pnl < 0 ? 'negative' : 'neutral'}
            />
            <MetricCard
              label="Max Drawdown"
              value={data.max_drawdown !== 0 ? `-$${Math.abs(data.max_drawdown).toFixed(2)}` : '$0.00'}
              icon={<TrendingDown size={14} />}
              trend={data.max_drawdown < -5 ? 'negative' : 'neutral'}
              valueColor="text-[#e84040]"
            />
          </div>

          {/* Charts */}
          <div className="space-y-4">
            <CumulativePnlChart data={data.cumulative_pnl} />
            <WinLossChart counts={data.win_loss_counts} />
          </div>
        </>
      )}
    </div>
  )
}
