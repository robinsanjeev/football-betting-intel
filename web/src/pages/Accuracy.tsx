import { useState, useEffect } from 'react'
import { Target, AlertCircle, Info } from 'lucide-react'
import { fetchAccuracy } from '../api'
import { CalibrationChart, RollingWinRateChart } from '../components/CalibrationChart'
import type { Accuracy as AccuracyData } from '../types'

export default function Accuracy() {
  const [data, setData] = useState<AccuracyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAccuracy()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load accuracy data'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="px-4 md:px-8 py-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-[#e2e2f0]">Model Accuracy</h1>
        <p className="text-xs text-[#6b6b8a] mt-1">How well the model's probabilities match real outcomes</p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <div className="loading-spinner" />
          <p className="text-sm text-[#6b6b8a]">Loading accuracy data…</p>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="card p-6 flex items-start gap-3">
          <AlertCircle size={18} className="text-[#e84040] shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-[#e84040]">Failed to load accuracy data</p>
            <p className="text-xs text-[#6b6b8a] mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Not enough data */}
      {!loading && !error && data && data.total_settled === 0 && (
        <div className="card p-12 flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-12 rounded-full bg-[#9b6dff]/10 flex items-center justify-center">
            <Target size={22} className="text-[#9b6dff]" />
          </div>
          <p className="text-sm font-medium text-[#e2e2f0]">Not enough data yet</p>
          <p className="text-xs text-[#6b6b8a] max-w-sm">
            {data.message || 'Accuracy charts will appear once you have settled trades. Keep logging bets!'}
          </p>
        </div>
      )}

      {!loading && !error && data && data.total_settled > 0 && (
        <>
          {/* Summary stat */}
          <div className="card px-5 py-4 flex items-center gap-3 mb-6">
            <Info size={15} className="text-[#9b6dff] shrink-0" />
            <p className="text-xs text-[#a0a0c0]">
              Based on{' '}
              <span className="text-[#e2e2f0] font-semibold">{data.total_settled}</span>{' '}
              settled trades.{' '}
              {data.message && <span>{data.message}</span>}
            </p>
          </div>

          <div className="space-y-4">
            <CalibrationChart data={data.calibration} />
            <RollingWinRateChart data={data.rolling_win_rate} />
          </div>
        </>
      )}
    </div>
  )
}
