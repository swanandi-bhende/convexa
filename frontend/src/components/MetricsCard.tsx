interface MetricsCardProps {
  label: string;
  value: string;
  trend?: string;
  tone?: "bull" | "bear" | "neutral";
}

const toneClass: Record<NonNullable<MetricsCardProps["tone"]>, string> = {
  bull: "bg-sky-50 text-sky-700",
  bear: "bg-orange-50 text-orange-700",
  neutral: "bg-slate-100 text-slate-700",
};

export function MetricsCard({ label, value, trend, tone = "neutral" }: MetricsCardProps) {
  return (
    <article className="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <div className="mt-3 flex items-end justify-between gap-4">
        <p className="text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
        {trend ? <span className={`rounded-full px-3 py-1 text-xs font-semibold ${toneClass[tone]}`}>{trend}</span> : null}
      </div>
    </article>
  );
}
