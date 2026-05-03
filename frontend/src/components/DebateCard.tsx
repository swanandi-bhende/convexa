interface DebateCardProps {
  debateId: string;
  tokenPair: string;
  winner: "Bull" | "Bear" | "Tie";
  bullScore: number;
  bearScore: number;
  date: string;
  duration: string;
  onSelect: () => void;
  selected?: boolean;
}

export function DebateCard({ debateId, tokenPair, winner, bullScore, bearScore, date, duration, onSelect, selected }: DebateCardProps) {
  const winnerTone = winner === "Bull" ? "bg-blue-100 text-blue-700" : winner === "Bear" ? "bg-orange-100 text-orange-700" : "bg-slate-200 text-slate-700";

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-2xl border bg-white p-5 text-left shadow-[0_8px_24px_rgba(33,42,60,0.07)] transition hover:-translate-y-0.5 ${selected ? "border-slate-950 ring-2 ring-slate-950/10" : "border-slate-200/70"}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">{date}</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-900">{tokenPair}</h3>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${winnerTone}`}>{winner}</span>
      </div>
      <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-4">
        <p>Debate: {debateId}</p>
        <p>Bull: {bullScore}</p>
        <p>Bear: {bearScore}</p>
        <p>Duration: {duration}</p>
      </div>
    </button>
  );
}
