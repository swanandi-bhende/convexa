export default function Loading() {
  return (
    <div className="space-y-4" aria-live="polite" aria-busy="true">
      <div className="h-8 w-64 animate-pulse rounded bg-slate-200" />
      <div className="grid gap-4 md:grid-cols-3">
        <div className="h-44 animate-pulse rounded-2xl bg-slate-200" />
        <div className="h-44 animate-pulse rounded-2xl bg-slate-200" />
        <div className="h-44 animate-pulse rounded-2xl bg-slate-200" />
      </div>
    </div>
  );
}
