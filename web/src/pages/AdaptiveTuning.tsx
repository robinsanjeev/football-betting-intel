import { useEffect, useState } from 'react'
import { fetchAdaptiveData, triggerRetune } from '../api'
import type { AdaptiveReport, GroupStats } from '../types'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pct(v: number) {
  return `${(v * 100).toFixed(1)}%`
}

function roiColor(roi: number) {
  if (roi > 0.05) return 'text-emerald-400'
  if (roi > 0) return 'text-emerald-300'
  if (roi > -0.05) return 'text-yellow-400'
  return 'text-red-400'
}

function winRateColor(wr: number) {
  if (wr >= 0.55) return 'text-emerald-400'
  if (wr >= 0.45) return 'text-yellow-400'
  return 'text-red-400'
}

function calibColor(err: number | null) {
  if (err === null) return 'text-[#6b6b8a]'
  const abs = Math.abs(err)
  if (abs <= 0.05) return 'text-emerald-400'
  if (abs <= 0.12) return 'text-yellow-400'
  return 'text-red-400'
}

function formatTs(iso: string) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    const diff = Date.now() - d.getTime()
    const h = Math.floor(diff / 3600000)
    const m = Math.floor((diff % 3600000) / 60000)
    if (h > 48) return d.toLocaleDateString()
    if (h > 0) return `${h}h ${m}m ago`
    return `${m}m ago`
  } catch {
    return iso
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-[#12121f] border border-[#1e1e3a] rounded-xl p-5">
      <h3 className="text-sm font-semibold text-[#e2e2f0] mb-4 uppercase tracking-wider">
        {title}
      </h3>
      {children}
    </div>
  )
}

function BetTypeTable({
  byBetType,
  currentParams,
}: {
  byBetType: Record<string, GroupStats>
  currentParams: { min_edge_by_type: Record<string, number>; enabled_bet_types: string[] }
}) {
  const BET_TYPES = ['MONEYLINE', 'OVER_UNDER', 'BTTS', 'SPREAD', 'FIRST_HALF']
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-[#6b6b8a] border-b border-[#1e1e3a]">
            <th className="text-left py-2 pr-4">Type</th>
            <th className="text-right py-2 px-3">Count</th>
            <th className="text-right py-2 px-3">Win Rate</th>
            <th className="text-right py-2 px-3">ROI</th>
            <th className="text-right py-2 px-3">Min Edge</th>
            <th className="text-right py-2 px-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {BET_TYPES.map((bt) => {
            const stats = byBetType[bt]
            const minEdge = currentParams.min_edge_by_type[bt] ?? 0.08
            const enabled = currentParams.enabled_bet_types.includes(bt)
            return (
              <tr key={bt} className="border-b border-[#1a1a2e] hover:bg-[#1a1a2e]/50">
                <td className="py-2.5 pr-4 font-medium text-[#c9c9e3]">
                  {bt.replace('_', ' ')}
                </td>
                <td className="text-right px-3 text-[#9b9bb8]">
                  {stats?.count ?? '—'}
                </td>
                <td className={`text-right px-3 ${stats ? winRateColor(stats.win_rate) : 'text-[#6b6b8a]'}`}>
                  {stats ? pct(stats.win_rate) : '—'}
                </td>
                <td className={`text-right px-3 ${stats ? roiColor(stats.roi) : 'text-[#6b6b8a]'}`}>
                  {stats ? `${stats.roi >= 0 ? '+' : ''}${pct(stats.roi)}` : '—'}
                </td>
                <td className="text-right px-3 text-[#9b6dff]">
                  {pct(minEdge)}
                </td>
                <td className="text-right px-3">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      enabled
                        ? 'bg-emerald-900/40 text-emerald-400'
                        : 'bg-red-900/40 text-red-400'
                    }`}
                  >
                    {enabled ? 'ON' : 'OFF'}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function EdgeBucketTable({ byEdgeBucket }: { byEdgeBucket: Record<string, GroupStats> }) {
  const buckets = ['8-12%', '12-16%', '16-20%', '20%+']
  const chartData = buckets.map((b) => ({
    name: b,
    roi: byEdgeBucket[b] ? +(byEdgeBucket[b].roi * 100).toFixed(1) : null,
    win_rate: byEdgeBucket[b] ? +(byEdgeBucket[b].win_rate * 100).toFixed(1) : null,
    count: byEdgeBucket[b]?.count ?? 0,
  }))

  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" />
          <XAxis dataKey="name" tick={{ fill: '#6b6b8a', fontSize: 11 }} />
          <YAxis tick={{ fill: '#6b6b8a', fontSize: 11 }} unit="%" />
          <Tooltip
            contentStyle={{ background: '#12121f', border: '1px solid #1e1e3a', borderRadius: 8 }}
            labelStyle={{ color: '#e2e2f0' }}
            itemStyle={{ color: '#9b6dff' }}
            formatter={(v: number) => [`${v}%`, '']}
          />
          <ReferenceLine y={0} stroke="#6b6b8a" strokeDasharray="3 3" />
          <Bar dataKey="roi" name="ROI" fill="#9b6dff" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-[#6b6b8a] border-b border-[#1e1e3a]">
              <th className="text-left py-2 pr-4">Edge Range</th>
              <th className="text-right py-2 px-3">Count</th>
              <th className="text-right py-2 px-3">Win Rate</th>
              <th className="text-right py-2 px-3">ROI</th>
            </tr>
          </thead>
          <tbody>
            {buckets.map((b) => {
              const s = byEdgeBucket[b]
              return (
                <tr key={b} className="border-b border-[#1a1a2e] hover:bg-[#1a1a2e]/50">
                  <td className="py-2.5 pr-4 font-medium text-[#c9c9e3]">{b}</td>
                  <td className="text-right px-3 text-[#9b9bb8]">{s?.count ?? '—'}</td>
                  <td className={`text-right px-3 ${s ? winRateColor(s.win_rate) : 'text-[#6b6b8a]'}`}>
                    {s ? pct(s.win_rate) : '—'}
                  </td>
                  <td className={`text-right px-3 ${s ? roiColor(s.roi) : 'text-[#6b6b8a]'}`}>
                    {s ? `${s.roi >= 0 ? '+' : ''}${pct(s.roi)}` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ProbCalibrationTable({ calibration }: { calibration: AdaptiveReport['calibration'] }) {
  return (
    <div className="space-y-4">
      <p className="text-xs text-[#6b6b8a]">
        How well our predicted win rates match actual outcomes. Negative error = model underestimates; positive = overestimates.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-[#6b6b8a] border-b border-[#1e1e3a]">
              <th className="text-left py-2 pr-4">Prob Range</th>
              <th className="text-right py-2 px-3">Predicted</th>
              <th className="text-right py-2 px-3">Actual</th>
              <th className="text-right py-2 px-3">Error</th>
              <th className="text-right py-2 px-3">Count</th>
            </tr>
          </thead>
          <tbody>
            {calibration.map((c) => (
              <tr key={c.bucket} className="border-b border-[#1a1a2e] hover:bg-[#1a1a2e]/50">
                <td className="py-2.5 pr-4 font-medium text-[#c9c9e3]">{c.bucket}</td>
                <td className="text-right px-3 text-[#9b9bb8]">
                  {pct(c.predicted_midpoint)}
                </td>
                <td className={`text-right px-3 ${c.actual_win_rate !== null ? winRateColor(c.actual_win_rate) : 'text-[#6b6b8a]'}`}>
                  {c.actual_win_rate !== null ? pct(c.actual_win_rate) : '—'}
                </td>
                <td className={`text-right px-3 ${calibColor(c.calibration_error)}`}>
                  {c.calibration_error !== null
                    ? `${c.calibration_error >= 0 ? '+' : ''}${pct(c.calibration_error)}`
                    : '—'}
                </td>
                <td className="text-right px-3 text-[#9b9bb8]">{c.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ConfidenceTable({
  byConfidence,
  enabledConfidence,
}: {
  byConfidence: Record<string, GroupStats>
  enabledConfidence: string[]
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-[#6b6b8a] border-b border-[#1e1e3a]">
            <th className="text-left py-2 pr-4">Level</th>
            <th className="text-right py-2 px-3">Count</th>
            <th className="text-right py-2 px-3">Win Rate</th>
            <th className="text-right py-2 px-3">ROI</th>
            <th className="text-right py-2 px-3">Alpha</th>
            <th className="text-right py-2 px-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {(['HIGH', 'MEDIUM', 'LOW'] as const).map((conf) => {
            const s = byConfidence[conf]
            const enabled = enabledConfidence.includes(conf)
            return (
              <tr key={conf} className="border-b border-[#1a1a2e] hover:bg-[#1a1a2e]/50">
                <td className="py-2.5 pr-4 font-medium text-[#c9c9e3]">{conf}</td>
                <td className="text-right px-3 text-[#9b9bb8]">{s?.count ?? '—'}</td>
                <td className={`text-right px-3 ${s ? winRateColor(s.win_rate) : 'text-[#6b6b8a]'}`}>
                  {s ? pct(s.win_rate) : '—'}
                </td>
                <td className={`text-right px-3 ${s ? roiColor(s.roi) : 'text-[#6b6b8a]'}`}>
                  {s ? `${s.roi >= 0 ? '+' : ''}${pct(s.roi)}` : '—'}
                </td>
                <td className="text-right px-3 text-[#9b6dff]">
                  {/* Alpha not shown per-row (shown in params section) */}—
                </td>
                <td className="text-right px-3">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      enabled
                        ? 'bg-emerald-900/40 text-emerald-400'
                        : 'bg-red-900/40 text-red-400'
                    }`}
                  >
                    {enabled ? 'ON' : 'OFF'}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function CurrentParamsCard({
  params,
  edgeDeltas,
  alphaDeltas,
}: {
  params: AdaptiveReport['current_params']
  edgeDeltas: Record<string, number>
  alphaDeltas: Record<string, number>
}) {
  function delta(v: number) {
    if (Math.abs(v) < 0.001) return null
    return (
      <span className={v > 0 ? 'text-red-400 ml-1 text-xs' : 'text-emerald-400 ml-1 text-xs'}>
        ({v > 0 ? '+' : ''}{pct(v)})
      </span>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Min Edge */}
      <div className="bg-[#0d0d1a] rounded-lg p-4 border border-[#1e1e3a]">
        <div className="text-xs text-[#6b6b8a] uppercase tracking-wider mb-3">Min Edge by Type</div>
        {Object.entries(params.min_edge_by_type).map(([bt, v]) => (
          <div key={bt} className="flex justify-between items-center py-1 text-sm">
            <span className="text-[#9b9bb8]">{bt.replace('_', ' ')}</span>
            <span className="text-[#9b6dff] font-mono">
              {pct(v)}{delta(edgeDeltas[bt] ?? 0)}
            </span>
          </div>
        ))}
      </div>

      {/* Min Prob */}
      <div className="bg-[#0d0d1a] rounded-lg p-4 border border-[#1e1e3a]">
        <div className="text-xs text-[#6b6b8a] uppercase tracking-wider mb-3">Min Prob by Type</div>
        {Object.entries(params.min_prob_by_type).map(([bt, v]) => (
          <div key={bt} className="flex justify-between items-center py-1 text-sm">
            <span className="text-[#9b9bb8]">{bt.replace('_', ' ')}</span>
            <span className="text-[#9b6dff] font-mono">{pct(v)}</span>
          </div>
        ))}
      </div>

      {/* Shrinkage Alpha */}
      <div className="bg-[#0d0d1a] rounded-lg p-4 border border-[#1e1e3a]">
        <div className="text-xs text-[#6b6b8a] uppercase tracking-wider mb-3">Shrinkage Alpha</div>
        {Object.entries(params.shrinkage_alpha_by_conf).map(([conf, v]) => (
          <div key={conf} className="flex justify-between items-center py-1 text-sm">
            <span className="text-[#9b9bb8]">{conf}</span>
            <span className="text-[#9b6dff] font-mono">
              {v.toFixed(2)}{delta(alphaDeltas[conf] ?? 0)}
            </span>
          </div>
        ))}
        <div className="mt-3 pt-3 border-t border-[#1e1e3a] flex justify-between text-sm">
          <span className="text-[#9b9bb8]">Max Edge Cap</span>
          <span className="text-[#9b6dff] font-mono">{pct(params.max_edge)}</span>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AdaptiveTuning() {
  const [report, setReport] = useState<AdaptiveReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retuning, setRetuning] = useState(false)
  const [retuneMsg, setRetuneMsg] = useState<string | null>(null)

  async function loadReport() {
    try {
      setLoading(true)
      setError(null)
      const data = await fetchAdaptiveData()
      setReport(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load adaptive data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReport()
  }, [])

  async function handleRetune() {
    setRetuning(true)
    setRetuneMsg(null)
    try {
      const res = await triggerRetune()
      setRetuneMsg(res.message)
      if (res.success) {
        // Refresh data after retune
        await loadReport()
      }
    } catch (e: unknown) {
      setRetuneMsg(e instanceof Error ? e.message : 'Retune failed')
    } finally {
      setRetuning(false)
    }
  }

  return (
    <div className="p-5 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#e2e2f0]">Adaptive Tuning</h1>
          <p className="text-sm text-[#6b6b8a] mt-1">
            Automatic signal parameter optimization based on settled trade outcomes
          </p>
        </div>
        <button
          onClick={handleRetune}
          disabled={retuning || loading}
          className="shrink-0 px-4 py-2 rounded-lg bg-[#9b6dff]/20 hover:bg-[#9b6dff]/30 text-[#9b6dff] text-sm font-medium border border-[#9b6dff]/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {retuning ? 'Retuning…' : 'Manual Retune'}
        </button>
      </div>

      {/* Retune result message */}
      {retuneMsg && (
        <div className="bg-[#1a1a2e] border border-[#2e2e5a] rounded-lg px-4 py-3 text-sm text-[#c9c9e3]">
          {retuneMsg}
        </div>
      )}

      {/* Loading / error states */}
      {loading && (
        <div className="text-center py-16 text-[#6b6b8a]">Loading adaptive data…</div>
      )}
      {error && (
        <div className="bg-red-900/20 border border-red-700/40 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {report && !loading && (
        <>
          {/* Status Banner */}
          <div
            className={`rounded-xl p-4 border ${
              report.status === 'ACTIVE'
                ? 'bg-emerald-900/20 border-emerald-700/40'
                : 'bg-yellow-900/20 border-yellow-700/40'
            }`}
          >
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <div className={`text-sm font-semibold ${report.status === 'ACTIVE' ? 'text-emerald-400' : 'text-yellow-400'}`}>
                  {report.status === 'ACTIVE'
                    ? `Adaptive tuning: ACTIVE (v${report.version}, updated ${formatTs(report.last_updated)})`
                    : `Adaptive tuning: WARMING UP (${report.total_settled}/${report.min_samples} trades needed)`}
                </div>
                <div className="text-xs text-[#9b9bb8] mt-0.5">
                  {report.status === 'ACTIVE'
                    ? `Based on ${report.total_settled} settled trades`
                    : `${report.samples_needed} more settled trades needed before auto-tuning activates`}
                </div>
              </div>
              <div className="text-xs text-[#6b6b8a]">
                v{report.version} • {report.total_settled} samples
              </div>
            </div>
          </div>

          {/* Performance by Bet Type */}
          <Card title="Performance by Bet Type">
            <BetTypeTable
              byBetType={report.by_bet_type}
              currentParams={report.current_params}
            />
          </Card>

          {/* Performance by Edge Range */}
          <Card title="Performance by Edge Range">
            <EdgeBucketTable byEdgeBucket={report.by_edge_bucket} />
          </Card>

          {/* Probability Calibration */}
          <Card title="Probability Calibration">
            <ProbCalibrationTable calibration={report.calibration} />
          </Card>

          {/* Performance by Confidence */}
          <Card title="Performance by Confidence Level">
            <ConfidenceTable
              byConfidence={report.by_confidence}
              enabledConfidence={report.current_params.enabled_confidence}
            />
          </Card>

          {/* Current Parameters */}
          <Card title={`Current Parameters (v${report.current_params.version})`}>
            <div className="mb-3 text-xs text-[#6b6b8a]">
              Last updated: {formatTs(report.current_params.updated_at)} • {report.current_params.sample_size} samples •{' '}
              <span className={`${report.edge_deltas && Object.values(report.edge_deltas).some(v => v !== 0) ? 'text-yellow-400' : 'text-emerald-400'}`}>
                {Object.values(report.edge_deltas).some(v => v !== 0)
                  ? 'Modified from defaults'
                  : 'At defaults'}
              </span>
            </div>
            <CurrentParamsCard
              params={report.current_params}
              edgeDeltas={report.edge_deltas}
              alphaDeltas={report.alpha_deltas}
            />
          </Card>
        </>
      )}
    </div>
  )
}
