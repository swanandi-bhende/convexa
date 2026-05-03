interface SettlementStatusProps {
  escrowBalanceEth: number;
  pendingPayouts: number;
  contractAddress: string;
}

export function SettlementStatus({ escrowBalanceEth, pendingPayouts, contractAddress }: SettlementStatusProps) {
  return (
    <section className="rounded-3xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
      <h2 className="text-xl font-semibold tracking-tight text-slate-950">Settlement Status</h2>
      <dl className="mt-4 space-y-3 text-sm text-slate-700">
        <div className="flex items-center justify-between">
          <dt>Escrow balance</dt>
          <dd>{escrowBalanceEth.toFixed(2)} ETH</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt>Pending payouts</dt>
          <dd>{pendingPayouts}</dd>
        </div>
        <div className="flex items-center justify-between gap-4">
          <dt>Contract</dt>
          <dd className="max-w-[18ch] truncate text-right font-mono text-xs text-slate-500">{contractAddress}</dd>
        </div>
      </dl>
    </section>
  );
}
