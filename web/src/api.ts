import type {
  Signal,
  Trade,
  Performance,
  Accuracy,
  ActiveSignalsResponse,
  ModelInsightsResponse,
  TradesResponse,
} from './types'

const API_BASE = '/api'

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error')
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export async function fetchActiveSignals(): Promise<ActiveSignalsResponse> {
  return apiFetch<ActiveSignalsResponse>('/signals/active')
}

export async function fetchTrades(status?: string): Promise<TradesResponse> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : ''
  return apiFetch<TradesResponse>(`/trades${qs}`)
}

export async function fetchPerformance(): Promise<Performance> {
  return apiFetch<Performance>('/performance')
}

export async function fetchAccuracy(): Promise<Accuracy> {
  return apiFetch<Accuracy>('/accuracy')
}

export interface SignalHistoryEntry {
  id: number
  generated_at: string
  event_ticker: string
  market_ticker: string
  match_title: string
  competition: string
  bet_type: string
  description: string
  model_prob: number
  kalshi_implied_prob: number
  edge: number
  confidence: string
  reasoning: string
  kalshi_url: string
  entry_cents: number
  upside_cents: number
  score: number
  home_crest: string
  away_crest: string
  league_emblem: string
  outcome: string
  actual_pnl: number
}

export interface SignalHistoryResponse {
  signals: SignalHistoryEntry[]
  total: number
}

export async function fetchSignalHistory(params?: {
  limit?: number
  competition?: string
  bet_type?: string
  outcome?: string
}): Promise<SignalHistoryResponse> {
  const qs = new URLSearchParams()
  if (params?.limit) qs.set('limit', String(params.limit))
  if (params?.competition) qs.set('competition', params.competition)
  if (params?.bet_type) qs.set('bet_type', params.bet_type)
  if (params?.outcome) qs.set('outcome', params.outcome)
  const q = qs.toString()
  return apiFetch<SignalHistoryResponse>(`/signals/history${q ? '?' + q : ''}`)
}

export async function fetchModelInsights(): Promise<ModelInsightsResponse> {
  return apiFetch<ModelInsightsResponse>('/model-insights')
}

// Re-export types for convenience
export type { Signal, Trade, Performance, Accuracy, ActiveSignalsResponse, ModelInsightsResponse, TradesResponse }
