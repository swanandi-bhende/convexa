'use client';

import { RPC_URLS, CONTRACT_ADDRESSES, CONVICTION_TRACKER_ABI, DEBATE_ESCROW_ABI } from './contracts';

export interface ConvictionEvent {
  roundNumber: number;
  bullScore: number;
  bearScore: number;
  timestamp: number;
}

export interface DepositEvent {
  depositor: string;
  side: number; // 0 = bull, 1 = bear
  amount: string;
  timestamp: number;
}

export type ContractEvent = ConvictionEvent | DepositEvent;

export function isConvictionEvent(event: any): event is ConvictionEvent {
  return 'bullScore' in event && 'bearScore' in event;
}

export function isDepositEvent(event: any): event is DepositEvent {
  return 'depositor' in event && 'side' in event;
}

// Parse ConvictionUpdated event log
export function parseConvictionEvent(log: any): ConvictionEvent | null {
  try {
    // Raw log format from Alchemy
    if (log.topics && log.data) {
      const data = log.data;
      const roundNumber = parseInt(log.topics[1] || '0', 16);
      const bullScore = parseInt(data.slice(0, 66), 16);
      const bearScore = parseInt(data.slice(66, 130), 16);
      return {
        roundNumber,
        bullScore,
        bearScore,
        timestamp: Date.now(),
      };
    }
  } catch (e) {
    console.error('Failed to parse conviction event', e);
  }
  return null;
}

// Parse Deposited event log
export function parseDepositEvent(log: any): DepositEvent | null {
  try {
    if (log.topics && log.data) {
      const depositor = '0x' + log.topics[1].slice(-40);
      const data = log.data;
      const side = parseInt(data.slice(0, 66), 16);
      const amount = '0x' + data.slice(66, 130);
      return {
        depositor,
        side,
        amount,
        timestamp: Date.now(),
      };
    }
  } catch (e) {
    console.error('Failed to parse deposit event', e);
  }
  return null;
}

export interface WebSocketManagerConfig {
  onConvictionUpdate: (event: ConvictionEvent) => void;
  onDepositEvent: (event: DepositEvent) => void;
  onConnectionChange: (status: 'connecting' | 'connected' | 'disconnected' | 'reconnecting') => void;
}

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000; // 3s base, exponential backoff
  private config: WebSocketManagerConfig;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  constructor(config: WebSocketManagerConfig) {
    this.config = config;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.config.onConnectionChange('connecting');
    try {
      this.ws = new WebSocket(RPC_URLS.ws);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected');
        this.reconnectAttempts = 0;
        this.config.onConnectionChange('connected');
        this.subscribeToEvents();
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.params?.result?.logs) {
            data.params.result.logs.forEach((log: any) => {
              // Check for ConvictionUpdated event
              if (log.address?.toLowerCase() === CONTRACT_ADDRESSES.conviction.toLowerCase()) {
                const parsed = parseConvictionEvent(log);
                if (parsed) this.config.onConvictionUpdate(parsed);
              }
              // Check for Deposited event
              if (log.address?.toLowerCase() === CONTRACT_ADDRESSES.escrow.toLowerCase()) {
                const parsed = parseDepositEvent(log);
                if (parsed) this.config.onDepositEvent(parsed);
              }
            });
          }
        } catch (e) {
          console.error('[WebSocket] Message parse error', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error', error);
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        this.stopHeartbeat();
        this.attemptReconnect();
      };
    } catch (e) {
      console.error('[WebSocket] Connection error', e);
      this.attemptReconnect();
    }
  }

  private subscribeToEvents() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

    // Subscribe to ConvictionUpdated events
    this.ws.send(
      JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'eth_subscribe',
        params: [
          'logs',
          {
            address: CONTRACT_ADDRESSES.conviction,
            topics: ['0x' + Buffer.from('ConvictionUpdated(uint256,uint256,uint256)'.split('(')[0]).toString('hex')],
          },
        ],
      })
    );

    // Subscribe to Deposited events
    this.ws.send(
      JSON.stringify({
        jsonrpc: '2.0',
        id: 2,
        method: 'eth_subscribe',
        params: [
          'logs',
          {
            address: CONTRACT_ADDRESSES.escrow,
            topics: ['0x' + Buffer.from('Deposited(address,uint8,uint256)'.split('(')[0]).toString('hex')],
          },
        ],
      })
    );
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ jsonrpc: '2.0', method: 'net_version', params: [], id: Date.now() }));
      }
    }, 30000); // every 30s
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached');
      this.config.onConnectionChange('disconnected');
      return;
    }

    this.config.onConnectionChange('reconnecting');
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    setTimeout(() => this.connect(), delay);
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.config.onConnectionChange('disconnected');
  }
}

// React hook wrapper
export function useContractEvents(
  onConvictionUpdate?: (event: ConvictionEvent) => void,
  onDepositEvent?: (event: DepositEvent) => void,
  onConnectionChange?: (status: string) => void
) {
  const managerRef = React.useRef<WebSocketManager | null>(null);

  React.useEffect(() => {
    managerRef.current = new WebSocketManager({
      onConvictionUpdate: onConvictionUpdate || (() => {}),
      onDepositEvent: onDepositEvent || (() => {}),
      onConnectionChange: onConnectionChange || (() => {}),
    });

    managerRef.current.connect();

    return () => {
      managerRef.current?.disconnect();
    };
  }, [onConvictionUpdate, onDepositEvent, onConnectionChange]);

  return {
    disconnect: () => managerRef.current?.disconnect(),
  };
}

// Import React for the hook
import React from 'react';
