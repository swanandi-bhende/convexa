import type { MarketSnapshot as MarketSnapshotShape } from "@/lib/api/debateApi";

interface MarketSnapshotProps {
  snapshot: MarketSnapshotShape;
}

function metricTone(value: number) {
  return value >= 0 ? "text-emerald-600" : "text-rose-600";
}

export function MarketSnapshot({ snapshot }: MarketSnapshotProps) {
  return (
    <section className="rounded-3xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.09)]">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Market Snapshot</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">{snapshot.symbol}</p>
      <dl className="mt-6 space-y-4">
        <div className="flex items-center justify-between">
          <dt className="text-sm text-slate-500">Price</dt>
          <dd className="text-lg font-semibold text-slate-900">${snapshot.price.toLocaleString()}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-sm text-slate-500">24h Change</dt>
          <dd className={`text-sm font-semibold ${metricTone(snapshot.change24h)}`}>{snapshot.change24h}%</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-sm text-slate-500">24h Volume</dt>
          <dd className="text-sm font-semibold text-slate-900">${snapshot.volume24h.toLocaleString()}M</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-sm text-slate-500">Volatility</dt>
          <dd className="text-sm font-semibold text-amber-600">{snapshot.volatility}%</dd>
        </div>
      </dl>
    </section>
  );
}
