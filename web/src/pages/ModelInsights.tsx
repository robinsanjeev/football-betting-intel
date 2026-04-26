import { useState, useEffect, useCallback } from 'react'
import { AlertCircle, Microscope, ChevronDown, ExternalLink, TrendingUp } from 'lucide-react'
import { fetchModelInsights, fetchAllOddsMovement } from '../api'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import type { MatchInsight, OddsMovement } from '../types'

// ── Helpers ──────────────────────────────────────────────────────────────────

function pct(v: number) {
  return `${(v * 100).toFixed(1)}%`
}

function confidenceBg(c: string) {
  if (c === 'HIGH') return 'bg-[#3ddc84]/10 border border-[#3ddc84]/30 text-[#3ddc84]'
  if (c === 'MEDIUM') return 'bg-[#f5a623]/10 border border-[#f5a623]/30 text-[#f5a623]'
  return 'bg-[#6b6b8a]/10 border border-[#6b6b8a]/30 text-[#6b6b8a]'
}

// ── Section wrapper ──────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card p-5 space-y-4">
      <h3 className="text-xs font-semibold uppercase tracking-widest text-[#6b6b8a]">{title}</h3>
      {children}
    </section>
  )
}

// ── Horizontal bar with label ─────────────────────────────────────────────────

function HBar({
  label,
  value,
  max,
  color,
  showMark,
  markAt,
}: {
  label: string
  value: number
  max: number
  color: string
  showMark?: boolean
  markAt?: number
}) {
  const pctFill = Math.min((value / max) * 100, 100)
  const markPct = showMark && markAt != null ? Math.min((markAt / max) * 100, 100) : null

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-[#a0a0c0] w-28 shrink-0 truncate">{label}</span>
      <div className="flex-1 relative h-2 rounded-full bg-[#1e1e3a] overflow-visible">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
          style={{ width: `${pctFill}%`, backgroundColor: color }}
        />
        {/* league-average mark */}
        {markPct != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-0.5 h-4 bg-[#6b6b8a] rounded-full"
            style={{ left: `${markPct}%` }}
          />
        )}
      </div>
      <span className="text-xs font-mono text-[#e2e2f0] w-10 text-right shrink-0">
        {value.toFixed(2)}
      </span>
    </div>
  )
}

// ── Expected Goals section ──────────────────────────────────────────────────

function ExpectedGoalsSection({ insight }: { insight: MatchInsight }) {
  const max = Math.max(insight.lambda_home, insight.lambda_away, insight.league_avg_home_goals, insight.league_avg_away_goals) * 1.3

  return (
    <Section title="Expected Goals (xG)">
      <div className="space-y-3">
        <div>
          <div className="flex justify-between text-[11px] text-[#6b6b8a] mb-1.5">
            <span>{insight.home_team}</span>
            <span className="text-[10px]">League avg: {insight.league_avg_home_goals.toFixed(2)}</span>
          </div>
          <HBar
            label="λ Home"
            value={insight.lambda_home}
            max={max}
            color="#9b6dff"
            showMark
            markAt={insight.league_avg_home_goals}
          />
        </div>
        <div>
          <div className="flex justify-between text-[11px] text-[#6b6b8a] mb-1.5">
            <span>{insight.away_team}</span>
            <span className="text-[10px]">League avg: {insight.league_avg_away_goals.toFixed(2)}</span>
          </div>
          <HBar
            label="λ Away"
            value={insight.lambda_away}
            max={max}
            color="#5b8def"
            showMark
            markAt={insight.league_avg_away_goals}
          />
        </div>
      </div>
      <p className="text-[10px] text-[#6b6b8a]">
        Grey line = league average. Bar length shows model-predicted expected goals for this fixture.
      </p>
    </Section>
  )
}

// ── Team Strengths section ──────────────────────────────────────────────────

function StrengthRow({
  label,
  home,
  away,
  color,
}: {
  label: string
  home: number
  away: number
  color: string
}) {
  const leagueAvg = 1.0
  const max = 2.5

  return (
    <div className="space-y-1.5 mb-4">
      <div className="text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium">{label}</div>
      <div className="grid grid-cols-2 gap-3">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative h-1.5 rounded-full bg-[#1e1e3a] overflow-visible">
            <div
              className="absolute inset-y-0 left-0 rounded-full"
              style={{ width: `${Math.min((home / max) * 100, 100)}%`, backgroundColor: color }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-0.5 h-3.5 bg-[#6b6b8a] rounded-full"
              style={{ left: `${(leagueAvg / max) * 100}%` }}
            />
          </div>
          <span
            className="text-xs font-mono w-10 text-right shrink-0"
            style={{ color: home > 1.05 ? '#3ddc84' : home < 0.95 ? '#e84040' : '#a0a0c0' }}
          >
            {home.toFixed(2)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 relative h-1.5 rounded-full bg-[#1e1e3a] overflow-visible">
            <div
              className="absolute inset-y-0 left-0 rounded-full"
              style={{ width: `${Math.min((away / max) * 100, 100)}%`, backgroundColor: color }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-0.5 h-3.5 bg-[#6b6b8a] rounded-full"
              style={{ left: `${(leagueAvg / max) * 100}%` }}
            />
          </div>
          <span
            className="text-xs font-mono w-10 text-right shrink-0"
            style={{ color: away > 1.05 ? '#3ddc84' : away < 0.95 ? '#e84040' : '#a0a0c0' }}
          >
            {away.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  )
}

function TeamStrengthsSection({ insight }: { insight: MatchInsight }) {
  const h = insight.home_strength
  const a = insight.away_strength

  return (
    <Section title="Team Strengths (1.0 = league average)">
      {/* Column headers */}
      <div className="grid grid-cols-2 gap-3 mb-2">
        <div className="flex items-center gap-2">
          {insight.home_crest && (
            <img src={insight.home_crest} alt="" className="w-5 h-5 object-contain" />
          )}
          <span className="text-xs font-medium text-[#e2e2f0] truncate">{insight.home_team}</span>
          <span className="text-[10px] text-[#6b6b8a]">({h.matches_played} games)</span>
        </div>
        <div className="flex items-center gap-2">
          {insight.away_crest && (
            <img src={insight.away_crest} alt="" className="w-5 h-5 object-contain" />
          )}
          <span className="text-xs font-medium text-[#e2e2f0] truncate">{insight.away_team}</span>
          <span className="text-[10px] text-[#6b6b8a]">({a.matches_played} games)</span>
        </div>
      </div>

      <StrengthRow label="Attack (Home)" home={h.attack_home} away={a.attack_home} color="#9b6dff" />
      <StrengthRow label="Attack (Away)" home={h.attack_away} away={a.attack_away} color="#9b6dff" />
      <StrengthRow label="Defense (Home)" home={h.defense_home} away={a.defense_home} color="#ff8c42" />
      <StrengthRow label="Defense (Away)" home={h.defense_away} away={a.defense_away} color="#ff8c42" />

      <p className="text-[10px] text-[#6b6b8a]">
        Grey line = average (1.0). Attack &gt; 1.0 = prolific scorer. Defense &gt; 1.0 = leaky defence.
        <span className="ml-1 text-[#3ddc84]">Green</span> = above avg, <span className="text-[#e84040]">Red</span> = below avg.
      </p>
    </Section>
  )
}

// ── Scoreline heatmap ────────────────────────────────────────────────────────

function ScorelineHeatmap({ insight }: { insight: MatchInsight }) {
  // Build 6×6 lookup
  const probMap: Record<string, number> = {}
  let maxProb = 0
  for (const entry of insight.scoreline_matrix) {
    if (entry.home_goals <= 5 && entry.away_goals <= 5) {
      const key = `${entry.home_goals}-${entry.away_goals}`
      probMap[key] = entry.probability
      if (entry.probability > maxProb) maxProb = entry.probability
    }
  }

  // Find the most likely scoreline in top 20
  const topEntry = insight.scoreline_matrix[0]

  return (
    <Section title="Scoreline Probability Heatmap">
      <div className="text-[10px] text-[#6b6b8a] mb-3">
        Rows = Home goals (0–5) · Columns = Away goals (0–5) · Colour intensity = probability
      </div>
      <div className="overflow-x-auto">
        <table className="border-collapse text-center text-[10px] font-mono">
          <thead>
            <tr>
              <th className="w-8 h-8 text-[#6b6b8a] font-normal">H↓ A→</th>
              {[0, 1, 2, 3, 4, 5].map((a) => (
                <th key={a} className="w-12 h-8 text-[#6b6b8a] font-semibold">{a}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[0, 1, 2, 3, 4, 5].map((h) => (
              <tr key={h}>
                <td className="w-8 h-10 text-[#6b6b8a] font-semibold">{h}</td>
                {[0, 1, 2, 3, 4, 5].map((a) => {
                  const key = `${h}-${a}`
                  const prob = probMap[key] ?? 0
                  const isTop = topEntry && topEntry.home_goals === h && topEntry.away_goals === a
                  const intensity = maxProb > 0 ? prob / maxProb : 0

                  return (
                    <td
                      key={a}
                      className="w-12 h-10 rounded transition-all relative border border-[#1e1e3a]"
                      style={{
                        backgroundColor: isTop
                          ? `rgba(155, 109, 255, ${0.15 + intensity * 0.7})`
                          : `rgba(91, 141, 239, ${intensity * 0.65})`,
                        border: isTop ? '1.5px solid rgba(155,109,255,0.7)' : undefined,
                      }}
                    >
                      {prob > 0 && (
                        <span className="text-[9px] font-mono text-[#e2e2f0]">
                          {(prob * 100).toFixed(1)}%
                        </span>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {topEntry && (
        <p className="text-xs text-[#a0a0c0] mt-2">
          Most likely scoreline:{' '}
          <span className="text-[#9b6dff] font-semibold">
            {topEntry.home_goals}–{topEntry.away_goals}
          </span>{' '}
          ({(topEntry.probability * 100).toFixed(1)}%)
        </p>
      )}
    </Section>
  )
}

// ── Goal distribution bar chart ───────────────────────────────────────────────

function GoalDistributionSection({ insight }: { insight: MatchInsight }) {
  const dist = insight.goal_distribution
  const maxP = Math.max(...dist.map((d) => d.probability), 0.01)

  return (
    <Section title="Goal Distribution">
      <div className="text-[10px] text-[#6b6b8a] mb-3">
        Probability of each total-goals outcome. Orange line marks Over 2.5.
      </div>

      {/* Chart area */}
      <div className="relative">
        {/* Over 2.5 boundary line — sits between index 2 and 3 */}
        <div
          className="absolute top-0 bottom-6 w-0.5 bg-[#f5a623]/60 rounded-full z-10"
          style={{ left: `calc(${(2.5 / dist.length) * 100}% + ${(0.75 * 2.5)}px)` }}
        />

        <div className="flex items-end gap-1.5" style={{ height: '140px' }}>
          {dist.map((entry) => {
            const heightPct = (entry.probability / maxP) * 100
            const label = entry.total_goals === 7 ? '7+' : String(entry.total_goals)
            return (
              <div key={entry.total_goals} className="flex-1 flex flex-col justify-end items-center h-full">
                {/* Probability label above bar */}
                <span className="text-[9px] font-mono text-[#a0a0c0] mb-1">
                  {(entry.probability * 100).toFixed(1)}%
                </span>
                {/* Bar — grows upward from bottom */}
                <div
                  className="w-full rounded-t transition-all duration-500"
                  style={{
                    height: `${heightPct}%`,
                    minHeight: '3px',
                    backgroundColor: entry.total_goals <= 2 ? '#5b8def' : '#9b6dff',
                  }}
                />
                {/* Goal count label */}
                <span className="text-[10px] text-[#6b6b8a] font-mono mt-1.5">{label}</span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="flex items-center gap-2 mt-3">
        <div className="w-4 h-0.5 bg-[#f5a623]/70 rounded" />
        <span className="text-[10px] text-[#6b6b8a]">Over 2.5 boundary — blue bars (≤2 goals) vs purple bars (3+ goals)</span>
      </div>
    </Section>
  )
}

// ── Market probabilities ──────────────────────────────────────────────────────

function ProbRow({
  label,
  modelProb,
  marketProb,
}: {
  label: string
  modelProb: number
  marketProb?: number
}) {
  const edge = marketProb != null ? modelProb - marketProb : null
  return (
    <div className="flex items-center justify-between gap-3 py-2 border-b border-[#1e1e3a] last:border-0">
      <span className="text-xs text-[#a0a0c0] flex-1">{label}</span>
      <span className="text-xs font-mono text-[#e2e2f0] w-14 text-right">{pct(modelProb)}</span>
      {marketProb != null ? (
        <>
          <span className="text-xs font-mono text-[#6b6b8a] w-14 text-right">{pct(marketProb)}</span>
          <span
            className={`text-xs font-mono w-16 text-right ${edge && edge > 0 ? 'text-[#3ddc84]' : 'text-[#e84040]'}`}
          >
            {edge != null ? (edge > 0 ? '+' : '') + pct(edge) : '—'}
          </span>
        </>
      ) : (
        <>
          <span className="text-xs text-[#6b6b8a] w-14 text-right">—</span>
          <span className="text-xs text-[#6b6b8a] w-16 text-right">—</span>
        </>
      )}
    </div>
  )
}

function MarketProbabilitiesSection({ insight }: { insight: MatchInsight }) {
  const mp = insight.market_prices ?? {}

  return (
    <Section title="Market Probabilities">
      {/* Column header row */}
      <div className="flex items-center justify-between gap-3 pb-1 text-[10px] uppercase tracking-widest text-[#6b6b8a] border-b border-[#1e1e3a]">
        <span className="flex-1">Market</span>
        <span className="w-14 text-right">Model</span>
        <span className="w-14 text-right">Market</span>
        <span className="w-16 text-right">Edge</span>
      </div>

      {/* 1X2 */}
      <ProbRow label="Home Win (1X2)" modelProb={insight.prob_1x2.home} marketProb={mp.home_win} />
      <ProbRow label="Draw (1X2)" modelProb={insight.prob_1x2.draw} marketProb={mp.draw} />
      <ProbRow label="Away Win (1X2)" modelProb={insight.prob_1x2.away} marketProb={mp.away_win} />

      {/* Totals */}
      <ProbRow label="Over 1.5 Goals" modelProb={insight.prob_over_under.over_1_5} marketProb={mp.over_1_5} />
      <ProbRow label="Over 2.5 Goals" modelProb={insight.prob_over_under.over_2_5} marketProb={mp.over_2_5} />
      <ProbRow label="Over 3.5 Goals" modelProb={insight.prob_over_under.over_3_5} marketProb={mp.over_3_5} />
      <ProbRow label="Over 4.5 Goals" modelProb={insight.prob_over_under.over_4_5} marketProb={mp.over_4_5} />

      {/* BTTS */}
      <ProbRow label="Both Teams to Score" modelProb={insight.prob_btts} marketProb={mp.btts_yes} />

      {/* First half */}
      <ProbRow label="1H Home Win" modelProb={insight.prob_first_half.home} marketProb={mp.fh_home} />
      <ProbRow label="1H Draw" modelProb={insight.prob_first_half.draw} marketProb={mp.fh_draw} />
      <ProbRow label="1H Away Win" modelProb={insight.prob_first_half.away} marketProb={mp.fh_away} />
    </Section>
  )
}

// ── Flagged signals ───────────────────────────────────────────────────────────

function FlaggedSignalsSection({ insight }: { insight: MatchInsight }) {
  if (insight.flagged_signals.length === 0) {
    return (
      <Section title="Flagged Signals">
        <p className="text-xs text-[#6b6b8a]">No signals with edge ≥ 5% were identified for this match.</p>
      </Section>
    )
  }

  return (
    <Section title="Flagged Signals">
      <div className="space-y-3">
        {insight.flagged_signals.map((sig) => (
          <div key={sig.market_ticker} className="card-inset p-4 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="text-xs font-semibold text-[#e2e2f0]">{sig.description}</span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] uppercase tracking-widest text-[#6b6b8a]">{sig.bet_type}</span>
                  <span className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded ${confidenceBg(sig.confidence)}`}>
                    {sig.confidence}
                  </span>
                </div>
              </div>
              <a
                href={sig.kalshi_url}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 flex items-center gap-1 text-[10px] text-[#9b6dff] hover:text-[#b48fff] transition-colors"
              >
                Kalshi <ExternalLink size={10} />
              </a>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="card-inset p-2 text-center">
                <p className="text-[9px] text-[#6b6b8a] uppercase tracking-widest">Model</p>
                <p className="text-sm font-mono font-semibold text-[#9b6dff]">{pct(sig.model_prob)}</p>
              </div>
              <div className="card-inset p-2 text-center">
                <p className="text-[9px] text-[#6b6b8a] uppercase tracking-widest">Kalshi</p>
                <p className="text-sm font-mono font-semibold text-[#a0a0c0]">{pct(sig.kalshi_implied_prob)}</p>
              </div>
              <div className="card-inset p-2 text-center">
                <p className="text-[9px] text-[#6b6b8a] uppercase tracking-widest">Edge</p>
                <p className="text-sm font-mono font-semibold text-[#3ddc84]">+{pct(sig.edge)}</p>
              </div>
            </div>

            {sig.reasoning && (
              <p className="text-[10px] text-[#6b6b8a] leading-relaxed">{sig.reasoning}</p>
            )}
          </div>
        ))}
      </div>
    </Section>
  )
}

// ── Match header ──────────────────────────────────────────────────────────────

function MatchHeader({ insight }: { insight: MatchInsight }) {
  return (
    <div className="card p-5 mb-4">
      <div className="flex items-center justify-center gap-6 flex-wrap">
        {/* Home */}
        <div className="flex flex-col items-center gap-2 min-w-[80px]">
          {insight.home_crest ? (
            <img src={insight.home_crest} alt={insight.home_team} className="w-12 h-12 object-contain" />
          ) : (
            <div className="w-12 h-12 rounded-full bg-[#1e1e3a] flex items-center justify-center text-lg font-bold text-[#9b6dff]">
              {insight.home_team[0]}
            </div>
          )}
          <span className="text-xs font-medium text-[#e2e2f0] text-center max-w-[100px] leading-tight">{insight.home_team}</span>
        </div>

        {/* Centre info */}
        <div className="flex flex-col items-center gap-1.5">
          <div className="flex items-center gap-2">
            {insight.league_emblem && (
              <img src={insight.league_emblem} alt={insight.competition} className="w-5 h-5 object-contain" />
            )}
            <span className="text-[11px] font-semibold text-[#6b6b8a] uppercase tracking-widest">{insight.competition}</span>
          </div>
          {insight.kickoff_utc && (
            <span className="text-[11px] text-[#a0a0c0] font-medium">
              {(() => {
                const d = new Date(insight.kickoff_utc)
                const dateStr = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
                // Only show time if it's not midnight (i.e. we have actual kickoff time)
                const hasTime = d.getHours() !== 0 || d.getMinutes() !== 0
                return hasTime ? `${dateStr} · ${d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}` : dateStr
              })()}
            </span>
          )}
          <div className="text-2xl font-bold text-[#9b6dff]">vs</div>
          <div className="flex items-center gap-3 text-[11px] text-[#6b6b8a]">
            <span>λ {insight.lambda_home.toFixed(2)}</span>
            <span className="text-[#1e1e3a]">|</span>
            <span>λ {insight.lambda_away.toFixed(2)}</span>
          </div>
          {insight.flagged_signals.length > 0 && (
            <div className="flex items-center gap-1 text-[10px] text-[#3ddc84] bg-[#3ddc84]/10 border border-[#3ddc84]/20 px-2 py-0.5 rounded-full">
              <TrendingUp size={10} />
              {insight.flagged_signals.length} signal{insight.flagged_signals.length !== 1 ? 's' : ''}
            </div>
          )}
        </div>

        {/* Away */}
        <div className="flex flex-col items-center gap-2 min-w-[80px]">
          {insight.away_crest ? (
            <img src={insight.away_crest} alt={insight.away_team} className="w-12 h-12 object-contain" />
          ) : (
            <div className="w-12 h-12 rounded-full bg-[#1e1e3a] flex items-center justify-center text-lg font-bold text-[#5b8def]">
              {insight.away_team[0]}
            </div>
          )}
          <span className="text-xs font-medium text-[#e2e2f0] text-center max-w-[100px] leading-tight">{insight.away_team}</span>
        </div>
      </div>
    </div>
  )
}

// ── Odds Movement section ──────────────────────────────────────────────────────

function OddsMovementSection({ insight, oddsData }: { insight: MatchInsight; oddsData: Record<string, OddsMovement> }) {
  // Find all market tickers from flagged signals and match markets
  const relevantTickers = insight.flagged_signals.map((s) => s.market_ticker)
  const movements = relevantTickers
    .map((ticker) => oddsData[ticker])
    .filter((m): m is OddsMovement => m != null && m.snapshots.length > 0)

  if (movements.length === 0) {
    return (
      <Section title="Odds Movement">
        <p className="text-xs text-[#6b6b8a]">No odds snapshots recorded yet. Trigger a snapshot from the API to start tracking line movement.</p>
      </Section>
    )
  }

  return (
    <Section title="Odds Movement">
      <p className="text-[10px] text-[#6b6b8a] mb-3">
        Kalshi implied probability over time for flagged markets. Purple = Kalshi odds, Blue = Model probability.
      </p>
      <div className="space-y-4">
        {movements.map((movement) => {
          const chartData = movement.snapshots.map((s) => ({
            time: new Date(s.snapshot_time).toLocaleTimeString('en-US', {
              month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
            }),
            kalshi: Math.round(s.kalshi_implied_prob * 1000) / 10,
            model: Math.round(s.model_prob * 1000) / 10,
          }))

          return (
            <div key={movement.market_ticker} className="card-inset p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono text-[#a0a0c0]">{movement.market_ticker}</span>
                <div className="flex items-center gap-2">
                  {movement.is_persistent ? (
                    <span className="text-[9px] px-2 py-0.5 rounded-full bg-[#3ddc84]/15 text-[#3ddc84] border border-[#3ddc84]/25 font-semibold">
                      PERSISTENT EDGE
                    </span>
                  ) : movement.is_new ? (
                    <span className="text-[9px] px-2 py-0.5 rounded-full bg-[#f5a623]/15 text-[#f5a623] border border-[#f5a623]/25 font-semibold">
                      NEW
                    </span>
                  ) : null}
                  <span className="text-[10px] text-[#6b6b8a]">{movement.total_snapshots} snapshot{movement.total_snapshots !== 1 ? 's' : ''}</span>
                </div>
              </div>
              <div style={{ height: 150 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" />
                    <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#6b6b8a' }} />
                    <YAxis tick={{ fontSize: 9, fill: '#6b6b8a' }} domain={['auto', 'auto']} unit="%" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#16162a', border: '1px solid #2e2e5a', borderRadius: 8, fontSize: 11 }}
                      labelStyle={{ color: '#a0a0c0' }}
                    />
                    <Line type="monotone" dataKey="kalshi" stroke="#9b6dff" strokeWidth={2} dot={false} name="Kalshi" />
                    <Line type="monotone" dataKey="model" stroke="#5b8def" strokeWidth={2} dot={false} name="Model" />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )
        })}
      </div>
    </Section>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ModelInsights() {
  const [matches, setMatches] = useState<MatchInsight[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedMatch, setSelectedMatch] = useState<string | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [oddsData, setOddsData] = useState<Record<string, OddsMovement>>({})

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchModelInsights()
      // Sort by kickoff date (nearest first), null dates at the end
      const sorted = [...data.matches].sort((a, b) => {
        if (!a.kickoff_utc && !b.kickoff_utc) return 0
        if (!a.kickoff_utc) return 1
        if (!b.kickoff_utc) return -1
        return new Date(a.kickoff_utc).getTime() - new Date(b.kickoff_utc).getTime()
      })
      setMatches(sorted)
      if (sorted.length > 0 && !selectedMatch) {
        setSelectedMatch(sorted[0].match_title)
      }
      // Fetch odds movement data
      try {
        const oddsResp = await fetchAllOddsMovement()
        setOddsData(oddsResp.markets || {})
      } catch {
        // Non-critical, just skip
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load model insights')
    } finally {
      setLoading(false)
    }
  }, [selectedMatch])

  useEffect(() => {
    load()
  }, [])

  const insight = matches.find((m) => m.match_title === selectedMatch) ?? null

  return (
    <div className="px-4 md:px-8 py-6 max-w-5xl mx-auto">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <Microscope size={18} className="text-[#9b6dff]" />
            <h1 className="text-xl font-semibold text-[#e2e2f0]">Model Insights</h1>
          </div>
          <p className="text-xs text-[#6b6b8a]">
            Deep-dive into the Calibrated Poisson model predictions for each upcoming match.
          </p>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="loading-spinner" />
          <p className="text-sm text-[#6b6b8a]">Running model pipeline…</p>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="card p-6 flex items-start gap-3">
          <AlertCircle size={18} className="text-[#e84040] shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-[#e84040]">Failed to load model insights</p>
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

      {/* Empty */}
      {!loading && !error && matches.length === 0 && (
        <div className="card p-12 flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-full bg-[#9b6dff]/10 flex items-center justify-center">
            <Microscope size={22} className="text-[#9b6dff]" />
          </div>
          <p className="text-sm font-medium text-[#e2e2f0]">No matches available</p>
          <p className="text-xs text-[#6b6b8a] max-w-xs">
            No upcoming matches were found on Kalshi. Check back when new fixtures are listed.
          </p>
        </div>
      )}

      {/* Match selector + content */}
      {!loading && !error && matches.length > 0 && (
        <>
          {/* Match selector dropdown */}
          <div className="relative mb-6">
            <button
              onClick={() => setDropdownOpen((o) => !o)}
              className="w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-[#16162a] border border-[#1e1e3a] text-left hover:border-[#2e2e5a] transition-colors"
            >
              <div className="flex items-center gap-3 min-w-0">
                {insight?.league_emblem && (
                  <img src={insight.league_emblem} alt="" className="w-5 h-5 object-contain shrink-0" />
                )}
                <span className="text-sm font-medium text-[#e2e2f0] truncate">
                  {selectedMatch ?? 'Select a match…'}
                </span>
                {insight && insight.flagged_signals.length > 0 && (
                  <span className="shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#3ddc84]/15 text-[#3ddc84] border border-[#3ddc84]/25">
                    {insight.flagged_signals.length} signal{insight.flagged_signals.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <ChevronDown
                size={16}
                className={`text-[#6b6b8a] transition-transform shrink-0 ${dropdownOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {dropdownOpen && (
              <div className="absolute top-full left-0 right-0 mt-1 rounded-xl bg-[#16162a] border border-[#1e1e3a] z-20 max-h-64 overflow-y-auto shadow-xl">
                {matches.map((m) => (
                  <button
                    key={m.match_title}
                    onClick={() => {
                      setSelectedMatch(m.match_title)
                      setDropdownOpen(false)
                    }}
                    className={`w-full flex items-center justify-between gap-3 px-4 py-3 text-left text-sm transition-colors hover:bg-white/5 ${
                      m.match_title === selectedMatch ? 'text-[#9b6dff] bg-[#9b6dff]/5' : 'text-[#a0a0c0]'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {m.league_emblem && (
                        <img src={m.league_emblem} alt="" className="w-4 h-4 object-contain shrink-0" />
                      )}
                      <span className="truncate">{m.match_title}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] text-[#6b6b8a]">
                        {m.competition}
                        {m.kickoff_utc && (
                          <span className="ml-1 text-[#a0a0c0]">
                            · {new Date(m.kickoff_utc).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                        )}
                      </span>
                      {m.flagged_signals.length > 0 && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-[#3ddc84]/15 text-[#3ddc84]">
                          {m.flagged_signals.length}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Click outside to close dropdown */}
          {dropdownOpen && (
            <div className="fixed inset-0 z-10" onClick={() => setDropdownOpen(false)} />
          )}

          {/* Match details */}
          {insight && (
            <div className="space-y-4">
              <MatchHeader insight={insight} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <ExpectedGoalsSection insight={insight} />
                <TeamStrengthsSection insight={insight} />
              </div>
              <ScorelineHeatmap insight={insight} />
              <GoalDistributionSection insight={insight} />
              <MarketProbabilitiesSection insight={insight} />
              <FlaggedSignalsSection insight={insight} />
              <OddsMovementSection insight={insight} oddsData={oddsData} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
