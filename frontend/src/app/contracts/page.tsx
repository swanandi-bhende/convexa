'use client';

import React, { useMemo, useState } from 'react';
import ContractOverview, { ContractInfo } from '@/components/ContractOverview';
import ContractDetail from '@/components/ContractDetail';

const mockContracts = (): ContractInfo[] => [
  {
    id: 'c-1',
    name: 'DebateEscrow Module',
    address: '0xAbC123...def',
    network: 'Unichain Sepolia',
    escrowBalanceUsd: 125000.5,
    totalStakedUsd: 200000,
    settlementStatus: 'OPEN',
    txHistory: [
      { hash: '0xaaa111', type: 'stake', from: '0xuser1', amountUsd: 2500, timestamp: new Date(Date.now()-3600*1000).toISOString() },
      { hash: '0xbbb222', type: 'mint', from: '0xuser2', amountUsd: 5000, timestamp: new Date(Date.now()-7200*1000).toISOString() },
    ],
  },
  {
    id: 'c-2',
    name: 'ConvictionTracker Module',
    address: '0xFfE987...012',
    network: 'Unichain Sepolia',
    escrowBalanceUsd: 42000,
    totalStakedUsd: 80000,
    settlementStatus: 'SETTLEMENT_PENDING',
    txHistory: [
      { hash: '0xccc333', type: 'stake', from: '0xuser3', amountUsd: 1200, timestamp: new Date(Date.now()-86400*1000).toISOString() },
    ],
  }
];

export default function ContractsPage() {
  const contracts = useMemo(() => mockContracts(), []);
  const [selectedId, setSelectedId] = useState<string | null>(contracts[0]?.id ?? null);

  const selected = contracts.find(c => c.id === selectedId) || null;

  return (
    <main className="space-y-lg p-lg">
      <div className="flex items-center justify-between">
        <h1 className="text-heading-lg font-bold">Smart Contract Dashboard</h1>
        <p className="text-text-secondary">Addresses, balances, stakes, and actions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg">
        <div className="lg:col-span-2 space-y-md">
          {contracts.map(c => (
            <div key={c.id} onClick={() => setSelectedId(c.id)}>
              <ContractOverview contract={c} onView={(id) => setSelectedId(id)} />
            </div>
          ))}
        </div>

        <div className="lg:col-span-1">
          {selected ? (
            <ContractDetail contract={selected} onClose={() => setSelectedId(null)} />
          ) : (
            <div className="rounded-lg border border-border-light bg-white p-lg text-text-secondary">Select a contract to view details.</div>
          )}
        </div>
      </div>
    </main>
  );
}
