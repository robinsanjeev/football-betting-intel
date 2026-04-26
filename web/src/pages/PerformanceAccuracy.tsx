import { useState, useEffect, useMemo } from 'react'
import {
  TrendingUp, TrendingDown, BarChart2, DollarSign, AlertCircle,
  Activity, ChevronDown, ChevronUp, Download, Target,
} from 'lucide-react'
import { fetchPerformance, fetchAccuracy, fetchTrades, fetchSignalHistory } from '../api'
import type { SignalHistoryEntry } from '../api'
import MetricCard from '../components/MetricCard'
import { WinLossChart } from '../components/PerformanceChart'
import type { Performance, Accuracy, Trade } from '../types'

// ─── Results Table Types ────────────────────────────────────────────────────

type SortKey = 'timestamp' | 'match' | 'bet_type' | 'model_prob' | 'implied_prob' | 'edge' | 'upside' | 'result' | 'pnl' | 'composite_score'
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
  const [betTypeFilter, setBetTypeFilter] = useState('ALL')
  const [competitionFilter, setCompetitionFilter] = useState('ALL')
  const [confidenceFilter, setConfidenceFilter] = useState('ALL')
  const [timeFilter, setTimeFilter] = useState('ALL') // ALL | 7d | 14d | 30d | 90d
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
    return signalHistory.filter((s) => s.bet_placed !== false).map((s) => {
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
        actualPnl: s.actual_pnl,
        betPlaced: s.bet_placed ?? false,
        compositeScore: s.composite_score ?? 0,
        scoreBreakdown: s.score_breakdown ?? '',
      }
    })
  }, [signalHistory])

  // Time filter cutoff
  const timeCutoff = useMemo(() => {
    if (timeFilter === 'ALL') return null
    const days = parseInt(timeFilter)
    if (isNaN(days)) return null
    const d = new Date()
    d.setDate(d.getDate() - days)
    return d.getTime()
  }, [timeFilter])

  // Settled trades (respects all filters for KPIs + charts)
  const settledTrades = useMemo(() => {
    let result = enrichedTrades.filter((t) => t.result === 'WIN' || t.result === 'LOSE')
    if (timeCutoff) result = result.filter((t) => new Date(t.timestamp).getTime() >= timeCutoff)
    if (betTypeFilter !== 'ALL') result = result.filter((t) => t.betType === betTypeFilter)
    if (competitionFilter !== 'ALL') result = result.filter((t) => t.competition === competitionFilter)
    if (confidenceFilter !== 'ALL') result = result.filter((t) => t.confidence === confidenceFilter)
    return result
  }, [enrichedTrades, timeCutoff, betTypeFilter, competitionFilter, confidenceFilter])

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

  // Unique values for filter dropdowns
  const uniqueBetTypes = useMemo(() => {
    const types = new Set(enrichedTrades.map((t) => t.betType))
    return ['ALL', ...Array.from(types).sort()]
  }, [enrichedTrades])

  const uniqueCompetitions = useMemo(() => {
    const comps = new Set(enrichedTrades.map((t) => t.competition))
    return ['ALL', ...Array.from(comps).sort()]
  }, [enrichedTrades])

  // Filter and sort
  const filteredTrades = useMemo(() => {
    let result = [...enrichedTrades]
    if (hidePending) result = result.filter((t) => t.result !== 'PENDING')
    if (timeCutoff) result = result.filter((t) => new Date(t.timestamp).getTime() >= timeCutoff)
    if (resultFilter !== 'ALL') result = result.filter((t) => t.result === resultFilter)
    if (betTypeFilter !== 'ALL') result = result.filter((t) => t.betType === betTypeFilter)
    if (competitionFilter !== 'ALL') result = result.filter((t) => t.competition === competitionFilter)
    if (confidenceFilter !== 'ALL') result = result.filter((t) => t.confidence === confidenceFilter)

    result.sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1
      switch (sortKey) {
        case 'timestamp': return dir * (new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
        case 'match': return dir * a.match.localeCompare(b.match)
        case 'bet_type': return dir * a.betType.localeCompare(b.betType)
        case 'model_prob': return dir * (a.modelProb - b.modelProb)
        case 'implied_prob': return dir * (a.impliedProb - b.impliedProb)
        case 'edge': return dir * (a.edge - b.edge)
        case 'composite_score': return dir * (a.compositeScore - b.compositeScore)
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
    const headers = ['Date', 'Match', 'Bet Type', 'Recommendation', 'Model %', 'Market %', 'Edge %', 'Composite Score', 'Upside ¢', 'Stake', 'Odds', 'Result', 'Actual PnL', 'Bet Placed', 'Hypothetical PnL']
    const rows = filteredTrades.map((t) => [
      new Date(t.timestamp).toLocaleDateString(),
      t.match,
      t.betType,
      t.side,
      (t.modelProb * 100).toFixed(1),
      (t.impliedProb * 100).toFixed(1),
      (t.edge * 100).toFixed(1),
      t.compositeScore.toFixed(0),
      t.upsideCents,
      t.stake.toFixed(2),
      t.odds.toFixed(2),
      t.result,
      t.actualPnl.toFixed(2),
      t.betPlaced ? 'Yes' : 'No',
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
          {/* ── Page-level filters (single row) ── */}
          <div className="flex flex-wrap gap-1.5 items-center mb-6">
              <FilterButton
                label={hidePending ? 'Settled' : 'All'}
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
              <span className="w-px h-6 bg-[#1e1e3a]" />
              <select
                value={betTypeFilter}
                onChange={(e) => setBetTypeFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded-full text-[11px] font-medium border bg-transparent text-[#a0a0c0] border-[#1e1e3a] hover:border-[#2e2e5a] focus:outline-none focus:border-[#9b6dff]/50 transition-all appearance-none cursor-pointer"
              >
                {uniqueBetTypes.map((t) => (
                  <option key={t} value={t} className="bg-[#16162a] text-[#e2e2f0]">
                    {t === 'ALL' ? 'All Types' : t.replace('_', '/')}
                  </option>
                ))}
              </select>
              <select
                value={competitionFilter}
                onChange={(e) => setCompetitionFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded-full text-[11px] font-medium border bg-transparent text-[#a0a0c0] border-[#1e1e3a] hover:border-[#2e2e5a] focus:outline-none focus:border-[#9b6dff]/50 transition-all appearance-none cursor-pointer"
              >
                {uniqueCompetitions.map((c) => (
                  <option key={c} value={c} className="bg-[#16162a] text-[#e2e2f0]">
                    {c === 'ALL' ? 'All Leagues' : c}
                  </option>
                ))}
              </select>
              <select
                value={confidenceFilter}
                onChange={(e) => setConfidenceFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded-full text-[11px] font-medium border bg-transparent text-[#a0a0c0] border-[#1e1e3a] hover:border-[#2e2e5a] focus:outline-none focus:border-[#9b6dff]/50 transition-all appearance-none cursor-pointer"
              >
                <option value="ALL" className="bg-[#16162a] text-[#e2e2f0]">All Confidence</option>
                <option value="HIGH" className="bg-[#16162a] text-[#e2e2f0]">HIGH</option>
                <option value="MEDIUM" className="bg-[#16162a] text-[#e2e2f0]">MEDIUM</option>
                <option value="LOW" className="bg-[#16162a] text-[#e2e2f0]">LOW</option>
              </select>
              <span className="w-px h-6 bg-[#1e1e3a] self-center" />
              <select
                value={timeFilter}
                onChange={(e) => setTimeFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded-full text-[11px] font-medium border bg-transparent text-[#a0a0c0] border-[#1e1e3a] hover:border-[#2e2e5a] focus:outline-none focus:border-[#9b6dff]/50 transition-all appearance-none cursor-pointer"
              >
                <option value="ALL" className="bg-[#16162a] text-[#e2e2f0]">All Time</option>
                <option value="7" className="bg-[#16162a] text-[#e2e2f0]">Last 7 days</option>
                <option value="14" className="bg-[#16162a] text-[#e2e2f0]">Last 14 days</option>
                <option value="30" className="bg-[#16162a] text-[#e2e2f0]">Last 30 days</option>
                <option value="90" className="bg-[#16162a] text-[#e2e2f0]">Last 90 days</option>
              </select>
              {(betTypeFilter !== 'ALL' || competitionFilter !== 'ALL' || confidenceFilter !== 'ALL' || timeFilter !== 'ALL') && (
                <button
                  onClick={() => { setBetTypeFilter('ALL'); setCompetitionFilter('ALL'); setConfidenceFilter('ALL'); setTimeFilter('ALL') }}
                  className="px-2.5 py-1.5 rounded-full text-[11px] font-medium text-[#e84040] border border-[#e84040]/20 hover:bg-[#e84040]/10 transition-all"
                >
                  × Clear
                </button>
              )}
          </div>

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
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
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
            <MetricCard
              label="Avg Score (Winners)"
              value={perfData.avg_composite_score_winners != null ? perfData.avg_composite_score_winners.toFixed(1) : '—'}
              icon={<Target size={14} />}
              trend="positive"
              valueColor="text-[#3ddc84]"
            />
            <MetricCard
              label="Avg Score (Losers)"
              value={perfData.avg_composite_score_losers != null ? perfData.avg_composite_score_losers.toFixed(1) : '—'}
              icon={<Target size={14} />}
              trend="negative"
              valueColor="text-[#e84040]"
            />
          </div>

          {/* ── Charts Row (settled only) ── */}
          {/* ── Charts Row (side by side, rolling 7 days) ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            {/* Cumulative PnL over time (rolling 7 days) */}
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-[#e2e2f0] mb-1">Cumulative PnL</h3>
              <p className="text-[10px] text-[#6b6b8a] mb-4">Rolling 7-day view — settled trades only</p>
              {(() => {
                // Build 7-day date range ending today
                const today = new Date()
                const dates: string[] = []
                const dateKeys: string[] = []
                for (let i = 6; i >= 0; i--) {
                  const d = new Date(today)
                  d.setDate(d.getDate() - i)
                  dates.push(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))
                  dateKeys.push(d.toISOString().slice(0, 10))
                }

                // Group settled trades by ISO date
                const pnlByDate: Record<string, number> = {}
                for (const t of settledTrades) {
                  const dk = new Date(t.timestamp).toISOString().slice(0, 10)
                  const pnl = t.result === 'WIN' ? t.stake * (t.odds - 1) : -t.stake
                  pnlByDate[dk] = (pnlByDate[dk] || 0) + pnl
                }

                // Compute cumulative PnL up to each day
                // First, get cumulative before the 7-day window
                const allSorted = [...settledTrades].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
                let priorCum = 0
                for (const t of allSorted) {
                  const dk = new Date(t.timestamp).toISOString().slice(0, 10)
                  if (dk < dateKeys[0]) {
                    priorCum += t.result === 'WIN' ? t.stake * (t.odds - 1) : -t.stake
                  }
                }

                let cum = priorCum
                const series = dateKeys.map((dk, i) => {
                  const dailyPnl = pnlByDate[dk] || 0
                  cum += dailyPnl
                  return { date: dates[i], dailyPnl, cumPnl: cum, hasData: dk in pnlByDate }
                })

                const allZero = series.every(s => s.cumPnl === 0 && !s.hasData)
                if (allZero) {
                  return (
                    <div className="flex items-center justify-center h-48">
                      <p className="text-[#6b6b8a] text-sm">No settled trades in the last 7 days</p>
                    </div>
                  )
                }

                const maxCum = Math.max(...series.map(s => Math.abs(s.cumPnl)), 0.01)
                const w = 100
                const h = 120
                const pad = 4
                const points = series.map((s, i) => {
                  const x = pad + (i / 6) * (w - 2 * pad)
                  const y = h / 2 - (s.cumPnl / maxCum) * (h / 2 - pad)
                  return { x, y, ...s }
                })
                const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
                const fillD = `${pathD} L${points[6].x},${h / 2} L${points[0].x},${h / 2} Z`
                const lastPnl = series[6].cumPnl
                const color = lastPnl >= 0 ? '#3ddc84' : '#e84040'
                const fillColor = lastPnl >= 0 ? 'rgba(61,220,132,0.08)' : 'rgba(232,64,64,0.08)'

                return (
                  <>
                    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: '180px' }} preserveAspectRatio="none">
                      <line x1={0} y1={h / 2} x2={w} y2={h / 2} stroke="#1e1e3a" strokeWidth="0.3" strokeDasharray="1,1" />
                      <path d={fillD} fill={fillColor} />
                      <path d={pathD} fill="none" stroke={color} strokeWidth="0.7" strokeLinecap="round" strokeLinejoin="round" />
                      {points.map((p, i) => (
                        <circle key={i} cx={p.x} cy={p.y} r={p.hasData ? 1.4 : 0.8} fill={p.hasData ? color : '#6b6b8a'} stroke="#0d0d14" strokeWidth="0.3">
                          <title>{p.date}: {p.cumPnl >= 0 ? '+' : ''}${p.cumPnl.toFixed(2)}{p.hasData ? ` (day: ${p.dailyPnl >= 0 ? '+' : ''}$${p.dailyPnl.toFixed(2)})` : ' (no trades)'}</title>
                        </circle>
                      ))}
                    </svg>
                    <div className="flex justify-between text-[9px] text-[#6b6b8a] mt-1 px-1">
                      {dates.map((d, i) => (
                        <span key={i} className={series[i].hasData ? 'text-[#a0a0c0]' : ''}>{d.split(' ')[1]}</span>
                      ))}
                    </div>
                    <div className="text-center text-[10px] mt-2">
                      <span className={`font-mono font-semibold ${lastPnl >= 0 ? 'text-[#3ddc84]' : 'text-[#e84040]'}`}>
                        {lastPnl >= 0 ? '+' : ''}${lastPnl.toFixed(2)}
                      </span>
                      <span className="text-[#6b6b8a]"> cumulative</span>
                    </div>
                  </>
                )
              })()}
            </div>

            {/* Daily bets stacked bar (rolling 7 days) */}
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-[#e2e2f0] mb-1">Daily Bets</h3>
              <p className="text-[10px] text-[#6b6b8a] mb-4">Wins vs losses per day — last 7 days</p>
              {(() => {
                const today = new Date()
                const dates: string[] = []
                const dateKeys: string[] = []
                for (let i = 6; i >= 0; i--) {
                  const d = new Date(today)
                  d.setDate(d.getDate() - i)
                  dates.push(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))
                  dateKeys.push(d.toISOString().slice(0, 10))
                }

                const byDate: Record<string, { wins: number; losses: number }> = {}
                for (const t of settledTrades) {
                  const dk = new Date(t.timestamp).toISOString().slice(0, 10)
                  if (!byDate[dk]) byDate[dk] = { wins: 0, losses: 0 }
                  if (t.result === 'WIN') byDate[dk].wins++
                  else byDate[dk].losses++
                }

                const days = dateKeys.map((dk, i) => {
                  const counts = byDate[dk] || { wins: 0, losses: 0 }
                  return { date: dates[i], dateKey: dk, ...counts, total: counts.wins + counts.losses }
                })

                const maxTotal = Math.max(...days.map(d => d.total), 1)
                const hasAny = days.some(d => d.total > 0)

                if (!hasAny) {
                  return (
                    <div className="flex items-center justify-center h-48">
                      <p className="text-[#6b6b8a] text-sm">No settled trades in the last 7 days</p>
                    </div>
                  )
                }

                return (
                  <>
                    <div className="flex items-end gap-2" style={{ height: '160px' }}>
                      {days.map((d) => {
                        const winH = maxTotal > 0 ? (d.wins / maxTotal) * 130 : 0
                        const loseH = maxTotal > 0 ? (d.losses / maxTotal) * 130 : 0
                        return (
                          <div key={d.dateKey} className="flex-1 flex flex-col items-center justify-end h-full" title={`${d.date}: ${d.wins}W / ${d.losses}L`}>
                            {d.total === 0 ? (
                              <div className="w-full flex items-end justify-center h-full">
                                <div className="w-full h-[2px] bg-[#1e1e3a] rounded" />
                              </div>
                            ) : (
                              <div className="w-full flex flex-col justify-end">
                                {d.wins > 0 && (
                                  <div className="w-full rounded-t" style={{ height: `${Math.max(winH, 4)}px`, backgroundColor: '#3ddc84' }} />
                                )}
                                {d.losses > 0 && (
                                  <div className="w-full" style={{ height: `${Math.max(loseH, 4)}px`, backgroundColor: '#e84040', borderRadius: d.wins === 0 ? '4px 4px 0 0' : '0' }} />
                                )}
                              </div>
                            )}
                            <span className="text-[9px] text-[#6b6b8a] mt-1.5">{d.date.split(' ')[1]}</span>
                          </div>
                        )
                      })}
                    </div>
                    <div className="flex items-center gap-4 justify-center mt-3 text-[10px]">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-sm bg-[#3ddc84]"></span>
                        <span className="text-[#a0a0c0]">Wins ({settledStats.wins})</span>
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-sm bg-[#e84040]"></span>
                        <span className="text-[#a0a0c0]">Losses ({settledStats.losses})</span>
                      </span>
                    </div>
                  </>
                )
              })()}
            </div>
          </div>

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
                      <SortableHeader label="Score" sortKey="composite_score" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <SortableHeader label="Upside" sortKey="upside" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium whitespace-nowrap">Conf.</th>
                      <SortableHeader label="Result" sortKey="result" currentSort={sortKey} currentDir={sortDir} onSort={handleSort} />
                      <th className="px-3 py-2.5 text-left text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium whitespace-nowrap">Actual PnL</th>
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
                        <td className="px-3 py-2.5 font-mono whitespace-nowrap">
                          <span className={t.compositeScore >= 70 ? 'text-[#3ddc84]' : t.compositeScore >= 50 ? 'text-[#f5a623]' : 'text-[#e84040]'}>
                            {t.compositeScore.toFixed(0)}
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
                          {t.result === 'PENDING' ? (
                            <span className="text-[#6b6b8a]">—</span>
                          ) : (
                            <span className={t.actualPnl >= 0 ? 'text-[#3ddc84]' : 'text-[#e84040]'}>
                              {t.actualPnl >= 0 ? '+' : ''}${t.actualPnl.toFixed(2)}
                            </span>
                          )}
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
