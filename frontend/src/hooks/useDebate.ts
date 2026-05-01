import { useEffect, useState, useCallback, useRef } from 'react';
import {
  DebateSessionResponse,
  WebSocketMessage,
  ErrorResponse,
} from '@/types/api';

/**
 * useDebateData - Fetch debate session with all rounds
 */
export function useDebateData(debateId: string) {
  const [data, setData] = useState<DebateSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [refetchCount, setRefetchCount] = useState(0);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/debates/${debateId}`);

      if (!response.ok) {
        const errorData = (await response.json()) as ErrorResponse;
        setError(errorData);
        setData(null);
        return;
      }

      const debate = (await response.json()) as DebateSessionResponse;
      setData(debate);
      setError(null);
    } catch (err) {
      setError({
        error: 'Failed to fetch debate data',
        code: 'FETCH_ERROR',
        details: { message: err instanceof Error ? err.message : String(err) },
      });
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [debateId]);

  useEffect(() => {
    fetchData();
  }, [debateId, refetchCount, fetchData]);

  const refetch = useCallback(() => {
    setRefetchCount((prev) => prev + 1);
  }, []);

  return { data, loading, error, refetch };
}

/**
 * useDebateUpdates - Subscribe to real-time SSE updates for a debate
 */
export function useDebateUpdates(
  debateId: string,
  onUpdate?: (message: WebSocketMessage) => void
) {
  const [connected, setConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Skip if debateId not available
    if (!debateId) return;

    const connectToUpdates = () => {
      try {
        const eventSource = new EventSource(
          `/api/debates/${debateId}/updates`,
          {
            withCredentials: false,
          }
        );

        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          setConnected(true);
          setConnectionError(null);
        };

        eventSource.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as WebSocketMessage;
            onUpdate?.(message);
          } catch (err) {
            console.error('Failed to parse SSE message:', err);
          }
        };

        eventSource.onerror = () => {
          setConnected(false);

          // Check if the connection was closed deliberately
          if (eventSource.readyState === EventSource.CLOSED) {
            eventSource.close();
            return;
          }

          // Attempt to reconnect after 3 seconds
          setConnectionError('Connection lost. Reconnecting...');
          setTimeout(connectToUpdates, 3000);
        };
      } catch (err) {
        setConnected(false);
        setConnectionError(
          err instanceof Error ? err.message : 'Connection error'
        );

        // Retry connection after 3 seconds
        setTimeout(connectToUpdates, 3000);
      }
    };

    connectToUpdates();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [debateId, onUpdate]);

  return { connected, connectionError };
}

/**
 * useRealTimeDebate - Combined hook for fetching + real-time updates
 */
export function useRealTimeDebate(debateId: string) {
  const { data, loading, error, refetch } = useDebateData(debateId);
  const [localData, setLocalData] = useState<DebateSessionResponse | null>(null);
  const [updates, setUpdates] = useState<WebSocketMessage[]>([]);

  const handleUpdate = useCallback((message: WebSocketMessage) => {
    setUpdates((prev) => [...prev, message]);

    // Update local debate data based on message type
    setLocalData((prev) => {
      if (!prev) return prev;

      switch (message.type) {
        case 'timer_tick': {
          const payload = message.payload as { time_remaining?: number };
          if (payload.time_remaining !== undefined) {
            return {
              ...prev,
              rounds: prev.rounds.map((round) => ({
                ...round,
                time_remaining: payload.time_remaining,
              })),
            };
          }
          return prev;
        }

        case 'conviction_updated': {
          const payload = message.payload as {
            bull_conviction?: number;
            bear_conviction?: number;
          };
          return {
            ...prev,
            currentBullConviction:
              payload.bull_conviction ?? prev.currentBullConviction,
            currentBearConviction:
              payload.bear_conviction ?? prev.currentBearConviction,
          };
        }

        case 'round_completed':
        case 'verdict_revealed':
        case 'debate_completed':
          // Refetch full data for these events
          refetch();
          return prev;

        default:
          return prev;
      }
    });
  }, [refetch]);

  const { connected, connectionError } = useDebateUpdates(
    debateId,
    handleUpdate
  );

  // Use local data if available (from updates), otherwise use fetched data
  const displayData = localData || data;

  return {
    data: displayData,
    loading,
    error,
    connected,
    connectionError,
    updates,
    refetch,
  };
}
