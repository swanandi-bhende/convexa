interface DebateRound {
  round: number;
  bullArgument: string;
  bearArgument: string;
  verdict: string;
}

interface DebateDetailProps {
  debateId: string;
  rounds: DebateRound[];
}

export function DebateDetail({ debateId, rounds }: DebateDetailProps) {
  return (
    <section className="rounded-3xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
      <h2 className="text-xl font-semibold tracking-tight text-slate-950">Debate Detail: {debateId}</h2>
      <div className="mt-4 space-y-4">
        {rounds.map((round) => (
          <article key={round.round} className="rounded-2xl border border-slate-200/70 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Round {round.round}</p>
            <p className="mt-3 text-sm leading-6 text-sky-700"><span className="font-semibold">Bull:</span> {round.bullArgument}</p>
            <p className="mt-2 text-sm leading-6 text-orange-700"><span className="font-semibold">Bear:</span> {round.bearArgument}</p>
            <p className="mt-3 text-sm leading-6 text-slate-700"><span className="font-semibold">Judge:</span> {round.verdict}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
