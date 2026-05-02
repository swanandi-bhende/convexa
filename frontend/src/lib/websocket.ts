"use client";

import React, { useEffect, useRef } from "react";
import { decodeEventLog, keccak256, stringToHex, type Hex } from "viem";
import { CONVICTION_TRACKER_ABI, CONTRACT_ADDRESSES, DEBATE_ESCROW_ABI, RPC_URLS } from "@/lib/contracts";

export type ConnectionStatus = "connecting" | "live" | "reconnecting" | "disconnected";

export interface ConvictionEvent {
  hash: string;
  roundNumber: number;
  bullScore: number;
  bearScore: number;
  timestamp: number;
}

export interface DepositEvent {
  hash: string;
  depositor: `0x${string}`;
  side: "bull" | "bear";
  amount: bigint;
  timestamp: number;
}

interface EventLog {
  address?: `0x${string}`;
  data: Hex;
  topics: readonly Hex[];
  transactionHash?: `0x${string}`;
  hash?: `0x${string}`;
}

export interface ContractEventHandlers {
  onConvictionUpdate: (event: ConvictionEvent) => void;
  onDepositEvent: (event: DepositEvent) => void;
  onConnectionStatusChange: (status: ConnectionStatus) => void;
}

const convictionTopic = keccak256(stringToHex("ConvictionUpdated(uint256,uint256,uint256,uint256)"));
const depositTopic = keccak256(stringToHex("Deposited(address,uint8,uint256)"));

function getLogHash(log: EventLog): string {
  return log.transactionHash ?? log.hash ?? "0x0000000000000000000000000000000000000000000000000000000000000000";
}

function toMs(timestamp: bigint | number): number {
  const numeric = Number(timestamp);
  return numeric < 1_000_000_000_000 ? numeric * 1000 : numeric;
}

export function parseConvictionEvent(log: EventLog): ConvictionEvent | null {
  try {
    const decoded = decodeEventLog({
      abi: CONVICTION_TRACKER_ABI,
      data: log.data,
      topics: [...log.topics] as [`0x${string}`, ...`0x${string}`[]],
      strict: false,
    });

    const [roundNumber, bullScore, bearScore, timestamp] = decoded.args as readonly [bigint, bigint, bigint, bigint];

    return {
      hash: getLogHash(log),
      roundNumber: Number(roundNumber),
      bullScore: Number(bullScore),
      bearScore: Number(bearScore),
      timestamp: toMs(timestamp),
    };
  } catch {
    return null;
  }
}

export function parseDepositEvent(log: EventLog): DepositEvent | null {
  try {
    const decoded = decodeEventLog({
      abi: DEBATE_ESCROW_ABI,
      data: log.data,
      topics: [...log.topics] as [`0x${string}`, ...`0x${string}`[]],
      strict: false,
    });

    const [depositor, side, amount] = decoded.args as readonly [`0x${string}`, bigint, bigint];

    return {
      hash: getLogHash(log),
      depositor,
      side: Number(side) === 0 ? "bull" : "bear",
      amount,
      timestamp: Date.now(),
    };
  } catch {
    return null;
  }
}

class ContractEventSocket {
  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private shouldReconnect = true;

  constructor(private readonly handlers: ContractEventHandlers) {}

  connect() {
    if (typeof window === "undefined" || !RPC_URLS.ws) {
      this.handlers.onConnectionStatusChange("disconnected");
      return;
    }

    this.shouldReconnect = true;
    this.handlers.onConnectionStatusChange(this.reconnectAttempts > 0 ? "reconnecting" : "connecting");

    try {
      this.socket = new WebSocket(RPC_URLS.ws);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.handlers.onConnectionStatusChange("live");
      this.subscribe();
    };

    this.socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data as string) as {
          method?: string;
          params?: { result?: EventLog };
        };

        if (payload.method !== "eth_subscription") {
          return;
        }

        const log = payload.params?.result;
        if (!log?.address) {
          return;
        }

        if (log.address.toLowerCase() === CONTRACT_ADDRESSES.conviction.toLowerCase()) {
          const convictionEvent = parseConvictionEvent(log);
          if (convictionEvent) {
            this.handlers.onConvictionUpdate(convictionEvent);
          }
        }

        if (log.address.toLowerCase() === CONTRACT_ADDRESSES.escrow.toLowerCase()) {
          const depositEvent = parseDepositEvent(log);
          if (depositEvent) {
            this.handlers.onDepositEvent(depositEvent);
          }
        }
      } catch {
        // Ignore malformed payloads and keep the stream alive.
      }
    };

    this.socket.onerror = () => {
      this.scheduleReconnect();
    };

    this.socket.onclose = () => {
      if (this.shouldReconnect) {
        this.scheduleReconnect();
      }
    };
  }

  private subscribe() {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return;
    }

    this.socket.send(
      JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "eth_subscribe",
        params: [
          "logs",
          {
            address: CONTRACT_ADDRESSES.conviction,
            topics: [convictionTopic],
          },
        ],
      })
    );

    this.socket.send(
      JSON.stringify({
        jsonrpc: "2.0",
        id: 2,
        method: "eth_subscribe",
        params: [
          "logs",
          {
            address: CONTRACT_ADDRESSES.escrow,
            topics: [depositTopic],
          },
        ],
      })
    );
  }

  private scheduleReconnect() {
    if (!this.shouldReconnect) {
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    if (this.reconnectAttempts >= 5) {
      this.handlers.onConnectionStatusChange("disconnected");
      return;
    }

    this.reconnectAttempts += 1;
    const delay = Math.min(30_000, 1000 * 2 ** (this.reconnectAttempts - 1));
    this.handlers.onConnectionStatusChange("reconnecting");

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  disconnect() {
    this.shouldReconnect = false;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }

    this.handlers.onConnectionStatusChange("disconnected");
  }
}

export function useContractEvents(handlers: ContractEventHandlers) {
  const handlersRef = useRef(handlers);

  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  useEffect(() => {
    const socket = new ContractEventSocket({
      onConvictionUpdate: (event) => handlersRef.current.onConvictionUpdate(event),
      onDepositEvent: (event) => handlersRef.current.onDepositEvent(event),
      onConnectionStatusChange: (status) => handlersRef.current.onConnectionStatusChange(status),
    });

    socket.connect();

    return () => {
      socket.disconnect();
    };
  }, []);
}
