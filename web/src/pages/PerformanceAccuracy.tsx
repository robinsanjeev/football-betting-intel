import { useState, useEffect, useMemo } from 'react'
import {
  TrendingUp, TrendingDown, BarChart2, DollarSign, AlertCircle,
  Activity, Target, ChevronDown, ChevronUp, Download,
} from 'lucide-react'
import { fetchPerformance, fetchAccuracy, fetchTrades, fetchSignalHistory } from '../api'
import type { SignalHistoryEntry } from '../api'
import MetricCard from '../components/MetricCard'
import { CumulativePnlChart, WinLossChart } from '../components/PerformanceChart'
import { CalibrationChart, RollingWinRateChart } from '../components/CalibrationChart'
import type { Performance, Accuracy, Trade } from '../types'

// ─── Results Table Types ────────────────────────────────────────────────────

type SortKey = 'timestamp' | 'match' | 'bet_type' | 'model_prob' | 'implied_prob' | 'edge' | 'upside' | 'result' | 'pnl'
type SortDir = 'asc' | 'desc'
type ResultFilter = 'ALL' | 'WIN' | 'LOSE' | 'PENDING'

function StatusBadge({ result }: { result: string }) {
  const styles: Record<string, string> = {
    WIN: 'bg-[#3ddc84]/15 text-[#3ddc84] border-[#3ddc84]/25',
    LOSE: 'bg-[#e84040]/15 text-[#e84040] border-[#e84040]/25',
    PENDING: 'bg-[#f5d623]/15 text-[#f5d623] border-[#f5d623]/25',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border ${styles[result] || styles.PENDING}`}>
      {result}
    </span>
  )
}

function FilterButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-[11px] font-medium border transition-all ${
        active
          ? 'bg-[#9b6dff]/15 text-[#9b6dff] border-[#9b6dff]/30'
          : 'bg-transparent text-[#6b6b8a] border-[#1e1e3a] hover:text-[#a0a0c0] hover:border-[#2e2e5a]'
      }`}
    >
      {label}
    </button>
  )
}

function SortableHeader({ label, sortKey, currentSort, currentDir, onSort }: {
  label: string
  sortKey: SortKey
  currentSort: SortKey
  currentDir: SortDir
  onSort: (key: SortKey) => void
}) {
  const isActive = currentSort === sortKey
  return (
    <th
      className="px-3 py-2.5 text-left text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium cursor-pointer hover:text-[#a0a0c0] transition-colors select-none whitespace-nowrap"
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {isActive && (
          currentDir === 'asc' ? <ChevronUp size={10} /> : <ChevronDown size={10} />
        )}
      </span>
    </th>
  )
}

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function PerformanceAccuracy() {
  const [perfData, setPerfData] = useState<Performance | null>(null)
  const [accData, setAccData] = useState<Accuracy | null>(null)
  const [_trades, setTrades] = useState<Trade[]>([])
  const [signalHistory, setSignalHistory] = useState<SignalHistoryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Table state
  const [resultFilter, setResultFilter] = useState<ResultFilter>('ALL')
  const [hidePending, setHidePending] = useState(true)  // default: show only settled
  const [sortKey, setSortKey] = useState<SortKey>('timestamp')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  useEffect(() => {
    Promise.all([
      fetchPerformance(),
      fetchAccuracy(),
      fetchTrades(),
      fetchSignalHistory({ limit: 500 }),
    ])
      .then(([perf, acc, tradeResp, histResp]) => {
        setPerfData(perf)
        setAccData(acc)
        setTrades(tradeResp.trades)
        setSignalHistory(histResp.signals)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load data'))
      .finally(() => setLoading(false))
  }, [])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  // Use signal history as the primary data source for the table
  const enrichedTrades = useMemo(() => {
    return signalHistory.map((s) => {
      const stake = 10
      const odds = s.kalshi_implied_prob > 0 ? 1 / s.kalshi_implied_prob : 0
      const hypotheticalPnl = s.outcome === 'WIN'
        ? stake * (odds - 1)
        : s.outcome === 'LOSE'
          ? -stake
          : null
      return {
        id: s.id,
        timestamp: s.generated_at,
        match: s.match_title,
        side: s.description,
        stake: stake,
        odds: odds,
        pnl: s.actual_pnl,
        result: s.outcome,
        impliedProb: s.kalshi_implied_prob,
        modelProb: s.model_prob,
        edge: s.edge,
        upsideCents: s.upside_cents,
        hypotheticalPnl: hypotheticalPnl,
        expectedValue: s.model_prob * stake * (odds - 1) - (1 - s.model_prob) * stake,
        competition: s.competition,
        betType: s.bet_type,
        confidence: s.confidence,
        homeCrest: s.home_crest,
        awayCrest: s.away_crest,
      }
    })
  }, [signalHistory])

  // Settled-only stats for KPI cards
  const settledTrades = useMemo(() =>
    enrichedTrades.filter((t) => t.result === 'WIN' || t.result === 'LOSE'),
    [enrichedTrades]
  )

  const settledStats = useMemo(() => {
    const wins = settledTrades.filter((t) => t.result === 'WIN').length
    const losses = settledTrades.filter((t) => t.result === 'LOSE').length
    const total = wins + losses
    const winRate = total > 0 ? wins / total : 0
    const totalPnl = settledTrades.reduce((sum, t) => {
      if (t.result === 'WIN') return sum + t.stake * (t.odds - 1)
      return sum - t.stake
    }, 0)
    const totalStaked = total * 10
    const roi = totalStaked > 0 ? totalPnl / totalStaked : 0

    // Max drawdown from cumulative PnL
    let peak = 0
    let maxDd = 0
    let cumPnl = 0
    const sorted = [...settledTrades].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    for (const t of sorted) {
      cumPnl += t.result === 'WIN' ? t.stake * (t.odds - 1) : -t.stake
      if (cumPnl > peak) peak = cumPnl
      const dd = peak - cumPnl
      if (dd > maxDd) maxDd = dd
    }

    // Avg edge of settled trades
    const avgEdge = total > 0 ? settledTrades.reduce((s, t) => s + t.edge, 0) / total : 0

    return { wins, losses, total, winRate, totalPnl, totalStaked, roi, maxDrawdown: maxDd, avgEdge }
  }, [settledTrades])

  // Filter and sort
  const filteredTrades = useMemo(() => {
    let result = [...enrichedTrades]
    if (hidePending) result = result.filter((t) => t.result !== 'PENDING')
    if (resultFilter !== 'ALL') result = result.filter((t) => t.result === resultFilter)

    result.sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1
      switch (sortKey) {
        case 'timestamp': return dir * (new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
        case 'match': return dir * a.match.localeCompare(b.match)
        case 'bet_type': return dir * a.betType.localeCompare(b.betType)
        case 'model_prob': return dir * (a.modelProb - b.modelProb)
        case 'implied_prob': return dir * (a.impliedProb - b.impliedProb)
        case 'edge': return dir * (a.edge - b.edge)
        case 'upside': return dir * (a.upsideCents - b.upsideCents)
        case 'result': return dir * a.result.localeCompare(b.result)
        case 'pnl': return dir * (a.pnl - b.pnl)
        default: return 0
      }
    })
    return result
  }, [enrichedTrades, resultFilter, sortKey, sortDir])

  // Running hypothetical PnL
  const runningPnl = useMemo(() => {
    let total = 0
    const settled = enrichedTrades.filter((t) => t.result !== 'PENDING').sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )
    return settled.map((t) => {
      total += t.result === 'WIN' ? t.stake * (t.odds - 1) : -t.stake
      return total
    })
  }, [enrichedTrades])

  const hypotheticalTotal = runningPnl.length > 0 ? runningPnl[runningPnl.length - 1] : 0

  // CSV export
  const exportCsv = () => {
    const headers = ['Date', 'Match', 'Bet Type', 'Recommendation', 'Model %', 'Market %', 'Edge %', 'Upside ¢', 'Stake', 'Odds', 'Result', 'PnL', 'Hypothetical PnL']
    const rows = filteredTrades.map((t) => [
      new Date(t.timestamp).toLocaleDateString(),
      t.match,
      t.betType,
      t.side,
      (t.modelProb * 100).toFixed(1),
      (t.impliedProb * 100).toFixed(1),
      (t.edge * 100).toFixed(1),
      t.upsideCents,
      t.stake.toFixed(2),
      t.odds.toFixed(2),
      t.result,
      t.pnl.toFixed(2),
      t.hypotheticalPnl !== null ? t.hypotheticalPnl.toFixed(2) : 'pending',
    ])
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `football-intel-results-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="px-4 md:px-8 py-6 max-w-6xl mx-auto">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-[#e2e2f0]">Performance &amp; Accuracy</h1>
        <p className="text-xs text-[#6b6b8a] mt-1">Model performance, accuracy metrics, and detailed trade results</p>
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
            <p className="text-sm font-medium text-[#e84040]">Failed to load data</p>
            <p className="text-xs text-[#6b6b8a] mt-1">{error}</p>
          </div>
        </div>
      )}

      {!loading && !error && perfData && (
        <>
          {/* ── Settled-only banner ── */}
          {settledStats.total === 0 && (
            <div className="card p-4 mb-6 flex items-center gap-3 border-[#f5a623]/20 bg-[#f5a623]/[0.04]">
              <AlertCircle size={16} className="text-[#f5a623] shrink-0" />
              <p className="text-xs text-[#a0a0c0]">
                No settled trades yet. Performance metrics will populate as matches complete and trades are settled.
                Currently tracking <span className="text-[#e2e2f0] font-medium">{enrichedTrades.length}</span> pending signals.
              </p>
            </div>
          )}

          {/* ── KPI Row (settled only) ── */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
            <MetricCard
              label="Settled Trades"
              value={settledStats.total}
              subValue={`${enrichedTrades.length} total signals`}
              icon={<BarChart2 size={14} />}
              trend="neutral"
              valueColor="text-[#e2e2f0]"
            />
            <MetricCard
              label="Win Rate"
              value={settledStats.total > 0 ? `${(settledStats.winRate * 100).toFixed(1)}%` : '—'}
              subValue={settledStats.total > 0 ? `${settledStats.wins}W / ${settledStats.losses}L` : 'No settled'}
              icon={<TrendingUp size={14} />}
              trend={settledStats.winRate >= 0.5 ? 'positive' : settledStats.winRate > 0 ? 'negative' : 'neutral'}
            />
            <MetricCard
              label="ROI"
              value={settledStats.total > 0 ? `${(settledStats.roi * 100).toFixed(1)}%` : '—'}
              subValue={settledStats.totalStaked > 0 ? `$${settledStats.totalStaked.toFixed(0)} staked` : ''}
              icon={<TrendingUp size={14} />}
              trend={settledStats.roi > 0 ? 'positive' : settledStats.roi < 0 ? 'negative' : 'neutral'}
            />
            <MetricCard
              label="Cumulative PnL"
              value={settledStats.total > 0 ? `${settledStats.totalPnl >= 0 ? '+' : ''}$${settledStats.totalPnl.toFixed(2)}` : '$0'}
              icon={<DollarSign size={14} />}
              trend={settledStats.totalPnl > 0 ? 'positive' : settledStats.totalPnl < 0 ? 'negative' : 'neutral'}
            />
            <MetricCard
              label="Max Drawdown"
              value={settledStats.total > 0 ? `-$${settledStats.maxDrawdown.toFixed(2)}` : '$0'}
              icon={<TrendingDown size={14} />}
              trend={settledStats.maxDrawdown > 5 ? 'negative' : 'neutral'}
              valueColor="text-[#e84040]"
            />
            <MetricCard
              label="Avg Edge"
              value={settledStats.total > 0 ? `${(settledStats.avgEdge * 100).toFixed(1)}%` : '—'}
              subValue="on settled trades"
              icon={<Activity size={14} />}
              trend={settledStats.avgEdge > 0.08 ? 'positive' : 'neutral'}
            />
          </div>

          {/* ── Charts Row ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <CumulativePnlChart data={perfData.cumulative_pnl} />
            <WinLossChart counts={perfData.win_loss_counts} />
          </div>

          {/* ── Accuracy Section ── */}
          {accData && (
            <>
              <div className="flex items-center gap-2 mb-4 mt-8">
                <Target size={16} className="text-[#9b6dff]" />
                <h2 className="text-base font-semibold text-[#e2e2f0]">Model Accuracy</h2>
                {accData.total_settled > 0 && (
                  <span className="text-[11px] text-[#6b6b8a]">
                    · {accData.total_settled} settled trades
                  </span>
                )}
              </div>

              {accData.total_settled === 0 ? (
                <div className="card p-8 flex flex-col items-center gap-3 text-center mb-8">
                  <Target size={20} className="text-[#6b6b8a]" />
                  <p className="text-sm font-medium text-[#e2e2f0]">Not enough data yet</p>
                  <p className="text-xs text-[#6b6b8a] max-w-sm">
                    {accData.message || 'Calibration and accuracy charts will appear once trades settle.'}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
                  <CalibrationChart data={accData.calibration} />
                  <RollingWinRateChart data={accData.rolling_win_rate} />
                </div>
              )}
            </>
          )}

          {/* ── Results Table ── */}
          <div className="mt-8">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h2 className="text-base font-semibold text-[#e2e2f0]">Settled Results</h2>
                <p className="text-[11px] text-[#6b6b8a] mt-0.5">
                  Only settled trades are shown — these reflect actual model performance
                </p>
              </div>
              <button
                onClick={exportCsv}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-[#16162a] border border-[#1e1e3a] text-[#a0a0c0] hover:text-[#e2e2f0] hover:border-[#2e2e5a] transition-all"
              >
                <Download size={13} />
                CSV
              </button>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-1.5 mb-4">
              <FilterButton
                label={hidePending ? 'Settled Only' : 'All Signals'}
                active={hidePending}
                onClick={() => setHidePending(!hidePending)}
              />
              {(['ALL', 'WIN', 'LOSE'] as ResultFilter[]).map((f) => (
                <FilterButton
                  key={f}
                  label={f === 'ALL' ? `All (${settledTrades.length})` : `${f} (${settledTrades.filter((t) => t.result === f).length})`}
                  active={resultFilter === f}
                  onClick={() => setResultFilter(f)}
                />
              ))}
              {!hidePending && (
                <FilterButton
                  label={`PENDING (${enrichedTrades.filter((t) => t.result === 'PENDING').length})`}
                  active={resultFilter === 'PENDING'}
                  onClick={() => setResultFilter('PENDING')}
                />
              )}
            </div>

            {/* Table */}
            <div className="card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-[#1e1e3a]">
                      <SortableHeader label="Date" sortKey="timestamp" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <SortableHeader label="Match" sortKey="match" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <SortableHeader label="Type" sortKey="bet_type" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium whitespace-nowrap">Recommendation</th>
                      <SortableHeader label="Model %" sortKey="model_prob" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <SortableHeader label="Market %" sortKey="implied_prob" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <SortableHeader label="Edge" sortKey="edge" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <SortableHeader label="Upside" sortKey="upside" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium whitespace-nowrap">Conf.</th>
                      <SortableHeader label="Result" sortKey="result" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium whitespace-nowrap">Exp. Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTrades.length === 0 && (
                      <tr>
                        <td colSpan={11} className="px-3 py-8 text-center text-[#6b6b8a] text-xs">
                          No trades match the selected filter.
                        </td>
                      </tr>
                    )}
                    {filteredTrades.map((t) => (
                      <tr
                        key={t.id}
                        className={`border-b border-[#1e1e3a]/50 hover:bg-[#1a1a30] transition-colors ${
                          t.result === 'WIN' ? 'bg-[#3ddc84]/[0.03]' :
                          t.result === 'LOSE' ? 'bg-[#e84040]/[0.03]' : ''
                        }`}
                      >
                        <td className="px-3 py-2.5 text-[#6b6b8a] whitespace-nowrap">
                          {new Date(t.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </td>
                        <td className="px-3 py-2.5 text-[#e2e2f0] font-medium max-w-[180px] truncate">
                          {t.match}
                        </td>
                        <td className="px-3 py-2.5 whitespace-nowrap">
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold bg-[#9b6dff]/10 text-[#9b6dff] border border-[#9b6dff]/20">
                            {t.betType.replace('_', '/')}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-[#a0a0c0] max-w-[160px] truncate">
                          {t.side}
                        </td>
                        <td className="px-3 py-2.5 font-mono text-[#9b6dff] whitespace-nowrap">
                          {(t.modelProb * 100).toFixed(1)}%
                        </td>
                        <td className="px-3 py-2.5 font-mono text-[#a0a0c0] whitespace-nowrap">
                          {(t.impliedProb * 100).toFixed(1)}%
                        </td>
                        <td className="px-3 py-2.5 font-mono whitespace-nowrap">
                          <span className={t.edge > 0 ? 'text-[#3ddc84]' : 'text-[#e84040]'}>
                            {t.edge > 0 ? '+' : ''}{(t.edge * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-[#3ddc84] whitespace-nowrap">
                          +{t.upsideCents}¢
                        </td>
                        <td className="px-3 py-2.5 whitespace-nowrap">
                          <span className={`text-[10px] font-semibold ${
                            t.confidence === 'HIGH' ? 'text-[#3ddc84]' :
                            t.confidence === 'MEDIUM' ? 'text-[#f5a623]' : 'text-[#e84040]'
                          }`}>{t.confidence}</span>
                        </td>
                        <td className="px-3 py-2.5">
                          <StatusBadge result={t.result} />
                        </td>
                        <td className="px-3 py-2.5 font-mono whitespace-nowrap">
                          <span className={t.expectedValue >= 0 ? 'text-[#3ddc84]' : 'text-[#e84040]'}>
                            {t.expectedValue >= 0 ? '+' : ''}${t.expectedValue.toFixed(2)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Table footer */}
              {filteredTrades.length > 0 && (
                <div className="px-3 py-2.5 border-t border-[#1e1e3a] flex items-center justify-between text-[10px] text-[#6b6b8a]">
                  <span>
                    Showing {filteredTrades.length} of {enrichedTrades.length} signals
                  </span>
                  <span>
                    Net PnL: {' '}
                    <span className={`font-mono font-semibold ${perfData.total_pnl >= 0 ? 'text-[#3ddc84]' : 'text-[#e84040]'}`}>
                      {perfData.total_pnl >= 0 ? '+' : ''}${perfData.total_pnl.toFixed(2)}
                    </span>
                    {' '} · Hypothetical: {' '}
                    <span className={`font-mono font-semibold ${hypotheticalTotal >= 0 ? 'text-[#3ddc84]' : 'text-[#e84040]'}`}>
                      {hypotheticalTotal >= 0 ? '+' : ''}${hypotheticalTotal.toFixed(2)}
                    </span>
                  </span>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
