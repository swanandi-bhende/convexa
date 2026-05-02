"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useDebateStore } from "@/store/debateStore";

interface ApiTransactionEntry {
  hash: string;
  type: string;
  label: string;
  status: string;
  timestamp: number;
  roundNumber: number | null;
  keeperHubJobId: string | null;
  gasUsedGwei: number | null;
  explorerUrl: string;
}

interface ApiTransactionResponse {
  sessionId: string | null;
  entries: ApiTransactionEntry[];
  stats: {
    totalCount: number;
    confirmedCount: number;
    failedCount: number;
    pendingCount: number;
    totalGasUsedGwei: number;
    successRate: number;
  };
}

interface FeedTransaction {
  hash: string;
  type: string;
  label: string;
  status: string;
  timestamp: number;
  roundNumber: number | null;
  keeperHubJobId: string | null;
  gasUsedGwei: number | null;
  explorerUrl: string;
}

function formatRelativeTime(timestamp: number) {
  const deltaSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));

  if (deltaSeconds < 60) {
    return `${deltaSeconds}s ago`;
  }

  const deltaMinutes = Math.floor(deltaSeconds / 60);
  if (deltaMinutes < 60) {
    return `${deltaMinutes}m ago`;
  }

  const deltaHours = Math.floor(deltaMinutes / 60);
  if (deltaHours < 24) {
    return `${deltaHours}h ago`;
  }

  return `${Math.floor(deltaHours / 24)}d ago`;
}

function explorerUrl(hash: string) {
  return `https://unichain-sepolia.blockscout.com/tx/${hash}`;
}

function statusTone(status: string) {
  if (status === "confirmed") {
    return "bg-emerald-500";
  }

  if (status === "failed") {
    return "bg-rose-400";
  }

  return "bg-amber-300";
}

function typeLabel(type: string) {
  if (type === "deposit") {
    return "Deposit";
  }

  if (type === "conviction") {
    return "Conviction";
  }

  if (type === "micro_settlement") {
    return "Micro settlement";
  }

  if (type === "final_settlement") {
    return "Final settlement";
  }

  return type.replace(/_/g, " ");
}

function dedupeTransactions(entries: FeedTransaction[]) {
  const seen = new Set<string>();
  const deduped: FeedTransaction[] = [];

  for (const entry of entries) {
    const key = `${entry.type}:${entry.hash}`;
    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    deduped.push(entry);
  }

  return deduped;
}

export function TransactionLog() {
  const { state } = useDebateStore();
  const [apiFeed, setApiFeed] = useState<ApiTransactionResponse | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [, setClock] = useState(Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 60000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadTransactions() {
      try {
        const response = await fetch("/api/transactions", { cache: "no-store" });
        if (!response.ok) {
          throw new Error("Unable to load transactions");
        }

        const payload = (await response.json()) as ApiTransactionResponse;
        if (!cancelled) {
          setApiFeed(payload);
        }
      } catch {
        if (!cancelled) {
          setApiFeed(null);
        }
      }
    }

    void loadTransactions();
    const interval = window.setInterval(loadTransactions, 30000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const entries = useMemo(() => {
    const storeEntries: FeedTransaction[] = state.transactions.map((transaction) => ({
      hash: transaction.hash,
      type: transaction.type,
      label: transaction.label,
      status: transaction.type === "confirmation" ? "confirmed" : transaction.type === "deposit" ? "confirmed" : "confirmed",
      timestamp: transaction.timestamp,
      roundNumber: null,
      keeperHubJobId: null,
      gasUsedGwei: null,
      explorerUrl: explorerUrl(transaction.hash),
    }));

    const apiEntries = apiFeed?.entries ?? [];
    return dedupeTransactions([...apiEntries, ...storeEntries]).sort((left, right) => right.timestamp - left.timestamp);
  }, [apiFeed?.entries, state.transactions]);

  const visibleEntries = showAll ? entries : entries.slice(0, 8);
  const stats = apiFeed?.stats ?? {
    totalCount: entries.length,
    confirmedCount: entries.filter((entry) => entry.status === "confirmed").length,
    failedCount: entries.filter((entry) => entry.status === "failed").length,
    pendingCount: entries.filter((entry) => entry.status === "pending").length,
    totalGasUsedGwei: 0,
    successRate: entries.length ? Math.round((entries.filter((entry) => entry.status === "confirmed").length / entries.length) * 100) : 0,
  };

  return (
    <section className="glass-card-strong min-w-0 overflow-hidden rounded-[28px] p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-on-surface-variant">Transaction log</p>
          <h3 className="mt-2 font-display text-3xl text-on-surface sm:text-4xl">Onchain activity</h3>
        </div>
        <div className="rounded-full bg-surface-container-low px-3 py-2 text-xs text-primary">Live feed</div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <div className="rounded-[20px] bg-surface p-4">
          <div className="text-[11px] uppercase tracking-[0.28em] text-on-surface-variant">Transactions</div>
          <div className="mt-2 font-mono text-2xl text-on-surface">{stats.totalCount}</div>
        </div>
        <div className="rounded-[20px] bg-surface p-4">
          <div className="text-[11px] uppercase tracking-[0.28em] text-secondary">Success rate</div>
          <div className="mt-2 font-mono text-2xl text-secondary">{stats.successRate}%</div>
        </div>
        <div className="rounded-[20px] bg-surface p-4">
          <div className="text-[11px] uppercase tracking-[0.28em] text-tertiary">Gas used</div>
          <div className="mt-2 font-mono text-2xl text-tertiary">{stats.totalGasUsedGwei.toFixed(2)}</div>
        </div>
        <div className="rounded-[20px] bg-surface p-4">
          <div className="text-[11px] uppercase tracking-[0.28em] text-primary">Pending</div>
          <div className="mt-2 font-mono text-2xl text-primary">{stats.pendingCount}</div>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {visibleEntries.length === 0 ? (
          <div className="rounded-[24px] bg-surface p-5 text-sm text-on-surface-variant">No transactions captured yet.</div>
        ) : null}

        {visibleEntries.map((entry, index) => (
          <article
            key={`${entry.type}:${entry.hash}`}
            className={`rounded-[22px] bg-surface p-4 transition ${index === 0 ? "animate-[slide-down-fade_0.35s_ease-out]" : ""}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className={`mt-1 h-2.5 w-2.5 rounded-full ${statusTone(entry.status)}`} />
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-medium text-on-surface">{entry.label}</h4>
                    <span className="rounded-full bg-surface-container-low px-2 py-1 text-[11px] uppercase tracking-[0.25em] text-on-surface-variant">{typeLabel(entry.type)}</span>
                    {entry.roundNumber !== null ? <span className="rounded-full bg-surface-container-low px-2 py-1 text-[11px] uppercase tracking-[0.25em] text-on-surface-variant">Round {entry.roundNumber}</span> : null}
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-on-surface-variant">
                    <span className="font-mono">{entry.hash.slice(0, 10)}...{entry.hash.slice(-6)}</span>
                    <span>{formatRelativeTime(entry.timestamp)}</span>
                    {entry.keeperHubJobId ? <span>Keeper job {entry.keeperHubJobId}</span> : null}
                    {entry.gasUsedGwei !== null ? <span>{entry.gasUsedGwei.toFixed(2)} gwei</span> : null}
                  </div>
                </div>
              </div>

              <a
                className="rounded-full bg-surface-container-low px-3 py-2 text-xs text-on-surface transition"
                href={entry.explorerUrl}
                rel="noreferrer"
                target="_blank"
              >
                View on Explorer
              </a>
            </div>
          </article>
        ))}
      </div>

      {entries.length > 8 ? (
        <div className="mt-4 flex justify-center">
          <button
            className="rounded-full bg-surface-container-low px-4 py-2 text-sm text-on-surface transition"
            onClick={() => setShowAll((value) => !value)}
          >
            {showAll ? "Show fewer" : `View all (${entries.length})`}
          </button>
        </div>
      ) : null}
    </section>
  );
}
