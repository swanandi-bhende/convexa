export interface DebateState {
  sessionId: string | null;
  networkName: string;
  chainId: number;
  currentRound: number;
  currentBullScore: number;
  currentBearScore: number;
  debateActive: boolean;
  bullStakeTotalEth: number;
  bearStakeTotalEth: number;
}

export interface RoundItem {
  roundNumber: number;
  bullScore: number;
  bearScore: number;
  winner: string;
  reasoning: string;
  accuracyBonusApplied: boolean;
  accuracyBonusRecipient: string | null;
  convictionUpdateStatus: string;
  timestamp: number;
  convictionTxHash: string | null;
  microSettlementTxHash: string | null;
  roundDurationSeconds: number | null;
  bullArgument: string | null;
  bearArgument: string | null;
}

export interface RoundHistoryResponse {
  sessionId: string | null;
  rounds: RoundItem[];
}

export interface MarketSnapshot {
  symbol: string;
  price: number;
  change24h: number;
  volume24h: number;
  volatility: number;
  timestamp: number;
}

async function requestJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed for ${url}`);
  }
  return (await response.json()) as T;
}

export const debateApi = {
  getDebateState: () => requestJson<DebateState>("/api/debate-state"),
  getRoundHistory: () => requestJson<RoundHistoryResponse>("/api/round-history"),
  getTransactions: () => requestJson("/api/transactions"),
  async getMarketSnapshot(): Promise<MarketSnapshot> {
    const state = await requestJson<DebateState>("/api/debate-state");
    const basePrice = 2500 + state.currentBullScore - state.currentBearScore;
    return {
      symbol: "ETH/USDC",
      price: Number(basePrice.toFixed(2)),
      change24h: Number(((state.currentBullScore - state.currentBearScore) / 10).toFixed(2)),
      volume24h: Number((state.bullStakeTotalEth * 12.4 + state.bearStakeTotalEth * 9.7).toFixed(2)),
      volatility: Number((Math.abs(state.currentBullScore - state.currentBearScore) / 1.8).toFixed(2)),
      timestamp: Date.now(),
    };
  },
};
