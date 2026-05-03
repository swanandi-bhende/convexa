"use client";

import { useState } from "react";
import { SettlementStatus } from "@/components/SettlementStatus";
import { StakeForm } from "@/components/StakeForm";

export default function StakePage() {
  const [lastMessage, setLastMessage] = useState<string>("No stake submitted yet.");

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Stake and Escrow</h1>
        <p className="mt-2 text-slate-600">Track contract balances, place Bull or Bear stakes, and inspect payout readiness.</p>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <StakeForm
          onSubmit={(side, amount) => {
            setLastMessage(`Queued ${amount.toFixed(3)} ETH on ${side.toUpperCase()} side.`);
          }}
        />
        <SettlementStatus
          escrowBalanceEth={215.42}
          pendingPayouts={4}
          contractAddress="0xBB7bD22Aa37E05979c3858540048e99bCa98CEF9"
        />
      </div>

      <section className="rounded-2xl bg-slate-900 px-5 py-4 text-sm text-slate-100">{lastMessage}</section>
    </div>
  );
}
