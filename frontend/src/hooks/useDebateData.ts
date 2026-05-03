"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { debateApi, type DebateState, type RoundHistoryResponse, type MarketSnapshot } from "@/lib/api/debateApi";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useUiSettings } from "@/hooks/useUiSettings";

interface DebateDataShape {
  state: DebateState | null;
  history: RoundHistoryResponse["rounds"];
  market: MarketSnapshot | null;
  loading: boolean;
  error: string | null;
  wsConnected: boolean;
}

const defaultMarket: MarketSnapshot = {
  symbol: "ETH/USDC",
  price: 0,
  change24h: 0,
  volume24h: 0,
  volatility: 0,
  timestamp: 0,
};

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function buildDemoArgument(side: "bull" | "bear", round: number, bullScore: number, bearScore: number): string {
  if (side === "bull") {
    return `Round ${round}: Bull argues momentum remains constructive with ${bullScore} conviction points and improving follow-through.`;
  }

  return `Round ${round}: Bear warns of fading participation with ${bearScore} conviction points and elevated downside risk.`;
}

function buildDemoRound(roundNumber: number, bullScore: number, bearScore: number): RoundHistoryResponse["rounds"][number] {
  return {
    roundNumber,
    bullScore,
    bearScore,
    winner: bullScore === bearScore ? "tie" : bullScore > bearScore ? "bull" : "bear",
    reasoning:
      bullScore === bearScore
        ? `Round ${roundNumber} closed neutral with matched conviction.`
        : `${bullScore > bearScore ? "Bull" : "Bear"} edges round ${roundNumber} after a ${Math.abs(bullScore - bearScore)} point spread.`,
    accuracyBonusApplied: false,
    accuracyBonusRecipient: null,
    convictionUpdateStatus: "simulated",
    timestamp: Date.now(),
    convictionTxHash: null,
    microSettlementTxHash: null,
    roundDurationSeconds: 60,
    bullArgument: buildDemoArgument("bull", roundNumber, bullScore, bearScore),
    bearArgument: buildDemoArgument("bear", roundNumber, bullScore, bearScore),
  };
}

function getSeedState(): DebateState {
  return {
    sessionId: "demo-session",
    networkName: "Unichain Sepolia",
    chainId: Number(process.env.NEXT_PUBLIC_CHAIN_ID || "1301"),
    currentRound: 1,
    currentBullScore: 54,
    currentBearScore: 49,
    debateActive: true,
    bullStakeTotalEth: 0.12,
    bearStakeTotalEth: 0.09,
  };
}

function getSeedHistory(seed: DebateState): RoundHistoryResponse["rounds"] {
  return [buildDemoRound(seed.currentRound, seed.currentBullScore, seed.currentBearScore)];
}

function getMarketFromState(state: DebateState): MarketSnapshot {
  const basePrice = 2500 + state.currentBullScore - state.currentBearScore;
  return {
    symbol: "ETH/USDC",
    price: Number(basePrice.toFixed(2)),
    change24h: Number(((state.currentBullScore - state.currentBearScore) / 10).toFixed(2)),
    volume24h: Number((state.bullStakeTotalEth * 12.4 + state.bearStakeTotalEth * 9.7).toFixed(2)),
    volatility: Number((Math.abs(state.currentBullScore - state.currentBearScore) / 1.8).toFixed(2)),
    timestamp: Date.now(),
  };
}

export function useDebateData(): DebateDataShape {
  const { demoMode, autoRefresh } = useUiSettings();

  const stateQuery = useQuery({
    queryKey: ["debate-state"],
    queryFn: debateApi.getDebateState,
    refetchInterval: autoRefresh ? 8000 : false,
    enabled: !demoMode,
  });

  const historyQuery = useQuery({
    queryKey: ["round-history"],
    queryFn: debateApi.getRoundHistory,
    refetchInterval: autoRefresh ? 12000 : false,
    enabled: !demoMode,
  });

  const marketQuery = useQuery({
    queryKey: ["market-snapshot"],
    queryFn: debateApi.getMarketSnapshot,
    refetchInterval: autoRefresh ? 10000 : false,
    enabled: !demoMode,
  });

  const wsUrl = typeof window !== "undefined" ? process.env.NEXT_PUBLIC_DEBATE_WS_URL ?? null : null;
  const { isConnected: wsConnected, lastMessage } = useWebSocket<Partial<DebateState>>(wsUrl, { enabled: !demoMode && Boolean(wsUrl) });

  const [demoState, setDemoState] = useState<DebateState | null>(null);
  const [demoHistory, setDemoHistory] = useState<RoundHistoryResponse["rounds"]>([]);

  useEffect(() => {
    if (!demoMode) {
      setDemoState(null);
      setDemoHistory([]);
      return;
    }

    const initial = getSeedState();
    setDemoState(initial);
    setDemoHistory(getSeedHistory(initial));
  }, [demoMode]);

  useEffect(() => {
    if (!demoMode || !autoRefresh) {
      return;
    }

    const timer = window.setInterval(() => {
      setDemoState((previous) => {
        const current = previous ?? getSeedState();
        const nextRound = current.currentRound >= 10 ? 1 : current.currentRound + 1;
        const bullNudge = (Math.random() > 0.5 ? 1 : -1) * (2 + Math.floor(Math.random() * 6));
        const bearNudge = (Math.random() > 0.5 ? 1 : -1) * (2 + Math.floor(Math.random() * 6));
        const nextBull = clampScore(current.currentBullScore + bullNudge);
        const nextBear = clampScore(current.currentBearScore + bearNudge);

        const nextState: DebateState = {
          ...current,
          currentRound: nextRound,
          currentBullScore: nextBull,
          currentBearScore: nextBear,
          debateActive: nextBull < 70 && nextBear < 70,
          bullStakeTotalEth: Number((current.bullStakeTotalEth + 0.003).toFixed(3)),
          bearStakeTotalEth: Number((current.bearStakeTotalEth + 0.002).toFixed(3)),
        };

        setDemoHistory((existing) => {
          const nextRoundEntry = buildDemoRound(nextState.currentRound, nextState.currentBullScore, nextState.currentBearScore);
          return [nextRoundEntry, ...existing.filter((item) => item.roundNumber !== nextRoundEntry.roundNumber)].slice(0, 12);
        });

        return nextState;
      });
    }, 6000);

    return () => {
      window.clearInterval(timer);
    };
  }, [demoMode, autoRefresh]);

  const resolvedState = useMemo(() => {
    if (demoMode) {
      return demoState;
    }

    if (!stateQuery.data) {
      return null;
    }

    if (!lastMessage || lastMessage.type !== "debate.update") {
      return stateQuery.data;
    }

    return { ...stateQuery.data, ...lastMessage.payload };
  }, [demoMode, demoState, lastMessage, stateQuery.data]);

  const error = useMemo(() => {
    if (demoMode) {
      return null;
    }

    const firstError = stateQuery.error || historyQuery.error || marketQuery.error;
    if (!firstError) {
      return null;
    }
    return firstError instanceof Error ? firstError.message : "Failed to load debate data.";
  }, [demoMode, historyQuery.error, marketQuery.error, stateQuery.error]);

  const resolvedHistory = useMemo(() => {
    if (demoMode) {
      return demoHistory;
    }
    return historyQuery.data?.rounds ?? [];
  }, [demoMode, demoHistory, historyQuery.data?.rounds]);

  const resolvedMarket = useMemo(() => {
    if (demoMode) {
      return demoState ? getMarketFromState(demoState) : defaultMarket;
    }

    return marketQuery.data ?? defaultMarket;
  }, [demoMode, demoState, marketQuery.data]);

  return useMemo(
    () => ({
      state: resolvedState,
      history: resolvedHistory,
      market: resolvedMarket,
      loading: demoMode ? !resolvedState : stateQuery.isLoading || historyQuery.isLoading || marketQuery.isLoading,
      error,
      wsConnected: demoMode ? false : wsConnected,
    }),
    [resolvedState, resolvedHistory, resolvedMarket, demoMode, stateQuery.isLoading, historyQuery.isLoading, marketQuery.isLoading, error, wsConnected]
  );
}
