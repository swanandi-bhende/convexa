import { NextResponse } from "next/server";
import { querySqlite, openSqliteDatabase } from "@/lib/server/sqlite";
import { readFile } from "node:fs/promises";
import path from "node:path";

export const runtime = "nodejs";

type SwapExecutionRow = {
  tx_hash: string | null;
  status: string;
  swap_type: string;
  round_number: number;
  keeperhub_job_id: string | null;
  gas_used_wei: string | null;
  gas_price_gwei: number | null;
  confirmed_at: string | null;
  error_message: string | null;
};

type RoundTraceTransactionRow = {
  round_number: number;
  conviction_tx_hash: string | null;
  micro_settlement_tx_hash: string | null;
  timestamp: string;
};

type SessionTransactionRow = {
  session_id: string;
  settlement_tx_hash: string | null;
  status: string;
  end_time: string | null;
  start_time: string;
};

type TransactionEntry = {
  hash: string;
  type: string;
  label: string;
  status: string;
  timestamp: number;
  roundNumber: number | null;
  keeperHubJobId: string | null;
  gasUsedGwei: number | null;
  explorerUrl: string;
};

function toTimestamp(value: string | null): number {
  if (!value) {
    return Date.now();
  }

  const parsed = new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : Date.now();
}

function toExplorerUrl(hash: string) {
  return `https://unichain-sepolia.blockscout.com/tx/${hash}`;
}

function formatGasUsedGwei(value: string | null): number | null {
  if (!value) {
    return null;
  }

  try {
    return Number(Number(BigInt(value)) / 1e9);
  } catch {
    return null;
  }
}

function uniqueByHash(entries: TransactionEntry[]) {
  const seen = new Set<string>();
  const deduped: TransactionEntry[] = [];

  for (const entry of entries) {
    const key = `${entry.type}:${entry.hash}`;
    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    deduped.push(entry);
  }

  return deduped;
}

async function querySwapExecutionsSafely() {
  const candidates = [
    "SELECT tx_hash, status, swap_type, round_number, keeperhub_job_id, gas_used_wei, gas_price_gwei, confirmed_at, error_message FROM swap_executions ORDER BY COALESCE(confirmed_at, quote_timestamp) DESC",
    "SELECT tx_hash, status, swap_type, round_number, keeperhub_job_id, gas_used_wei, gas_price_gwei, confirmed_at, error_message FROM swap_executions ORDER BY confirmed_at DESC",
    "SELECT tx_hash, status, swap_type, round_number, keeperhub_job_id, gas_used_wei, NULL as gas_price_gwei, confirmed_at, error_message FROM swap_executions ORDER BY confirmed_at DESC",
  ];

  for (const sql of candidates) {
    try {
      return await querySqlite<SwapExecutionRow>(sql);
    } catch {
      // Try next SQL variant to support schema drift across environments.
    }
  }

  return [] as SwapExecutionRow[];
}

export async function GET() {
  try {
    const db = await openSqliteDatabase();
    if (!db) {
      const snapPath = path.join(process.cwd(), "src", "app", "api", "_data", "transactions.json");
      const raw = await readFile(snapPath, "utf8");
      return NextResponse.json(JSON.parse(raw));
    }

    const latestSession = await querySqlite<{ session_id: string }>(
      "SELECT session_id FROM debate_sessions ORDER BY start_time DESC LIMIT 1"
    );
    const sessionId = latestSession[0]?.session_id ?? null;

    const [swapExecutions, roundTraces, sessions] = await Promise.all([
      querySwapExecutionsSafely(),
      sessionId
        ? querySqlite<RoundTraceTransactionRow>(
            "SELECT round_number, conviction_tx_hash, micro_settlement_tx_hash, timestamp FROM round_trace WHERE session_id = ? ORDER BY round_number DESC",
            [sessionId]
          )
        : [],
      querySqlite<SessionTransactionRow>(
        "SELECT session_id, settlement_tx_hash, status, end_time, start_time FROM debate_sessions ORDER BY start_time DESC LIMIT 5"
      ),
    ]);

    const entries: TransactionEntry[] = [];

    for (const execution of swapExecutions) {
      if (!execution.tx_hash) {
        continue;
      }

      entries.push({
        hash: execution.tx_hash,
        type: execution.swap_type,
        label: `${execution.swap_type.replace(/_/g, " ")} ${execution.round_number}`,
        status: execution.status,
        timestamp: toTimestamp(execution.confirmed_at),
        roundNumber: execution.round_number,
        keeperHubJobId: execution.keeperhub_job_id,
        gasUsedGwei: formatGasUsedGwei(execution.gas_used_wei),
        explorerUrl: toExplorerUrl(execution.tx_hash),
      });
    }

    for (const trace of roundTraces) {
      if (trace.conviction_tx_hash) {
        entries.push({
          hash: trace.conviction_tx_hash,
          type: "conviction",
          label: `Round ${trace.round_number} conviction update`,
          status: "confirmed",
          timestamp: toTimestamp(trace.timestamp),
          roundNumber: trace.round_number,
          keeperHubJobId: null,
          gasUsedGwei: null,
          explorerUrl: toExplorerUrl(trace.conviction_tx_hash),
        });
      }

      if (trace.micro_settlement_tx_hash) {
        entries.push({
          hash: trace.micro_settlement_tx_hash,
          type: "micro_settlement",
          label: `Round ${trace.round_number} micro settlement`,
          status: "confirmed",
          timestamp: toTimestamp(trace.timestamp),
          roundNumber: trace.round_number,
          keeperHubJobId: null,
          gasUsedGwei: null,
          explorerUrl: toExplorerUrl(trace.micro_settlement_tx_hash),
        });
      }
    }

    for (const session of sessions) {
      if (!session.settlement_tx_hash) {
        continue;
      }

      entries.push({
        hash: session.settlement_tx_hash,
        type: "final_settlement",
        label: `Session ${session.session_id.slice(0, 8)} final settlement`,
        status: session.status,
        timestamp: toTimestamp(session.end_time ?? session.start_time),
        roundNumber: null,
        keeperHubJobId: null,
        gasUsedGwei: null,
        explorerUrl: toExplorerUrl(session.settlement_tx_hash),
      });
    }

    const orderedEntries = uniqueByHash(entries).sort((left, right) => right.timestamp - left.timestamp);
    const stats = orderedEntries.reduce(
      (accumulator, entry) => {
        accumulator.totalCount += 1;
        accumulator.totalGasUsedGwei += entry.gasUsedGwei ?? 0;
        if (entry.status === "confirmed") {
          accumulator.confirmedCount += 1;
        } else if (entry.status === "failed") {
          accumulator.failedCount += 1;
        } else {
          accumulator.pendingCount += 1;
        }
        return accumulator;
      },
      { totalCount: 0, confirmedCount: 0, failedCount: 0, pendingCount: 0, totalGasUsedGwei: 0 }
    );

    return NextResponse.json({
      sessionId,
      entries: orderedEntries,
      stats: {
        ...stats,
        successRate: stats.totalCount ? Math.round((stats.confirmedCount / stats.totalCount) * 100) : 0,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to load transaction log.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
