'use client';

import React from 'react';
import Link from 'next/link';
import { useDemoMode } from '@/hooks/useDemoMode';
import { seedDemoDebates, clearDemoDebates, getDemoDebates } from '@/lib/demoSeed';

export default function PresentationPage() {
  const { enabled, setEnabled } = useDemoMode();

  const handleSeed = () => {
    seedDemoDebates();
    // reload to pick up demo data in pages that read localStorage
    window.location.reload();
  };

  const handleClear = () => {
    clearDemoDebates();
    window.location.reload();
  };

  const demoCount = typeof window !== 'undefined' ? getDemoDebates().length : 0;

  return (
    <main className="p-lg max-w-4xl mx-auto">
      <header className="mb-lg">
        <h1 className="text-heading-lg font-bold">Convexa — Live Debate Market</h1>
        <p className="text-text-secondary mt-sm">Problem: aligning incentives for predictive debates. Solution: Conviction-powered debate markets with on-chain escrow and settlements.</p>
      </header>

      <section className="space-y-md">
        <h2 className="text-heading-md font-semibold">Demo Mode</h2>
        <p className="text-text-secondary">Toggle demo mode to run the app locally without network dependencies. Seed sample debates for an offline walkthrough.</p>

        <div className="flex items-center gap-md">
          <label className="flex items-center gap-sm">
            <input aria-label="Enable demo mode" type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
            <span className="text-sm">Demo mode</span>
          </label>

          <button className="px-md py-sm bg-bull-500 text-white rounded-md" onClick={handleSeed}>Seed Demo Data</button>
          <button className="px-md py-sm bg-warning-500 text-white rounded-md" onClick={handleClear}>Clear Demo Data</button>
          <div className="text-sm text-text-secondary">Seeded: {demoCount}</div>
        </div>
      </section>

      <section className="mt-lg space-y-md">
        <h2 className="text-heading-md font-semibold">Presentation</h2>
        <p className="text-text-secondary">Slides-style bullets:</p>
        <ul className="list-disc pl-6 text-sm space-y-2">
          <li><strong>Problem:</strong> Sophisticated on-chain prediction debates are brittle and lack continuous incentives.</li>
          <li><strong>Solution:</strong> Convexa — debates with conviction voting, escrow staking, and automated settlement.</li>
          <li><strong>Tech:</strong> Next.js (App Router), TypeScript, Tailwind CSS, Server-Sent Events for real-time updates, Ethers.js + Hardhat for contracts.</li>
          <li><strong>Demo:</strong> Use Demo Mode and visit <Link href="/contracts">Contracts</Link> and <Link href="/history">History</Link>.</li>
        </ul>
      </section>

      <section className="mt-lg">
        <h2 className="text-heading-md font-semibold">Links</h2>
        <ul className="pl-4 list-disc text-sm">
          <li><a className="text-bull-600 hover:underline" href="/contracts">Contracts Dashboard</a></li>
          <li><a className="text-bull-600 hover:underline" href="/history">Debate History</a></li>
          <li><a className="text-bull-600 hover:underline" href="https://unichain.explorer/" target="_blank" rel="noreferrer">Unichain Explorer</a></li>
        </ul>
      </section>

      <footer className="mt-lg text-sm text-text-secondary">
        <p>Ready for presentation: use the demo mode to walk through sample debates and contracts.</p>
      </footer>
    </main>
  );
}
