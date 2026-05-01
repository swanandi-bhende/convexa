/**
 * API Response Types
 * These types match the database schema and represent the actual debate data
 * returned from the backend orchestrator and stored in the database.
 */

export interface AgentRound {
  id: number;
  roundNumber: number;
  tokenPair: string;
  argument: string;
  confidence: number;
  keyMetrics: string[]; // JSON parsed from database
  rawMarketData: Record<string, unknown>; // JSON parsed from database
  axlDeliveryStatus: string;
  timestamp: string; // ISO 8601
}

export interface JudgeVerdictData {
  id: number;
  roundNumber: number;
  bullScore: number; // 0-100
  bearScore: number; // 0-100
  winner: 'bull' | 'bear';
  reasoning: string;
  bullArgumentReceived: string;
  bearArgumentReceived: string;
  accuracyBonusApplied: boolean;
  accuracyBonusRecipient?: string;
  convictionUpdateStatus: string;
  timestamp: string; // ISO 8601
}

export interface MarketDataSnapshot {
  tokenPair: string;
  currentPrice: number;
  priceChange24h: number; // percentage
  volume24h: number;
  volatility: number; // percentage
  timestamp: string; // ISO 8601
  sparkline: number[]; // Array of price points for chart
}

export interface RoundData {
  roundNumber: number;
  status: 'in-progress' | 'pending' | 'completed';
  timeRemaining?: number; // seconds (null if not in-progress)
  bullRound: AgentRound;
  bearRound: AgentRound;
  judgeVerdict?: JudgeVerdictData;
  marketData: MarketDataSnapshot;
  bullCumulativeScore: number; // Running total through all rounds
  bearCumulativeScore: number; // Running total through all rounds
}

export interface DebateSessionResponse {
  id: number;
  sessionId: string;
  tokenPair: string;
  startTime: string; // ISO 8601
  endTime?: string; // ISO 8601
  totalRounds: number;
  currentRound: number; // Current round number being debated
  winningSide?: 'bull' | 'bear';
  finalBullScore?: number;
  finalBearScore?: number;
  settlementTriggered: boolean;
  settlementTxHash?: string;
  status: 'IDLE' | 'INITIALIZING' | 'RUNNING' | 'COMPLETED' | 'SETTLED';
  currentBullConviction: number; // Cumulative conviction votes
  currentBearConviction: number; // Cumulative conviction votes
  rounds: RoundData[];
}

export interface DebateDetailResponse {
  debate: DebateSessionResponse;
  latest_round?: RoundData;
}

export interface ErrorResponse {
  error: string;
  code: string;
  details?: Record<string, unknown>;
}

/**
 * WebSocket Message Types
 */

export type WebSocketMessageType =
  | 'round_started'
  | 'round_completed'
  | 'verdict_revealed'
  | 'timer_tick'
  | 'conviction_updated'
  | 'debate_completed'
  | 'error';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  payload: unknown;
  timestamp: string; // ISO 8601
}

export interface RoundStartedPayload {
  round_number: number;
  time_remaining: number; // seconds
}

export interface RoundCompletedPayload {
  round_number: number;
  bull_score: number;
  bear_score: number;
  winner: 'bull' | 'bear';
  bull_cumulative_score: number;
  bear_cumulative_score: number;
}

export interface VerdictRevealedPayload extends RoundCompletedPayload {
  reasoning: string;
  accuracy_bonus_applied: boolean;
}

export interface TimerTickPayload {
  round_number: number;
  time_remaining: number; // seconds
  progress_percent: number; // 0-100
}

export interface ConvictionUpdatedPayload {
  bull_conviction: number;
  bear_conviction: number;
  timestamp: string;
}

export interface DebateCompletedPayload {
  final_bull_score: number;
  final_bear_score: number;
  winning_side: 'bull' | 'bear';
  settlement_tx_hash?: string;
}
