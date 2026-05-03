"use client";

import { useEffect, useMemo, useRef, useState } from "react";

export interface WebSocketMessage<T = unknown> {
  type: string;
  payload: T;
}

interface UseWebSocketOptions {
  enabled?: boolean;
  reconnectMs?: number;
}

export function useWebSocket<T = unknown>(url: string | null, options: UseWebSocketOptions = {}) {
  const { enabled = true, reconnectMs = 2500 } = options;
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage<T> | null>(null);

  useEffect(() => {
    if (!enabled || !url) {
      return;
    }

    let cancelled = false;

    const connect = () => {
      if (cancelled) {
        return;
      }

      const ws = new WebSocket(url);
      socketRef.current = ws;

      ws.onopen = () => {
        if (!cancelled) {
          setIsConnected(true);
        }
      };

      ws.onclose = () => {
        if (cancelled) {
          return;
        }

        setIsConnected(false);
        reconnectRef.current = window.setTimeout(connect, reconnectMs);
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as WebSocketMessage<T>;
          setLastMessage(parsed);
        } catch {
          setLastMessage({ type: "raw", payload: event.data as T });
        }
      };
    };

    connect();

    return () => {
      cancelled = true;
      setIsConnected(false);
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current);
      }
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [enabled, reconnectMs, url]);

  const send = useMemo(
    () => (message: unknown) => {
      if (socketRef.current?.readyState !== WebSocket.OPEN) {
        return false;
      }
      socketRef.current.send(JSON.stringify(message));
      return true;
    },
    []
  );

  return { isConnected, lastMessage, send };
}
