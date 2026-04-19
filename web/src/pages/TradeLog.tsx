import { useState, useEffect, useCallback } from 'react'
import { Download, AlertCircle, FileText } from 'lucide-react'
import { fetchTrades } from '../api'
import TradeTable from '../components/TradeTable'
import type { Trade } from '../types'

type Filter = 'all' | 'PENDING' | 'WIN' | 'LOSE'

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'PENDING', label: 'Pending' },
  { key: 'WIN', label: 'Won' },
  { key: 'LOSE', label: 'Lost' },
]

function exportCsv(trades: Trade[]) {
  const headers = ['ID', 'Timestamp', 'Match', 'Side', 'Stake', 'Odds', 'Implied%', 'Result', 'PnL']
  const rows = trades.map((t) => [
    t.id,
    t.timestamp,
    `"${t.match.replace(/"/g, '""')}"`,
    `"${t.side.replace(/"/g, '""')}"`,
    t.stake.toFixed(2),
    t.odds.toFixed(2),
    (t.implied_prob * 100).toFixed(2),
    t.result,
    t.pnl.toFixed(2),
  ])
  const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `trades_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export default function TradeLog() {
  const [allTrades, setAllTrades] = useState<Trade[]>([])
  const [filter, setFilter] = useState<Filter>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [counts, setCounts] = useState({ total: 0, pending: 0, settled: 0 })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchTrades()
      setAllTrades(data.trades)
      setCounts({ total: data.total, pending: data.pending, settled: data.settled })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trades')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filteredTrades =
    filter === 'all'
      ? allTrades
      : allTrades.filter((t) => t.result.toUpperCase() === filter)

  return (
    <div className="px-4 md:px-8 py-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-semibold text-[#e2e2f0]">Trade Log</h1>
          {!loading && (
            <p className="text-xs text-[#6b6b8a] mt-1">
              {counts.total} total · {counts.settled} settled · {counts.pending} pending
            </p>
          )}
        </div>
        <button
          onClick={() => exportCsv(filteredTrades)}
          disabled={filteredTrades.length === 0}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-[#16162a] border border-[#1e1e3a] text-[#a0a0c0] hover:text-[#e2e2f0] hover:border-[#2e2e5a] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Download size={13} />
          Export CSV
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1.5 mb-5 flex-wrap">
        {FILTERS.map(({ key, label }) => {
          const count =
            key === 'all'
              ? allTrades.length
              : allTrades.filter((t) => t.result.toUpperCase() === key).length

          return (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                filter === key
                  ? 'bg-[#9b6dff]/15 text-[#9b6dff] border-[#9b6dff]/30'
                  : 'bg-[#16162a] text-[#6b6b8a] border-[#1e1e3a] hover:text-[#a0a0c0] hover:border-[#2e2e5a]'
              }`}
            >
              {label}
              {!loading && (
                <span
                  className={`ml-1.5 text-[10px] ${
                    filter === key ? 'text-[#9b6dff]/70' : 'text-[#4a4a6a]'
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="loading-spinner" />
          <p className="text-sm text-[#6b6b8a]">Loading trades…</p>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="card p-6 flex items-start gap-3">
          <AlertCircle size={18} className="text-[#e84040] shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-[#e84040]">Failed to load trades</p>
            <p className="text-xs text-[#6b6b8a] mt-1">{error}</p>
            <button
              onClick={load}
              className="mt-3 text-xs text-[#9b6dff] hover:text-[#b48fff] transition-colors"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && allTrades.length === 0 && (
        <div className="card p-12 flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-full bg-[#9b6dff]/10 flex items-center justify-center">
            <FileText size={22} className="text-[#9b6dff]" />
          </div>
          <p className="text-sm font-medium text-[#e2e2f0]">No trades logged yet</p>
          <p className="text-xs text-[#6b6b8a] max-w-xs">
            Trades will appear here once you start placing bets using active signals.
          </p>
        </div>
      )}

      {/* Table */}
      {!loading && !error && allTrades.length > 0 && (
        <TradeTable trades={filteredTrades} />
      )}
    </div>
  )
}
