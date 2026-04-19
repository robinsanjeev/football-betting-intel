import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import type { Trade } from '../types'

interface TradeTableProps {
  trades: Trade[]
}

type SortKey = keyof Trade
type SortDir = 'asc' | 'desc' | null

function ResultBadge({ result }: { result: string }) {
  const upper = result.toUpperCase()
  if (upper === 'WIN') return <span className="badge-win">WIN</span>
  if (upper === 'LOSE' || upper === 'LOSS') return <span className="badge-lose">LOSE</span>
  return <span className="badge-pending">PENDING</span>
}

function PnlCell({ pnl }: { pnl: number }) {
  if (pnl === 0) return <span className="font-mono text-xs text-[#6b6b8a]">—</span>
  const color = pnl > 0 ? 'text-[#3ddc84]' : 'text-[#e84040]'
  return (
    <span className={`font-mono text-xs font-semibold ${color}`}>
      {pnl > 0 ? '+' : ''}${pnl.toFixed(2)}
    </span>
  )
}

function SortIcon({ col, sortKey, sortDir }: { col: SortKey; sortKey: SortKey | null; sortDir: SortDir }) {
  if (sortKey !== col) return <ChevronsUpDown size={12} className="text-[#2a2a4a]" />
  if (sortDir === 'asc') return <ChevronUp size={12} className="text-[#9b6dff]" />
  return <ChevronDown size={12} className="text-[#9b6dff]" />
}

const COLUMNS: { key: SortKey; label: string; align?: string }[] = [
  { key: 'id', label: '#' },
  { key: 'timestamp', label: 'Date' },
  { key: 'match', label: 'Match' },
  { key: 'side', label: 'Bet' },
  { key: 'stake', label: 'Stake', align: 'right' },
  { key: 'odds', label: 'Odds', align: 'right' },
  { key: 'implied_prob', label: 'Implied%', align: 'right' },
  { key: 'result', label: 'Result', align: 'center' },
  { key: 'pnl', label: 'PnL', align: 'right' },
]

export default function TradeTable({ trades }: TradeTableProps) {
  const [sortKey, setSortKey] = useState<SortKey | null>('timestamp')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : d === 'desc' ? null : 'asc'))
      if (sortDir === null) setSortKey(null)
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = [...trades].sort((a, b) => {
    if (!sortKey || !sortDir) return 0
    const av = a[sortKey]
    const bv = b[sortKey]
    if (av === bv) return 0
    const cmp = av < bv ? -1 : 1
    return sortDir === 'asc' ? cmp : -cmp
  })

  if (trades.length === 0) {
    return (
      <div className="card p-10 flex items-center justify-center">
        <p className="text-[#6b6b8a] text-sm">No trades found</p>
      </div>
    )
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#1e1e3a]">
              {COLUMNS.map(({ key, label, align }) => (
                <th
                  key={key}
                  onClick={() => handleSort(key)}
                  className={`px-4 py-3 text-[10px] uppercase tracking-widest text-[#6b6b8a] font-medium cursor-pointer hover:text-[#a0a0c0] select-none whitespace-nowrap ${
                    align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
                  }`}
                >
                  <span className="inline-flex items-center gap-1">
                    {label}
                    <SortIcon col={key} sortKey={sortKey} sortDir={sortDir} />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((trade, idx) => (
              <tr
                key={trade.id}
                className={`border-b border-[#1e1e3a]/50 hover:bg-white/[0.02] transition-colors ${
                  idx % 2 === 0 ? '' : 'bg-white/[0.01]'
                }`}
              >
                <td className="px-4 py-3 text-[#6b6b8a] font-mono">{trade.id}</td>
                <td className="px-4 py-3 text-[#a0a0c0] whitespace-nowrap">
                  {new Date(trade.timestamp).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </td>
                <td className="px-4 py-3 text-[#e2e2f0] max-w-[200px] truncate">{trade.match}</td>
                <td className="px-4 py-3 text-[#a0a0c0]">{trade.side}</td>
                <td className="px-4 py-3 text-right text-[#e2e2f0] font-mono">${trade.stake.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-[#a0a0c0] font-mono">{trade.odds.toFixed(2)}</td>
                <td className="px-4 py-3 text-right text-[#a0a0c0] font-mono">
                  {(trade.implied_prob * 100).toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-center">
                  <ResultBadge result={trade.result} />
                </td>
                <td className="px-4 py-3 text-right">
                  <PnlCell pnl={trade.pnl} />
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-[#1e1e3a]">
              <td colSpan={4} className="px-4 py-3 text-[10px] text-[#6b6b8a]">
                {trades.length} trade{trades.length !== 1 ? 's' : ''}
              </td>
              <td className="px-4 py-3 text-right font-mono text-xs text-[#a0a0c0]">
                ${trades.reduce((s, t) => s + t.stake, 0).toFixed(2)}
              </td>
              <td colSpan={3} />
              <td className="px-4 py-3 text-right">
                <PnlCell pnl={trades.reduce((s, t) => s + t.pnl, 0)} />
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
