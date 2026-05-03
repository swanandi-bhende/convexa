"use client";

import { useEffect, useMemo, useState } from "react";
import { SettlementStatus } from "@/components/SettlementStatus";
import { StakeForm } from "@/components/StakeForm";
import {
  getDemoStakeStore,
  markDemoStakeApplied,
  queueDemoStake,
  subscribeDemoStakeStore,
  type DemoStakeEvent,
} from "@/lib/demoStake";

export default function StakePage() {
  const [lastMessage, setLastMessage] = useState<string>("No stake submitted yet.");
  const [events, setEvents] = useState<DemoStakeEvent[]>([]);
  const [bullStakeDelta, setBullStakeDelta] = useState(0);
  const [bearStakeDelta, setBearStakeDelta] = useState(0);

  useEffect(() => {
    const initial = getDemoStakeStore();
    setEvents(initial.events);
    setBullStakeDelta(initial.bull);
    setBearStakeDelta(initial.bear);

    return subscribeDemoStakeStore((next) => {
      setEvents(next.events);
      setBullStakeDelta(next.bull);
      setBearStakeDelta(next.bear);
    });
  }, []);

  const pendingPayouts = useMemo(() => 4 + events.filter((event) => event.status === "queued").length, [events]);
  const escrowBalanceEth = useMemo(() => 215.42 + bullStakeDelta + bearStakeDelta, [bullStakeDelta, bearStakeDelta]);

  return (
    <div className="space-y-8">
      <section className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Stake and Escrow</h1>
        <p className="mt-2 text-slate-600">Queue Bull/Bear stake intents and watch them progress from queued to applied, with settlement metrics updated in real time.</p>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <StakeForm
          onSubmit={(side, amount) => {
            const queued = queueDemoStake(side, amount);
            setLastMessage(`Queued ${amount.toFixed(3)} ETH on ${side.toUpperCase()} side. Applying to demo state...`);

            window.setTimeout(() => {
              const applied = markDemoStakeApplied(queued.id);
              if (applied) {
                setLastMessage(`Applied ${applied.amount.toFixed(3)} ETH to ${applied.side.toUpperCase()} side. Debate conviction will rebalance.`);
              }
            }, 3500);
          }}
        />
        <SettlementStatus
          escrowBalanceEth={escrowBalanceEth}
          pendingPayouts={pendingPayouts}
          contractAddress="0xBB7bD22Aa37E05979c3858540048e99bCa98CEF9"
        />
      </div>

      <section className="rounded-2xl border border-slate-200/70 bg-white p-5 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Stake Event Feed</p>
        <div className="mt-3 space-y-2 text-sm">
          {events.length > 0 ? (
            events.slice(0, 6).map((event) => (
              <div key={event.id} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                <span className="font-medium text-slate-700">{event.side.toUpperCase()} {event.amount.toFixed(3)} ETH</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${event.status === "applied" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                  {event.status}
                </span>
              </div>
            ))
          ) : (
            <p className="text-slate-500">No stake events yet. Submit a stake to see queue progression.</p>
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200/70 bg-slate-950 px-5 py-4 text-sm text-slate-100 shadow-[0_10px_24px_rgba(15,23,42,0.18)]">{lastMessage}</section>
    </div>
  );
}
