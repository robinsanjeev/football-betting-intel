import { ExternalLink } from 'lucide-react'
import type { Signal } from '../types'

interface SignalCardProps {
  signal: Signal
}

function getEdgeBadge(edge: number) {
  const edgePct = edge * 100
  if (edgePct >= 20) {
    return (
      <span className="badge-strong">
        STRONG
      </span>
    )
  }
  return (
    <span className="badge-lean">
      LEAN
    </span>
  )
}

function getMatchQuestion(signal: Signal): string {
  const { match_title, bet_type } = signal
  const lower = bet_type.toLowerCase()
  if (lower.includes('draw') || lower.includes('btts') || lower.includes('over') || lower.includes('under')) {
    return `${match_title} — ${bet_type}?`
  }
  return `${match_title} Winner?`
}

function TeamCrest({ url, name, size = 28 }: { url: string; name: string; size?: number }) {
  if (!url) {
    return (
      <div
        className="rounded-full bg-[#1e1e3a] flex items-center justify-center text-[10px] font-bold text-[#6b6b8a] shrink-0"
        style={{ width: size, height: size }}
      >
        {name.charAt(0)}
      </div>
    )
  }
  return (
    <img
      src={url}
      alt={name}
      className="object-contain shrink-0"
      style={{ width: size, height: size }}
      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
    />
  )
}

export default function SignalCard({ signal }: SignalCardProps) {
  const upsideOn10 = ((signal.upside_cents / 100) * 10).toFixed(2)
  const displayUrl = signal.kalshi_url.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]

  // Parse team names from match_title
  const matchParts = signal.match_title.split(' vs ')
  const homeName = matchParts[0]?.trim() || ''
  const awayName = matchParts[1]?.trim() || ''

  return (
    <div className="card p-5 flex flex-col gap-4 hover:border-[#2e2e5a] transition-colors glow-purple">
      {/* Header with team crests */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Team crests */}
          <div className="flex items-center gap-1.5 shrink-0">
            <TeamCrest url={signal.home_crest} name={homeName} />
            <span className="text-[10px] text-[#6b6b8a] font-medium">vs</span>
            <TeamCrest url={signal.away_crest} name={awayName} />
          </div>
          {/* Match question + league badge */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              {signal.league_emblem && (
                <img
                  src={signal.league_emblem}
                  alt={signal.competition}
                  className="w-4 h-4 object-contain shrink-0 opacity-60"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
              )}
              <span className="text-[10px] text-[#6b6b8a] font-medium uppercase tracking-wider">{signal.competition}</span>
            </div>
            <h3 className="text-[#e2e2f0] font-semibold text-sm leading-snug mt-0.5 truncate">
              {getMatchQuestion(signal)}
            </h3>
          </div>
        </div>
        {getEdgeBadge(signal.edge)}
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium">Entry</span>
          <span className="font-mono text-lg font-semibold text-[#9b6dff]">
            {signal.entry_cents}¢
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium">Upside</span>
          <span className="font-mono text-lg font-semibold text-[#3ddc84]">
            +{signal.upside_cents}¢
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium">Score</span>
          <span className="font-mono text-lg font-semibold text-[#e2e2f0]">
            {signal.score.toFixed(1)}
          </span>
        </div>
      </div>

      {/* Bet recommendation */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#3ddc84]/[0.06] border border-[#3ddc84]/15">
        <span className="text-[#3ddc84] text-sm">→</span>
        <span className="text-[13px] font-medium text-[#e2e2f0]">{signal.description}</span>
      </div>

      {/* Model reasoning */}
      {signal.reasoning && (
        <p className="text-[11px] text-[#a0a0c0] italic leading-relaxed">
          🧠 {signal.reasoning.split('.').slice(0, 2).join('.').trim()}.        </p>
      )}

      {/* Bet type + summary */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-[#9b6dff]/10 text-[#9b6dff] border border-[#9b6dff]/20">
          {signal.bet_type.replace('_', '/')}
        </span>
        <span className="text-[11px] text-[#6b6b8a]">
          {signal.confidence} confidence · {signal.competition}
        </span>
      </div>

      {/* Model comparison box */}
      <div className="card-inset px-4 py-3 flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-[9px] uppercase tracking-widest text-[#6b6b8a] font-medium">Models</span>
          <span className="text-sm font-semibold text-[#e2e2f0]">
            Poisson{' '}
            <span className="text-[#9b6dff]">{(signal.model_prob * 100).toFixed(1)}%</span>
          </span>
        </div>

        <div className="w-px h-8 bg-[#1e1e3a]" />

        <div className="flex flex-col gap-1 text-right">
          <span className="text-[9px] uppercase tracking-widest text-[#6b6b8a] font-medium">Market</span>
          <div className="flex items-center gap-1.5 justify-end">
            <span className="text-sm font-semibold text-[#e2e2f0]">{(signal.kalshi_implied_prob * 100).toFixed(1)}%</span>
            <span className="text-xs text-[#3ddc84] font-medium">(+{(signal.edge * 100).toFixed(1)}% edge)</span>
          </div>
          <span className="text-[10px] text-[#a0a0c0] capitalize">{signal.confidence}</span>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 text-[11px] text-[#6b6b8a] pt-1 border-t border-[#1e1e3a]">
        <span>💡</span>
        <span>
          $10 bet → win{' '}
          <span className="text-[#3ddc84] font-medium">+${upsideOn10}</span>
        </span>
        <span className="text-[#1e1e3a]">·</span>
        <a
          href={signal.kalshi_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[#9b6dff] hover:text-[#b48fff] transition-colors"
        >
          <span>{displayUrl}</span>
          <ExternalLink size={10} />
        </a>
      </div>
    </div>
  )
}
