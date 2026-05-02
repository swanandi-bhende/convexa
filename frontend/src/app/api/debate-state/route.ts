import { NextResponse } from "next/server";
import { createPublicClient, http } from "viem";
import { CONTRACT_ADDRESSES, CONVICTION_TRACKER_ABI, DEBATE_ESCROW_ABI, RPC_URLS } from "@/lib/contracts";
import { querySqlite } from "@/lib/server/sqlite";

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

    return NextResponse.json({
      sessionId: latestSession[0]?.session_id ?? null,
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
