interface BearCardProps {
  name: string;
  argument: string;
  confidence: number;
  score: number;
  metrics: string[];
}

export function BearCard({ name, argument, confidence, score, metrics }: BearCardProps) {
  return (
    <article
      className="rounded-3xl p-6 text-white shadow-[0_16px_32px_rgba(33,42,60,0.20)]"
      style={{ background: "linear-gradient(135deg, #f97316 0%, #ef4444 100%)" }}
    >
      <div className="flex items-center justify-between">
        <span className="rounded-full bg-white/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em]">{name}</span>
        <span className="rounded-full bg-white/20 px-3 py-1 text-xs font-semibold">Confidence {confidence}%</span>
      </div>
      <p className="mt-4 text-base leading-7 text-orange-50">{argument}</p>
      <div className="mt-5 flex items-center gap-2">
        <p className="text-sm font-semibold text-orange-100">Score {score}</p>
      </div>
      <ul className="mt-4 space-y-2 text-sm text-orange-100">
        {metrics.map((metric) => (
          <li key={metric}>• {metric}</li>
        ))}
      </ul>
    </article>
  );
}
