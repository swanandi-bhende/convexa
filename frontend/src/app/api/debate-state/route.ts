import { NextResponse } from "next/server";
import { createPublicClient, http } from "viem";
import { CONTRACT_ADDRESSES, CONVICTION_TRACKER_ABI, DEBATE_ESCROW_ABI, RPC_URLS } from "@/lib/contracts";
import { querySqlite, openSqliteDatabase } from "@/lib/server/sqlite";
import { readFile } from "node:fs/promises";
import path from "node:path";

export const runtime = "nodejs";

function toNumber(value: bigint | number | string | boolean) {
  if (typeof value === "bigint") {
    return Number(value);
  }

  if (typeof value === "boolean") {
    return value ? 1 : 0;
  }

  return Number(value);
}

export async function GET() {
  try {
    const client = createPublicClient({ transport: http(RPC_URLS.http) });
    const [scores, stakeInfo, latestSession] = await Promise.all([
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
      querySqlite<{ session_id: string }>("SELECT session_id FROM debate_sessions ORDER BY start_time DESC LIMIT 1"),
    ]);
    let sessionId = latestSession[0]?.session_id ?? null;

    // If no local DB is present, load a static snapshot so serverless deployments still return UI-ready data.
    const db = await openSqliteDatabase();
    if (!db) {
      const snapPath = path.join(process.cwd(), "src", "app", "api", "_data", "debate_state.json");
      const raw = await readFile(snapPath, "utf8");
      const parsed = JSON.parse(raw);
      // Merge on-chain reads into the snapshot where possible, but keep snapshot values as fallback.
      return NextResponse.json({
        sessionId: parsed.sessionId ?? sessionId,
        networkName: parsed.networkName ?? "Unichain Sepolia",
        chainId: parsed.chainId ?? Number(process.env.NEXT_PUBLIC_CHAIN_ID || "1301"),
        currentRound: toNumber(scores[2]) ?? parsed.currentRound,
        currentBullScore: toNumber(scores[0]) ?? parsed.currentBullScore,
        currentBearScore: toNumber(scores[1]) ?? parsed.currentBearScore,
        debateActive: Boolean(scores[3]) ?? parsed.debateActive,
        bullStakeTotalWei: stakeInfo[0].toString() ?? parsed.bullStakeTotalWei,
        bearStakeTotalWei: stakeInfo[1].toString() ?? parsed.bearStakeTotalWei,
        bullStakeTotalEth: Number.parseFloat((Number(stakeInfo[0]) / 1e18).toFixed(3)) ?? parsed.bullStakeTotalEth,
        bearStakeTotalEth: Number.parseFloat((Number(stakeInfo[1]) / 1e18).toFixed(3)) ?? parsed.bearStakeTotalEth,
      });
    }

    return NextResponse.json({
      sessionId,
      networkName: "Unichain Sepolia",
      chainId: Number(process.env.NEXT_PUBLIC_CHAIN_ID || "1301"),
      currentRound: toNumber(scores[2]),
      currentBullScore: toNumber(scores[0]),
      currentBearScore: toNumber(scores[1]),
      debateActive: Boolean(scores[3]),
      bullStakeTotalWei: stakeInfo[0].toString(),
      bearStakeTotalWei: stakeInfo[1].toString(),
      bullStakeTotalEth: Number.parseFloat((Number(stakeInfo[0]) / 1e18).toFixed(3)),
      bearStakeTotalEth: Number.parseFloat((Number(stakeInfo[1]) / 1e18).toFixed(3)),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to load debate state.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
