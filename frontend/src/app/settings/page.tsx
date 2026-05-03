export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Settings</h1>
        <p className="mt-2 text-slate-600">Configure network preferences, demo mode, and default debate parameters.</p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <label className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
          <div>
            <p className="text-sm font-semibold text-slate-800">Demo Mode</p>
            <p className="mt-2 text-sm leading-6 text-slate-500">Use static API snapshots for offline walkthroughs.</p>
          </div>
          <input type="checkbox" className="mt-1 h-4 w-4 accent-slate-950" defaultChecked />
        </label>
        <label className="flex items-start justify-between gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
          <div>
            <p className="text-sm font-semibold text-slate-800">Auto-refresh</p>
            <p className="mt-2 text-sm leading-6 text-slate-500">Refresh state every 8 seconds when websocket is unavailable.</p>
          </div>
          <input type="checkbox" className="mt-1 h-4 w-4 accent-slate-950" defaultChecked />
        </label>
      </section>
    </div>
  );
}
