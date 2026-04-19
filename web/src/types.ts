export interface Signal {
  id: number;
  match_title: string;
  competition: string;
  bet_type: string;
  description: string;
  market_ticker: string;
  model_prob: number;
  kalshi_implied_prob: number;
  edge: number;
  ev_per_dollar: number;
  confidence: string;
  reasoning: string;
  kalshi_url: string;
  entry_cents: number;
  upside_cents: number;
  score: number;
  home_crest: string;
  away_crest: string;
  league_emblem: string;
}

export interface Trade {
  id: number;
  timestamp: string;
  match: string;
  side: string;
  stake: number;
  odds: number;
  implied_prob: number;
  result: string;
  pnl: number;
}

export interface Performance {
  total_trades: number;
  settled_trades: number;
  pending_trades: number;
  win_rate: number;
  roi: number;
  total_pnl: number;
  max_drawdown: number;
  total_staked: number;
  cumulative_pnl: { date: string; pnl: number }[];
  weekly_roi: { week: string; roi: number }[];
  win_loss_counts: { WIN: number; LOSE: number; PENDING: number };
}

export interface Accuracy {
  calibration: {
    bucket: string;
    predicted_prob: number;
    actual_win_rate: number | null;
    count: number;
  }[];
  rolling_win_rate: {
    trade_number: number;
    rolling_10_win_rate: number | null;
  }[];
  total_settled: number;
  message: string;
}

export interface ActiveSignalsResponse {
  signals: Signal[];
  generated_at: string;
  total_matches_scanned: number;
}

export interface TradesResponse {
  trades: Trade[];
  total: number;
  pending: number;
  settled: number;
}

// ---------------------------------------------------------------------------
// Model Insights
// ---------------------------------------------------------------------------

export interface TeamStrengthData {
  attack_home: number;
  attack_away: number;
  defense_home: number;
  defense_away: number;
  matches_played: number;
}

export interface ScorelineEntry {
  home_goals: number;
  away_goals: number;
  probability: number;
}

export interface GoalDistributionEntry {
  total_goals: number; // 0-6 exact; 7 = "7+"
  probability: number;
}

export interface Prob1X2 {
  home: number;
  draw: number;
  away: number;
}

export interface ProbOverUnder {
  over_1_5: number;
  over_2_5: number;
  over_3_5: number;
  over_4_5: number;
}

export interface FirstHalfProbs {
  home: number;
  draw: number;
  away: number;
}

export interface FlaggedSignal {
  id: number;
  match_title: string;
  competition: string;
  bet_type: string;
  description: string;
  market_ticker: string;
  model_prob: number;
  kalshi_implied_prob: number;
  edge: number;
  confidence: string;
  reasoning: string;
  kalshi_url: string;
  entry_cents: number;
  upside_cents: number;
  score: number;
}

export interface MatchInsight {
  match_title: string;
  competition: string;
  home_team: string;
  away_team: string;
  home_crest: string;
  away_crest: string;
  league_emblem: string;
  lambda_home: number;
  lambda_away: number;
  home_strength: TeamStrengthData;
  away_strength: TeamStrengthData;
  league_avg_home_goals: number;
  league_avg_away_goals: number;
  prob_1x2: Prob1X2;
  prob_over_under: ProbOverUnder;
  prob_btts: number;
  prob_first_half: FirstHalfProbs;
  scoreline_matrix: ScorelineEntry[];
  goal_distribution: GoalDistributionEntry[];
  market_prices: Record<string, number>;  // label → Kalshi implied prob
  flagged_signals: FlaggedSignal[];
}

export interface ModelInsightsResponse {
  matches: MatchInsight[];
}

// ---------------------------------------------------------------------------
// Adaptive Tuning
// ---------------------------------------------------------------------------

export interface AdaptiveParams {
  min_edge_by_type: Record<string, number>;
  min_prob_by_type: Record<string, number>;
  shrinkage_alpha_by_conf: Record<string, number>;
  max_edge: number;
  enabled_bet_types: string[];
  enabled_confidence: string[];
  updated_at: string;
  sample_size: number;
  version: number;
}

export interface GroupStats {
  count: number;
  wins: number;
  win_rate: number;
  total_pnl: number;
  total_staked: number;
  roi: number;
  avg_edge: number;
  avg_model_prob: number;
  calibration_error: number;
}

export interface CalibrationPoint {
  bucket: string;
  predicted_midpoint: number;
  actual_win_rate: number | null;
  count: number;
  calibration_error: number | null;
}

export interface AdaptiveReport {
  status: 'ACTIVE' | 'WARMING_UP';
  total_settled: number;
  samples_needed: number;
  min_samples: number;
  current_params: AdaptiveParams;
  default_params: AdaptiveParams;
  edge_deltas: Record<string, number>;
  alpha_deltas: Record<string, number>;
  by_bet_type: Record<string, GroupStats>;
  by_edge_bucket: Record<string, GroupStats>;
  by_prob_bucket: Record<string, GroupStats>;
  by_confidence: Record<string, GroupStats>;
  calibration: CalibrationPoint[];
  last_updated: string;
  version: number;
}

export interface RetuneResponse {
  success: boolean;
  message: string;
  new_params: AdaptiveParams | null;
  total_settled: number;
  version: number;
}
