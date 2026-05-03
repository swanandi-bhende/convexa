import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

async function seed() {
  const dataDir = path.join(process.cwd(), "src", "app", "api", "_data");
  await mkdir(dataDir, { recursive: true });

  const debateState = {
    sessionId: "demo-session-seeded",
    networkName: "Unichain Sepolia",
    chainId: 1301,
    currentRound: 4,
    currentBullScore: 68,
    currentBearScore: 61,
    debateActive: true,
    bullStakeTotalWei: "132000000000000000000",
    bearStakeTotalWei: "108000000000000000000",
    bullStakeTotalEth: 132,
    bearStakeTotalEth: 108,
  };

  const roundHistory = {
    sessionId: "demo-session-seeded",
    rounds: [
      {
        roundNumber: 1,
        bullScore: 54,
        bearScore: 49,
        winner: "bull",
        reasoning: "Bull provided stronger momentum evidence.",
        accuracyBonusApplied: false,
        accuracyBonusRecipient: null,
        convictionUpdateStatus: "confirmed",
        timestamp: Date.now() - 1000 * 60 * 12,
        convictionTxHash: null,
        microSettlementTxHash: null,
        roundDurationSeconds: 180,
        bullArgument: "Liquidity trend confirms upside continuation.",
        bearArgument: "Risk remains elevated on macro prints.",
      },
    ],
  };

  const transactions = {
    sessionId: "demo-session-seeded",
    entries: [],
    stats: {
      totalCount: 0,
      confirmedCount: 0,
      failedCount: 0,
      pendingCount: 0,
      totalGasUsedGwei: 0,
      successRate: 0,
    },
  };

  await Promise.all([
    writeFile(path.join(dataDir, "debate_state.json"), JSON.stringify(debateState, null, 2)),
    writeFile(path.join(dataDir, "round_history.json"), JSON.stringify(roundHistory, null, 2)),
    writeFile(path.join(dataDir, "transactions.json"), JSON.stringify(transactions, null, 2)),
  ]);

  console.log("Demo snapshot seeded at src/app/api/_data");
}

seed().catch((error) => {
  console.error(error);
  process.exit(1);
});
