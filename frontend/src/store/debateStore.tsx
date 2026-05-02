"use client";

import React, { createContext, useContext, useEffect, useMemo, useReducer, type ReactNode } from "react";
import { createPublicClient, formatEther, http } from "viem";
import { formatTimestamp } from "@/lib/format";
import { CONTRACT_ADDRESSES, CONVICTION_TRACKER_ABI, DEBATE_ESCROW_ABI, RPC_URLS } from "@/lib/contracts";
import { type ConnectionStatus, type ConvictionEvent, type DepositEvent, useContractEvents } from "@/lib/websocket";

export interface RoundResult {
  roundNumber: number;
  bullScore: number;
  bearScore: number;
  winner: "bull" | "bear" | "tie";
  judgeReasoning: string;
  timestamp: number;
}

export interface TransactionRecord {
  hash: string;
  type: "conviction" | "deposit" | "confirmation";
  timestamp: number;
  label: string;
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
  transactions: TransactionRecord[];
  bullStakeTotal: string;
  bearStakeTotal: string;
  connectionStatus: ConnectionStatus;
}

const initialState: DebateState = {
  currentBullScore: 50,
  currentBearScore: 50,
  currentRound: 0,
  debateActive: true,
  bullArgument: "Bull is assembling the opening case.",
  bearArgument: "Bear is waiting for the first crack in the argument.",
  judgeReasoning: "",
  roundHistory: [],
  transactions: [],
  bullStakeTotal: "0.000",
  bearStakeTotal: "0.000",
  connectionStatus: "connecting",
};

type HydratePayload = Partial<DebateState> & {
  roundHistory?: RoundResult[];
  transactions?: TransactionRecord[];
};

type Action =
  | { type: "HYDRATE_STATE"; payload: HydratePayload }
  | { type: "CONVICTION_UPDATED"; payload: ConvictionEvent }
  | { type: "ARGUMENT_RECEIVED"; payload: { side: "bull" | "bear"; text: string } }
  | { type: "DEPOSIT_MADE"; payload: DepositEvent }
  | { type: "STAKE_TOTALS_REFRESHED"; payload: { bullStakeTotal: string; bearStakeTotal: string } }
  | { type: "TRANSACTION_CONFIRMED"; payload: TransactionRecord }
  | { type: "CONNECTION_STATUS_CHANGED"; payload: ConnectionStatus };

interface DebateContextValue {
  state: DebateState;
  dispatch: React.Dispatch<Action>;
}

const DebateContext = createContext<DebateContextValue | undefined>(undefined);

function winnerFromScores(bullScore: number, bearScore: number): RoundResult["winner"] {
  if (bullScore > bearScore) {
    return "bull";
  }

  if (bearScore > bullScore) {
    return "bear";
  }

  return "tie";
}

function buildJudgeReasoning(roundNumber: number, bullScore: number, bearScore: number): string {
  const lead = Math.abs(bullScore - bearScore);
  const winner = winnerFromScores(bullScore, bearScore);

  if (bullScore === bearScore) {
    return `Round ${roundNumber} is locked at ${bullScore}-${bearScore}; the next update decides the tone.`;
  }

  return `${winner === "bull" ? "Bull" : "Bear"} leads round ${roundNumber} by ${lead} point${lead === 1 ? "" : "s"}, keeping the debate active but leaning decisive.`;
}

function buildArgumentCopy(side: "bull" | "bear", roundNumber: number, bullScore: number, bearScore: number): string {
  const lead = Math.abs(bullScore - bearScore);
  const isLeading = side === "bull" ? bullScore >= bearScore : bearScore >= bullScore;
  const leadText = isLeading ? "pressing the advantage" : "building a comeback";

  if (side === "bull") {
    return `Bull is ${leadText} in round ${roundNumber}, using ${bullScore} conviction points to keep pressure on Bear${lead > 0 ? ` and widen a ${lead}-point edge` : ""}.`;
  }

  return `Bear is ${leadText} in round ${roundNumber}, answering with ${bearScore} conviction points${lead > 0 ? ` and trying to erase a ${lead}-point gap` : ""}.`;
}

function formatStakeTotal(value: bigint): string {
  return Number.parseFloat(formatEther(value)).toFixed(3);
}

function createTransaction(hash: string, type: TransactionRecord["type"], timestamp: number, label: string): TransactionRecord {
  return { hash, type, timestamp, label };
}

function debateReducer(state: DebateState, action: Action): DebateState {
  switch (action.type) {
    case "HYDRATE_STATE": {
      return {
        ...state,
        ...action.payload,
        roundHistory: action.payload.roundHistory ?? state.roundHistory,
        transactions: action.payload.transactions ?? state.transactions,
      };
    }

    case "CONVICTION_UPDATED": {
      const { roundNumber, bullScore, bearScore, timestamp } = action.payload;
      const roundResult: RoundResult = {
        roundNumber,
        bullScore,
        bearScore,
        winner: winnerFromScores(bullScore, bearScore),
        judgeReasoning: buildJudgeReasoning(roundNumber, bullScore, bearScore),
        timestamp,
      };

      const nextHistory = [roundResult, ...state.roundHistory.filter((entry) => entry.roundNumber !== roundNumber)].sort(
        (left, right) => right.roundNumber - left.roundNumber
      );

      return {
        ...state,
        currentBullScore: bullScore,
        currentBearScore: bearScore,
        currentRound: roundNumber,
        debateActive: bullScore < 70 && bearScore < 70,
        judgeReasoning: roundResult.judgeReasoning,
        roundHistory: nextHistory,
      };
    }

    case "ARGUMENT_RECEIVED": {
      return {
        ...state,
        bullArgument: action.payload.side === "bull" ? action.payload.text : state.bullArgument,
        bearArgument: action.payload.side === "bear" ? action.payload.text : state.bearArgument,
      };
    }

    case "DEPOSIT_MADE": {
      const amountEth = Number.parseFloat(formatEther(action.payload.amount));
      const side = action.payload.side;

      return {
        ...state,
        bullStakeTotal: side === "bull" ? (Number.parseFloat(state.bullStakeTotal) + amountEth).toFixed(3) : state.bullStakeTotal,
        bearStakeTotal: side === "bear" ? (Number.parseFloat(state.bearStakeTotal) + amountEth).toFixed(3) : state.bearStakeTotal,
      };
    }

    case "STAKE_TOTALS_REFRESHED": {
      return {
        ...state,
        bullStakeTotal: action.payload.bullStakeTotal,
        bearStakeTotal: action.payload.bearStakeTotal,
      };
    }

    case "TRANSACTION_CONFIRMED": {
      return {
        ...state,
        transactions: [action.payload, ...state.transactions.filter((entry) => entry.hash !== action.payload.hash)].slice(0, 50),
      };
    }

    case "CONNECTION_STATUS_CHANGED": {
      return {
        ...state,
        connectionStatus: action.payload,
      };
    }

    default:
      return state;
  }
}

async function loadInitialState(dispatch: React.Dispatch<Action>) {
  if (!RPC_URLS.http) {
    dispatch({ type: "CONNECTION_STATUS_CHANGED", payload: "disconnected" });
    return;
  }

  try {
    const client = createPublicClient({ transport: http(RPC_URLS.http) });

    const [scores, stakeInfo, roundHistoryRaw] = await Promise.all([
      client.readContract({
        address: CONTRACT_ADDRESSES.conviction,
        abi: CONVICTION_TRACKER_ABI,
        functionName: "getCurrentScores",
      }),
      client.readContract({
        address: CONTRACT_ADDRESSES.escrow,
        abi: DEBATE_ESCROW_ABI,
        functionName: "getStakeInfo",
      }),
      client.readContract({
        address: CONTRACT_ADDRESSES.conviction,
        abi: CONVICTION_TRACKER_ABI,
        functionName: "getRoundHistory",
      }),
    ]);

    const history = [...roundHistoryRaw]
      .map((round) => ({
        roundNumber: Number(round.roundNumber),
        bullScore: Number(round.bullScore),
        bearScore: Number(round.bearScore),
        winner: winnerFromScores(Number(round.bullScore), Number(round.bearScore)),
        judgeReasoning: buildJudgeReasoning(Number(round.roundNumber), Number(round.bullScore), Number(round.bearScore)),
        timestamp: Number(round.timestamp) * 1000,
      }))
      .sort((left, right) => right.roundNumber - left.roundNumber) as RoundResult[];

    const currentRound = Number(scores[2]);
    const currentBullScore = Number(scores[0]);
    const currentBearScore = Number(scores[1]);
    const debateActive = Boolean(scores[3]);

    const latestRound = history[0];
    const bullArgument = latestRound
      ? buildArgumentCopy("bull", latestRound.roundNumber, latestRound.bullScore, latestRound.bearScore)
      : initialState.bullArgument;
    const bearArgument = latestRound
      ? buildArgumentCopy("bear", latestRound.roundNumber, latestRound.bullScore, latestRound.bearScore)
      : initialState.bearArgument;

    dispatch({
      type: "HYDRATE_STATE",
      payload: {
        currentBullScore,
        currentBearScore,
        currentRound,
        debateActive,
        bullStakeTotal: formatStakeTotal(stakeInfo[0]),
        bearStakeTotal: formatStakeTotal(stakeInfo[1]),
        roundHistory: history,
        transactions: history.map((round) =>
          createTransaction(`round-${round.roundNumber}`, "conviction", round.timestamp, `Round ${round.roundNumber} conviction settled`)
        ),
        bullArgument,
        bearArgument,
        judgeReasoning: latestRound?.judgeReasoning ?? buildJudgeReasoning(currentRound, currentBullScore, currentBearScore),
      },
    });
  } catch {
    dispatch({ type: "CONNECTION_STATUS_CHANGED", payload: "disconnected" });
  }
}

export function DebateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(debateReducer, initialState);

  useEffect(() => {
    void loadInitialState(dispatch);
  }, []);

  useContractEvents({
    onConvictionUpdate: (event) => {
      dispatch({ type: "CONVICTION_UPDATED", payload: event });
      dispatch({
        type: "ARGUMENT_RECEIVED",
        payload: {
          side: "bull",
          text: buildArgumentCopy("bull", event.roundNumber, event.bullScore, event.bearScore),
        },
      });
      dispatch({
        type: "ARGUMENT_RECEIVED",
        payload: {
          side: "bear",
          text: buildArgumentCopy("bear", event.roundNumber, event.bullScore, event.bearScore),
        },
      });
      dispatch({
        type: "TRANSACTION_CONFIRMED",
        payload: createTransaction(event.hash, "confirmation", event.timestamp, `Conviction event ${formatTimestamp(event.timestamp)}`),
      });
    },
    onDepositEvent: (event) => {
      dispatch({ type: "DEPOSIT_MADE", payload: event });
      dispatch({
        type: "TRANSACTION_CONFIRMED",
        payload: createTransaction(
          event.hash,
          "deposit",
          event.timestamp,
          `${event.side === "bull" ? "Bull" : "Bear"} deposit confirmed`
        ),
      });
    },
    onConnectionStatusChange: (status) => {
      dispatch({ type: "CONNECTION_STATUS_CHANGED", payload: status });
    },
  });

  const value = useMemo(() => ({ state, dispatch }), [state]);

  return <DebateContext.Provider value={value}>{children}</DebateContext.Provider>;
}

export function useDebateStore() {
  const context = useContext(DebateContext);
  if (!context) {
    throw new Error("useDebateStore must be used within a DebateProvider");
  }

  return context;
}
