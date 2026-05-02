'use client';

import React, { useReducer, useContext, createContext, ReactNode } from 'react';
import { ConvictionEvent, DepositEvent } from '@/lib/websocket';

export interface RoundResult {
  roundNumber: number;
  bullScore: number;
  bearScore: number;
  winner: 'bull' | 'bear' | 'tie';
  judgeReasoning: string;
  timestamp: number;
}

export interface Transaction {
  hash: string;
  type: 'conviction' | 'deposit' | 'settlement' | 'swap';
  from: string;
  amount: string;
  timestamp: number;
  status: 'pending' | 'confirmed' | 'failed';
  keeperJobId?: string;
}

export interface DebateState {
  currentBullScore: number;
  currentBearScore: number;
  currentRound: number;
  debateActive: boolean;
  bullArgument: string;
  bearArgument: string;
  judgeReasoning: string;
  roundHistory: RoundResult[];
  transactions: Transaction[];
  bullStakeTotal: string; // in ETH
  bearStakeTotal: string; // in ETH
  connectionStatus: 'connecting' | 'live' | 'reconnecting' | 'disconnected';
  lastUpdate: number;
}

const initialState: DebateState = {
  currentBullScore: 0,
  currentBearScore: 0,
  currentRound: 1,
  debateActive: true,
  bullArgument: 'Awaiting Bull argument...',
  bearArgument: 'Awaiting Bear argument...',
  judgeReasoning: '',
  roundHistory: [],
  transactions: [],
  bullStakeTotal: '0.0',
  bearStakeTotal: '0.0',
  connectionStatus: 'connecting',
  lastUpdate: Date.now(),
};

type Action =
  | { type: 'CONVICTION_UPDATED'; payload: ConvictionEvent }
  | { type: 'DEPOSIT_MADE'; payload: DepositEvent }
  | { type: 'ARGUMENT_RECEIVED'; payload: { side: 'bull' | 'bear'; text: string; round: number } }
  | { type: 'JUDGE_VERDICT'; payload: { reasoning: string; bullScore: number; bearScore: number; round: number } }
  | { type: 'TRANSACTION_ADDED'; payload: Transaction }
  | { type: 'CONNECTION_STATUS_CHANGED'; payload: string }
  | { type: 'STAKE_UPDATED'; payload: { side: 'bull' | 'bear'; amount: string } }
  | { type: 'DEBATE_ENDED' };

function debateReducer(state: DebateState, action: Action): DebateState {
  switch (action.type) {
    case 'CONVICTION_UPDATED': {
      const { roundNumber, bullScore, bearScore } = action.payload;
      const updated: RoundResult = {
        roundNumber,
        bullScore,
        bearScore,
        winner: bullScore > bearScore ? 'bull' : bearScore > bullScore ? 'bear' : 'tie',
        judgeReasoning: state.judgeReasoning,
        timestamp: action.payload.timestamp,
      };
      return {
        ...state,
        currentBullScore: bullScore,
        currentBearScore: bearScore,
        currentRound: roundNumber,
        roundHistory: [updated, ...state.roundHistory.filter(r => r.roundNumber !== roundNumber)],
        lastUpdate: Date.now(),
      };
    }

    case 'DEPOSIT_MADE': {
      const amount = (BigInt(action.payload.amount) / BigInt(1e18)).toString();
      return {
        ...state,
        bullStakeTotal:
          action.payload.side === 0
            ? (parseFloat(state.bullStakeTotal) + parseFloat(amount)).toFixed(4)
            : state.bullStakeTotal,
        bearStakeTotal:
          action.payload.side === 1
            ? (parseFloat(state.bearStakeTotal) + parseFloat(amount)).toFixed(4)
            : state.bearStakeTotal,
      };
    }

    case 'ARGUMENT_RECEIVED': {
      return {
        ...state,
        bullArgument: action.payload.side === 'bull' ? action.payload.text : state.bullArgument,
        bearArgument: action.payload.side === 'bear' ? action.payload.text : state.bearArgument,
      };
    }

    case 'JUDGE_VERDICT': {
      return {
        ...state,
        judgeReasoning: action.payload.reasoning,
      };
    }

    case 'TRANSACTION_ADDED': {
      return {
        ...state,
        transactions: [action.payload, ...state.transactions].slice(0, 100), // keep last 100
      };
    }

    case 'CONNECTION_STATUS_CHANGED': {
      const status = action.payload as 'connecting' | 'live' | 'reconnecting' | 'disconnected';
      return {
        ...state,
        connectionStatus: status,
      };
    }

    case 'STAKE_UPDATED': {
      return {
        ...state,
        bullStakeTotal:
          action.payload.side === 'bull'
            ? action.payload.amount
            : state.bullStakeTotal,
        bearStakeTotal:
          action.payload.side === 'bear'
            ? action.payload.amount
            : state.bearStakeTotal,
      };
    }

    case 'DEBATE_ENDED': {
      return {
        ...state,
        debateActive: false,
      };
    }

    default:
      return state;
  }
}

interface DebateContextType {
  state: DebateState;
  dispatch: React.Dispatch<Action>;
}

const DebateContext = createContext<DebateContextType | undefined>(undefined);

export function DebateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(debateReducer, initialState);

  return (
    <DebateContext.Provider value={{ state, dispatch }}>
      {children}
    </DebateContext.Provider>
  );
}

export function useDebateStore() {
  const context = useContext(DebateContext);
  if (!context) {
    throw new Error('useDebateStore must be used within DebateProvider');
  }
  return context;
}
