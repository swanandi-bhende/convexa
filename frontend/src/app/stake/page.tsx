"use client";

import { useEffect, useMemo, useState } from "react";
import { SettlementStatus } from "@/components/SettlementStatus";
import { StakeForm } from "@/components/StakeForm";
import { MegaBreadcrumb } from "@/components/MegaBreadcrumb";
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
    <div className="max-w-6xl mx-auto space-y-24 pb-32 slide-up-fade">
      <MegaBreadcrumb />

      <section className="grid md:grid-cols-2 gap-16 items-start">
        <div className="space-y-8">
          <h1 className="display-lg text-on-surface">Stake on Conviction</h1>
          <p className="body-lg text-on-surface-variant border-l-2 border-outline-variant pl-6">
            Participate directly in the consensus mechanism. By staking on the Bull or Bear, you are depositing ETH into the <code>DebateEscrow</code> smart contract on Unichain Sepolia.
          </p>
          
          <div className="tonal-card p-8 mt-12 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-1 h-full bg-secondary group-hover:w-2 transition-all duration-300" />
            <h3 className="headline-md mb-4 text-secondary">The Settlement Mechanics</h3>
            <ul className="space-y-4 body-lg text-on-surface-variant">
              <li className="flex items-start gap-3">
                <span className="text-secondary mt-1">01.</span>
                <span><strong>Deposit:</strong> Your stake is locked in the <code>DebateEscrow</code> contract.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-secondary mt-1">02.</span>
                <span><strong>Orchestration:</strong> The Python Orchestrator monitors the Judge's Conviction Score.</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-secondary mt-1">03.</span>
                <span><strong>Resolution:</strong> The Orchestrator triggers <code>settle()</code>, distributing the opposing side's stake to the winners.</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="bg-surface-container-low p-8 sm:p-12 relative ambient-shadow space-y-8">
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
          <section className="bg-surface p-5 border border-outline-variant">
            <p className="label-md text-on-surface-variant mb-4">Stake Event Feed</p>
            <div className="space-y-2 text-sm">
              {events.length > 0 ? (
                events.slice(0, 6).map((event) => (
                  <div key={event.id} className="flex items-center justify-between bg-surface-container-low px-3 py-2">
                    <span className="font-medium text-on-surface">{event.side.toUpperCase()} {event.amount.toFixed(3)} ETH</span>
                    <span className={`px-2 py-0.5 label-md ${event.status === "applied" ? "text-bull-500" : "text-tertiary"}`}>
                      {event.status}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-on-surface-variant">No stake events yet. Submit a stake to see queue progression.</p>
              )}
            </div>
          </section>
          <section className="bg-primary/10 text-primary p-4 text-sm body-lg">{lastMessage}</section>
        </div>
      </section>
    </div>
  );
}
