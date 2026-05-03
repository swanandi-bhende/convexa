"use client";

import { useState } from "react";

interface StakeFormProps {
  onSubmit?: (side: "bull" | "bear", amount: number) => void;
}

export function StakeForm({ onSubmit }: StakeFormProps) {
  const [side, setSide] = useState<"bull" | "bear">("bull");
  const [amount, setAmount] = useState("0.05");

  return (
    <form
      className="rounded-3xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit?.(side, Number(amount));
      }}
    >
      <h2 className="text-xl font-semibold tracking-tight text-slate-900">Place Stake</h2>
      <div className="mt-4 grid gap-4">
        <label className="space-y-2 text-sm text-slate-600">
          Side
          <select value={side} onChange={(event) => setSide(event.target.value as "bull" | "bear")} className="w-full rounded-xl border border-slate-200 px-3 py-2 outline-none transition focus:border-slate-400">
            <option value="bull">Bull</option>
            <option value="bear">Bear</option>
          </select>
        </label>
        <label className="space-y-2 text-sm text-slate-600">
          Amount (ETH)
          <input type="number" min="0" step="0.001" value={amount} onChange={(event) => setAmount(event.target.value)} className="w-full rounded-xl border border-slate-200 px-3 py-2 outline-none transition focus:border-slate-400" />
        </label>
        <button className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800">Submit Stake</button>
      </div>
    </form>
  );
}
