"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { debateApi, type DebateState, type RoundHistoryResponse, type MarketSnapshot } from "@/lib/api/debateApi";
import { useWebSocket } from "@/hooks/useWebSocket";

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

export function useDebateData(): DebateDataShape {
  const stateQuery = useQuery({
    queryKey: ["debate-state"],
    queryFn: debateApi.getDebateState,
    refetchInterval: 8000,
  });

  const historyQuery = useQuery({
    queryKey: ["round-history"],
    queryFn: debateApi.getRoundHistory,
    refetchInterval: 12000,
  });

  const marketQuery = useQuery({
    queryKey: ["market-snapshot"],
    queryFn: debateApi.getMarketSnapshot,
    refetchInterval: 10000,
  });

  const wsUrl = typeof window !== "undefined" ? process.env.NEXT_PUBLIC_DEBATE_WS_URL ?? null : null;
  const { isConnected: wsConnected, lastMessage } = useWebSocket<Partial<DebateState>>(wsUrl, { enabled: Boolean(wsUrl) });

  const resolvedState = useMemo(() => {
    if (!stateQuery.data) {
      return null;
    }

    if (!lastMessage || lastMessage.type !== "debate.update") {
      return stateQuery.data;
    }

    return { ...stateQuery.data, ...lastMessage.payload };
  }, [lastMessage, stateQuery.data]);

  const error = useMemo(() => {
    const firstError = stateQuery.error || historyQuery.error || marketQuery.error;
    if (!firstError) {
      return null;
    }
    return firstError instanceof Error ? firstError.message : "Failed to load debate data.";
  }, [historyQuery.error, marketQuery.error, stateQuery.error]);

  return useMemo(
    () => ({
      state: resolvedState,
      history: historyQuery.data?.rounds ?? [],
      market: marketQuery.data ?? defaultMarket,
      loading: stateQuery.isLoading || historyQuery.isLoading || marketQuery.isLoading,
      error,
      wsConnected,
    }),
    [resolvedState, historyQuery.data?.rounds, marketQuery.data, stateQuery.isLoading, historyQuery.isLoading, marketQuery.isLoading, error, wsConnected]
  );
}
