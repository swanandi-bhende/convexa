interface ConvictionTrackerProps {
  bullScore: number;
  bearScore: number;
  threshold?: number;
}

export function ConvictionTracker({ bullScore, bearScore, threshold = 70 }: ConvictionTrackerProps) {
  const total = Math.max(1, bullScore + bearScore);
  const bullPercent = (bullScore / total) * 100;
  const bearPercent = 100 - bullPercent;

  return (
    <section className="rounded-3xl bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.09)]">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Conviction Tracker</p>
      <div className="mt-5 overflow-hidden rounded-2xl bg-slate-100">
        <div className="flex h-7 w-full">
          <div className="h-full bg-blue-500 transition-all duration-500" style={{ width: `${bullPercent}%` }} aria-label="Bull conviction" />
          <div className="h-full bg-orange-500 transition-all duration-500" style={{ width: `${bearPercent}%` }} aria-label="Bear conviction" />
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="font-semibold text-blue-700">Bull {bullScore}</span>
        <span className="font-semibold text-slate-600">Threshold {threshold}</span>
        <span className="font-semibold text-orange-700">Bear {bearScore}</span>
      </div>
    </section>
  );
}
