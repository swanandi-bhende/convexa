import { NextResponse } from "next/server";
import { querySqlite } from "@/lib/server/sqlite";

export const runtime = "nodejs";

type RoundHistoryRow = {
  round_number: number;
  bull_score: number;
  bear_score: number;
  winner: string;
  reasoning: string;
  accuracy_bonus_applied: number | boolean | null;
  accuracy_bonus_recipient: string | null;
  conviction_update_status: string;
  timestamp: string;
};

type RoundTraceRow = {
  round_number: number;
  bull_argument_json: string | null;
  bear_argument_json: string | null;
  judge_verdict_json: string | null;
  conviction_tx_hash: string | null;
  micro_settlement_tx_hash: string | null;
  round_duration_seconds: number | null;
  timestamp: string;
};

function parseJsonMaybe(value: string | null | undefined): Record<string, unknown> | null {
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function toTimestamp(value: string | number | Date): number {
  const parsed = typeof value === "number" ? value : new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : Date.now();
}

export async function GET() {
  try {
    const latestSession = await querySqlite<{ session_id: string }>(
      "SELECT session_id FROM debate_sessions ORDER BY start_time DESC LIMIT 1"
    );
    const sessionId = latestSession[0]?.session_id ?? null;

    const verdicts = await querySqlite<RoundHistoryRow>(
      "SELECT round_number, bull_score, bear_score, winner, reasoning, accuracy_bonus_applied, accuracy_bonus_recipient, conviction_update_status, timestamp FROM judge_verdicts ORDER BY round_number DESC"
    );
    const roundTraces = sessionId
      ? await querySqlite<RoundTraceRow>(
          "SELECT round_number, bull_argument_json, bear_argument_json, judge_verdict_json, conviction_tx_hash, micro_settlement_tx_hash, round_duration_seconds, timestamp FROM round_trace WHERE session_id = ? ORDER BY round_number DESC",
          [sessionId]
        )
      : [];

    const traceByRound = new Map<number, RoundTraceRow>();
    for (const trace of roundTraces) {
      traceByRound.set(trace.round_number, trace);
    }

    const rounds = verdicts.map((verdict) => {
      const trace = traceByRound.get(verdict.round_number);
      const verdictJson = parseJsonMaybe(trace?.judge_verdict_json);
      const bullArgumentJson = parseJsonMaybe(trace?.bull_argument_json);
      const bearArgumentJson = parseJsonMaybe(trace?.bear_argument_json);

      return {
        roundNumber: verdict.round_number,
        bullScore: verdict.bull_score,
        bearScore: verdict.bear_score,
        winner: verdict.winner,
        reasoning: verdict.reasoning,
        accuracyBonusApplied: Boolean(verdict.accuracy_bonus_applied),
        accuracyBonusRecipient: verdict.accuracy_bonus_recipient,
        convictionUpdateStatus: verdict.conviction_update_status,
        timestamp: toTimestamp(verdict.timestamp),
        convictionTxHash: trace?.conviction_tx_hash ?? null,
        microSettlementTxHash: trace?.micro_settlement_tx_hash ?? null,
        roundDurationSeconds: trace?.round_duration_seconds ?? null,
        bullArgument: typeof bullArgumentJson?.argument === "string" ? bullArgumentJson.argument : null,
        bearArgument: typeof bearArgumentJson?.argument === "string" ? bearArgumentJson.argument : null,
        verdictPayload: verdictJson,
      };
    });

    return NextResponse.json({
      sessionId,
      rounds,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to load round history.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
