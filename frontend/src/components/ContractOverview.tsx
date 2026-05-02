'use client';

import React from 'react';

export type ContractTx = {
  hash: string;
  type: 'stake' | 'mint' | 'settle' | 'payout';
  from: string;
  amountUsd: number;
  timestamp: string; // ISO
};

export type ContractInfo = {
  id: string;
  name?: string;
  address: string;
  network?: string;
  escrowBalanceUsd: number;
  totalStakedUsd: number;
  settlementStatus: 'OPEN' | 'SETTLEMENT_PENDING' | 'SETTLED';
  contractsLinked?: string[];
  txHistory?: ContractTx[];
};

interface ContractOverviewProps {
  contract: ContractInfo;
  onView?: (id: string) => void;
}

export const ContractOverview: React.FC<ContractOverviewProps> = ({ contract, onView }) => {
  return (
    <div className="rounded-lg border border-border-light bg-white p-lg" role="region" aria-label={`Contract ${contract.name ?? contract.address}`}>
      <div className="flex items-start justify-between gap-md">
        <div>
          <div className="text-sm text-text-secondary">Contract</div>
          <div className="font-semibold text-text-primary">{contract.name ?? contract.address}</div>
          <div className="text-xs text-text-secondary">{contract.network ?? 'Unichain'}</div>
        </div>

        <div className="text-right">
          <div className="text-xs text-text-secondary">Escrow Balance</div>
          <div className="font-mono font-bold text-lg">${contract.escrowBalanceUsd.toLocaleString()}</div>
          <div className="text-xs text-text-secondary">Total Staked: ${contract.totalStakedUsd.toLocaleString()}</div>
        </div>

        <div className="text-center">
          <div className="text-xs text-text-secondary">Status</div>
          <div className={`mt-sm px-sm py-xs rounded-md font-semibold ${contract.settlementStatus === 'OPEN' ? 'bg-success-50 text-success-700' : contract.settlementStatus === 'SETTLEMENT_PENDING' ? 'bg-warning-50 text-warning-700' : 'bg-surface text-text-secondary'}`}>
            {contract.settlementStatus}
          </div>
        </div>

        <div className="flex flex-col items-end gap-sm">
          <button className="px-md py-sm bg-bull-500 text-white rounded-md text-sm hover:brightness-95" onClick={() => onView?.(contract.id)}>Details</button>
          <a className="text-xs text-text-secondary hover:underline" href={`https://unichain.explorer/address/${contract.address}`} target="_blank" rel="noreferrer">View on Explorer</a>
        </div>
      </div>

      {contract.txHistory && contract.txHistory.length > 0 && (
        <div className="mt-lg border-t pt-lg">
          <h4 className="text-sm font-semibold mb-sm">Recent Transactions</h4>
          <ul className="space-y-sm">
            {contract.txHistory.slice(0,4).map(tx => (
              <li key={tx.hash} className="flex items-center justify-between p-sm rounded-md bg-surface">
                <div>
                  <div className="font-mono text-sm">{tx.type.toUpperCase()}</div>
                  <div className="text-xs text-text-secondary">{new Date(tx.timestamp).toLocaleString()} • from {tx.from}</div>
                </div>
                <div className="text-right">
                  <div className="font-semibold">${tx.amountUsd.toFixed(2)}</div>
                  <a className="text-xs text-text-secondary hover:underline" href={`https://unichain.explorer/tx/${tx.hash}`} target="_blank" rel="noreferrer">tx</a>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ContractOverview;
