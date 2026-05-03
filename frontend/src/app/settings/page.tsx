export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <section className="rounded-3xl bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Settings</h1>
        <p className="mt-2 text-slate-600">Configure network preferences, demo mode, and default debate parameters.</p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <label className="rounded-2xl bg-white p-5 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
          <p className="text-sm font-semibold text-slate-800">Demo Mode</p>
          <p className="mt-2 text-sm text-slate-500">Use static API snapshots for offline walkthroughs.</p>
          <input type="checkbox" className="mt-4" defaultChecked />
        </label>
        <label className="rounded-2xl bg-white p-5 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
          <p className="text-sm font-semibold text-slate-800">Auto-refresh</p>
          <p className="mt-2 text-sm text-slate-500">Refresh state every 8 seconds when websocket is unavailable.</p>
          <input type="checkbox" className="mt-4" defaultChecked />
        </label>
      </section>
    </div>
  );
}
