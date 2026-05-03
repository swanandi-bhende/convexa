interface JudgeVerdictProps {
  pending: boolean;
  round: number;
  bullScore: number;
  bearScore: number;
}

export function JudgeVerdict({ pending, round, bullScore, bearScore }: JudgeVerdictProps) {
  const winner = bullScore === bearScore ? "Tie" : bullScore > bearScore ? "Bull" : "Bear";
  const winnerTone = winner === "Bull" ? "text-sky-300" : winner === "Bear" ? "text-orange-300" : "text-slate-300";

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-950 p-6 text-slate-100 shadow-[0_14px_28px_rgba(15,23,42,0.28)]">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">Judge Verdict</p>
      {pending ? (
        <div className="mt-4 animate-pulse rounded-2xl bg-slate-800 px-4 py-6 text-sm text-slate-300">Pending reveal for round {round}...</div>
      ) : (
        <div className="mt-4 rounded-2xl bg-slate-900 px-4 py-5">
          <p className="text-sm text-slate-300">Round {round} winner</p>
          <p className={`mt-2 text-3xl font-semibold tracking-tight ${winnerTone}`}>{winner}</p>
          <p className="mt-2 text-sm text-slate-300">Bull {bullScore} vs Bear {bearScore}</p>
        </div>
      )}
    </section>
  );
}
