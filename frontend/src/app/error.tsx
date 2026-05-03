"use client";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <section className="rounded-2xl bg-rose-50 p-6 text-rose-700" role="alert">
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="mt-2 text-sm">{error.message}</p>
      <button onClick={reset} className="mt-4 rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white">
        Try again
      </button>
    </section>
  );
}
