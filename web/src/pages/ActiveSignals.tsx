import { useState, useEffect, useCallback, useMemo } from 'react'
import { RefreshCw, AlertCircle, Zap, TrendingUp, Target, BarChart3, Filter, HelpCircle, X } from 'lucide-react'
import { fetchActiveSignals, fetchAllOddsMovement } from '../api'
import SignalCard from '../components/SignalCard'
import type { Signal } from '../types'

const REFRESH_INTERVAL_MS = 5 * 60 * 1000 // 5 minutes

const BET_TYPES = ['ALL', 'MONEYLINE', 'OVER_UNDER', 'SPREAD', 'BTTS', 'FIRST_HALF'] as const
const COMPETITIONS = ['ALL', 'EPL', 'Bundesliga', 'UCL'] as const
const CONFIDENCE_LEVELS = ['ALL', 'HIGH', 'MEDIUM', 'LOW'] as const
const SORT_OPTIONS = [
  { label: 'Composite Score', value: 'composite_score' },
  { label: 'Highest Edge', value: 'edge' },
  { label: 'Highest Score', value: 'score' },
  { label: 'Highest Prob', value: 'model_prob' },
  { label: 'Lowest Entry', value: 'entry' },
] as const

type SortOption = typeof SORT_OPTIONS[number]['value']

interface SummaryStats {
  totalSignals: number
  avgEdge: number
  avgScore: number
  strongCount: number
  topCompetition: string
  topBetType: string
  bestEdge: number
}

function computeSummary(signals: Signal[]): SummaryStats {
  if (signals.length === 0) {
    return {
      totalSignals: 0, avgEdge: 0, avgScore: 0, strongCount: 0,
      topCompetition: '-', topBetType: '-', bestEdge: 0,
    }
  }
  const avgEdge = (signals.reduce((s, x) => s + x.edge, 0) / signals.length) * 100
  const avgScore = signals.reduce((s, x) => s + x.score, 0) / signals.length
  const strongCount = signals.filter((s) => s.edge >= 0.20).length
  const bestEdge = Math.max(...signals.map((s) => s.edge)) * 100

  const compCounts: Record<string, number> = {}
  const typeCounts: Record<string, number> = {}
  for (const s of signals) {
    compCounts[s.competition] = (compCounts[s.competition] || 0) + 1
    typeCounts[s.bet_type] = (typeCounts[s.bet_type] || 0) + 1
  }
  const topCompetition = Object.entries(compCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '-'
  const topBetType = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '-'

  return { totalSignals: signals.length, avgEdge, avgScore, strongCount, topCompetition, topBetType, bestEdge }
}

function SummaryCard({ label, value, sub, icon: Icon, color }: {
  label: string
  value: string
  sub?: string
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="card p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center`} style={{ background: `${color}15` }}>
        <Icon size={18} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium">{label}</p>
        <p className="text-lg font-semibold text-[#e2e2f0] font-mono">{value}</p>
        {sub && <p className="text-[10px] text-[#6b6b8a] truncate">{sub}</p>}
      </div>
    </div>
  )
}

function FilterPill({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
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

function ScoreExplainer() {
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 mb-4 text-[11px] text-[#6b6b8a] hover:text-[#a0a0c0] transition-colors"
      >
        <HelpCircle size={13} />
        <span>How do signals work?</span>
      </button>
    )
  }

  return (
    <div className="card p-5 mb-6 relative">
      <button
        onClick={() => setOpen(false)}
        className="absolute top-3 right-3 text-[#6b6b8a] hover:text-[#a0a0c0] transition-colors"
      >
        <X size={14} />
      </button>
      <h3 className="text-sm font-semibold text-[#e2e2f0] mb-3 flex items-center gap-2">
        <HelpCircle size={14} className="text-[#9b6dff]" />
        Understanding Signals
      </h3>
      <div className="space-y-3 text-[12px] text-[#a0a0c0] leading-relaxed">
        <div>
          <span className="text-[#e2e2f0] font-semibold">Composite Score</span>
          <span className="mx-1.5 text-[#9b6dff]">0–100</span>
          — The main number. Higher = stronger signal. Combines five factors:
          <ul className="mt-1 ml-4 space-y-0.5 list-disc text-[11px]">
            <li><span className="text-[#e2e2f0]">Model Confidence (40%)</span> — How sure is our model about this outcome?</li>
            <li><span className="text-[#e2e2f0]">Data Quality (20%)</span> — How many historical matches back the prediction?</li>
            <li><span className="text-[#e2e2f0]">Edge (15%)</span> — Gap between our model and the market price</li>
            <li><span className="text-[#e2e2f0]">Market Alignment (15%)</span> — Are odds trending toward our prediction?</li>
            <li><span className="text-[#e2e2f0]">Bet Type Bonus (10%)</span> — Our model is structurally better at some bet types (e.g. goal totals)</li>
          </ul>
          <div className="flex gap-3 mt-1.5 text-[10px]">
            <span className="text-[#3ddc84]">● 70+ Strong</span>
            <span className="text-[#f5a623]">● 50–69 Moderate</span>
            <span className="text-[#e84040]">● &lt;50 Filtered out</span>
          </div>
        </div>
        <div>
          <span className="text-[#e2e2f0] font-semibold">Badges</span>
          <div className="mt-1 ml-4 space-y-0.5 text-[11px]">
            <div><span className="text-[#3ddc84]">🛡 Persistent</span> — Edge has held across multiple odds snapshots (more reliable)</div>
            <div><span className="text-[#f5a623]">✨ New</span> — First time we've spotted this edge (wait for confirmation or act with caution)</div>
            <div><span className="text-[#3ddc84]">STRONG</span> — Edge ≥ 20% between model and market</div>
            <div><span className="text-[#9b6dff]">LEAN</span> — Positive edge but under 20%</div>
          </div>
        </div>
        <div>
          <span className="text-[#e2e2f0] font-semibold">Key Metrics</span>
          <div className="mt-1 ml-4 space-y-0.5 text-[11px]">
            <div><span className="text-[#e2e2f0]">Model vs Market</span> — Our Poisson model probability vs Kalshi's implied odds</div>
            <div><span className="text-[#e2e2f0]">Entry</span> — Cost in cents to buy a Yes contract on Kalshi</div>
            <div><span className="text-[#e2e2f0]">Upside</span> — Profit in cents if the bet wins (contracts pay out 100¢)</div>
            <div><span className="text-[#e2e2f0]">Confidence</span> — HIGH/MEDIUM/LOW based on historical data volume for both teams</div>
          </div>
        </div>
        <p className="text-[10px] text-[#6b6b8a] italic">Signals require positive edge and ≥45% model confidence. This is paper trading — no real money at risk.</p>
      </div>
    </div>
  )
}

export default function ActiveSignals() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [generatedAt, setGeneratedAt] = useState<string | null>(null)
  const [totalScanned, setTotalScanned] = useState<number>(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [betType, setBetType] = useState<string>('ALL')
  const [competition, setCompetition] = useState<string>('ALL')
  const [confidence, setConfidence] = useState<string>('ALL')
  const [sortBy, setSortBy] = useState<SortOption>('composite_score')
  const [showFilters, setShowFilters] = useState(false)

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    setError(null)
    try {
      const data = await fetchActiveSignals()
      // Enrich signals with odds persistence data
      let enrichedSignals = data.signals
      try {
        const oddsResp = await fetchAllOddsMovement()
        const markets = oddsResp.markets || {}
        enrichedSignals = data.signals.map((s) => {
          const movement = markets[s.market_ticker]
          return {
            ...s,
            is_persistent_edge: movement?.is_persistent ?? false,
            is_new_signal: movement?.is_new ?? true,
          }
        })
      } catch {
        // Non-critical
      }
      setSignals(enrichedSignals)
      setGeneratedAt(data.generated_at)
      setTotalScanned(data.total_matches_scanned)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load signals')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(() => load(true), REFRESH_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [load])

  // Filtered and sorted signals
  const filtered = useMemo(() => {
    let result = [...signals]
    if (betType !== 'ALL') result = result.filter((s) => s.bet_type === betType)
    if (competition !== 'ALL') result = result.filter((s) => s.competition === competition)
    if (confidence !== 'ALL') result = result.filter((s) => s.confidence === confidence)

    result.sort((a, b) => {
      switch (sortBy) {
        case 'composite_score': return (b.composite_score ?? 0) - (a.composite_score ?? 0)
        case 'edge': return b.edge - a.edge
        case 'score': return b.score - a.score
        case 'model_prob': return b.model_prob - a.model_prob
        case 'entry': return a.entry_cents - b.entry_cents
        default: return (b.composite_score ?? 0) - (a.composite_score ?? 0)
      }
    })
    return result
  }, [signals, betType, competition, confidence, sortBy])

  const summary = useMemo(() => computeSummary(filtered), [filtered])

  const formattedTime = generatedAt
    ? new Date(generatedAt).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      })
    : null

  const activeFilterCount = [betType, competition, confidence].filter((f) => f !== 'ALL').length

  return (
    <div className="px-4 md:px-8 py-6 max-w-6xl mx-auto">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <h1 className="text-xl font-semibold text-[#e2e2f0]">Active Signals</h1>
            {!loading && signals.length > 0 && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-[#9b6dff]/15 text-[#9b6dff] border border-[#9b6dff]/25">
                {signals.length}
              </span>
            )}
          </div>
          {formattedTime && (
            <p className="text-xs text-[#6b6b8a]">
              Last updated: {formattedTime}
              {totalScanned > 0 && ` · ${totalScanned} matches scanned`}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
              showFilters || activeFilterCount > 0
                ? 'bg-[#9b6dff]/10 border-[#9b6dff]/30 text-[#9b6dff]'
                : 'bg-[#16162a] border-[#1e1e3a] text-[#a0a0c0] hover:text-[#e2e2f0] hover:border-[#2e2e5a]'
            }`}
          >
            <Filter size={13} />
            Filters
            {activeFilterCount > 0 && (
              <span className="inline-flex items-center justify-center w-4 h-4 rounded-full text-[9px] font-bold bg-[#9b6dff] text-white">
                {activeFilterCount}
              </span>
            )}
          </button>
          <button
            onClick={() => load(true)}
            disabled={loading || refreshing}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-[#16162a] border border-[#1e1e3a] text-[#a0a0c0] hover:text-[#e2e2f0] hover:border-[#2e2e5a] transition-all disabled:opacity-50"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* How it works explainer */}
      {!loading && !error && signals.length > 0 && <ScoreExplainer />}

      {/* Summary cards */}
      {!loading && !error && signals.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <SummaryCard
            label="Total Signals"
            value={String(summary.totalSignals)}
            sub={`${summary.strongCount} strong`}
            icon={Zap}
            color="#9b6dff"
          />
          <SummaryCard
            label="Avg Edge"
            value={`${summary.avgEdge.toFixed(1)}%`}
            sub={`Best: ${summary.bestEdge.toFixed(1)}%`}
            icon={TrendingUp}
            color="#3ddc84"
          />
          <SummaryCard
            label="Avg Score"
            value={summary.avgScore.toFixed(0)}
            sub={`Top: ${summary.topBetType}`}
            icon={Target}
            color="#f5a623"
          />
          <SummaryCard
            label="Top League"
            value={summary.topCompetition}
            sub={`${totalScanned} matches scanned`}
            icon={BarChart3}
            color="#5b8def"
          />
        </div>
      )}

      {/* Filters panel */}
      {showFilters && !loading && (
        <div className="card p-4 mb-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-[#a0a0c0] uppercase tracking-widest">Filters</h3>
            {activeFilterCount > 0 && (
              <button
                onClick={() => { setBetType('ALL'); setCompetition('ALL'); setConfidence('ALL') }}
                className="text-[10px] text-[#9b6dff] hover:text-[#b48fff] transition-colors"
              >
                Clear all
              </button>
            )}
          </div>

          <div>
            <p className="text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium mb-2">Bet Type</p>
            <div className="flex flex-wrap gap-1.5">
              {BET_TYPES.map((t) => (
                <FilterPill key={t} label={t === 'ALL' ? 'All Types' : t.replace('_', '/')} active={betType === t} onClick={() => setBetType(t)} />
              ))}
            </div>
          </div>

          <div>
            <p className="text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium mb-2">Competition</p>
            <div className="flex flex-wrap gap-1.5">
              {COMPETITIONS.map((c) => (
                <FilterPill key={c} label={c === 'ALL' ? 'All Leagues' : c} active={competition === c} onClick={() => setCompetition(c)} />
              ))}
            </div>
          </div>

          <div>
            <p className="text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium mb-2">Confidence</p>
            <div className="flex flex-wrap gap-1.5">
              {CONFIDENCE_LEVELS.map((c) => (
                <FilterPill key={c} label={c === 'ALL' ? 'Any' : c} active={confidence === c} onClick={() => setConfidence(c)} />
              ))}
            </div>
          </div>

          <div>
            <p className="text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium mb-2">Sort By</p>
            <div className="flex flex-wrap gap-1.5">
              {SORT_OPTIONS.map((o) => (
                <FilterPill key={o.value} label={o.label} active={sortBy === o.value} onClick={() => setSortBy(o.value)} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="loading-spinner" />
          <p className="text-sm text-[#6b6b8a]">Scanning for signals…</p>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="card p-6 flex items-start gap-3 border-red-500/20">
          <AlertCircle size={18} className="text-[#e84040] shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-[#e84040]">Failed to load signals</p>
            <p className="text-xs text-[#6b6b8a] mt-1">{error}</p>
            <button
              onClick={() => load()}
              className="mt-3 text-xs text-[#9b6dff] hover:text-[#b48fff] transition-colors"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && signals.length === 0 && (
        <div className="card p-12 flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-full bg-[#9b6dff]/10 flex items-center justify-center">
            <Zap size={22} className="text-[#9b6dff]" />
          </div>
          <p className="text-sm font-medium text-[#e2e2f0]">No active signals</p>
          <p className="text-xs text-[#6b6b8a] max-w-xs">
            No high-confidence betting opportunities were found right now. Check back soon — markets update frequently.
          </p>
        </div>
      )}

      {/* Filtered empty state */}
      {!loading && !error && signals.length > 0 && filtered.length === 0 && (
        <div className="card p-8 flex flex-col items-center gap-3 text-center">
          <Filter size={20} className="text-[#6b6b8a]" />
          <p className="text-sm font-medium text-[#e2e2f0]">No signals match filters</p>
          <p className="text-xs text-[#6b6b8a]">Try adjusting your filters to see more results.</p>
          <button
            onClick={() => { setBetType('ALL'); setCompetition('ALL'); setConfidence('ALL') }}
            className="mt-2 text-xs text-[#9b6dff] hover:text-[#b48fff] transition-colors"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Signal grid */}
      {!loading && !error && filtered.length > 0 && (
        <>
          {activeFilterCount > 0 && (
            <p className="text-xs text-[#6b6b8a] mb-3">
              Showing {filtered.length} of {signals.length} signals
            </p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
