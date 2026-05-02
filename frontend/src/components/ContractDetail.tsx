'use client';

import React from 'react';
import { ContractInfo } from './ContractOverview';
import ContractActions from './ContractActions';

interface ContractDetailProps {
  contract: ContractInfo;
  onClose?: () => void;
}

export const ContractDetail: React.FC<ContractDetailProps> = ({ contract, onClose }) => {
  const payoutExample = () => {
    // simple mock payout calc
    const totalPot = contract.escrowBalanceUsd;
    const protocolFee = totalPot * 0.02;
    const winnerPot = totalPot - protocolFee;
    return { totalPot, protocolFee, winnerPot };
  };

  const { totalPot, protocolFee, winnerPot } = payoutExample();

  const handleStake = async (amountUsd: number) => {
    // placeholder: in production call backend or wallet
    console.log('stake', contract.id, amountUsd);
    return;
  };

  const handleMint = async (amountUsd: number) => {
    console.log('mint', contract.id, amountUsd);
    return;
  };

  return (
    <div className="rounded-lg border border-border-light bg-white p-lg">
      <div className="flex items-center justify-between mb-md">
        <div>
          <h3 className="text-heading-md font-semibold">Contract Detail</h3>
          <div className="text-xs text-text-secondary">{contract.address}</div>
        </div>
        <div>
          <button onClick={onClose} className="text-sm text-text-secondary">Close</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
        <div>
          <div className="text-sm text-text-secondary mb-sm">Escrow</div>
          <div className="font-mono font-bold text-lg mb-md">${contract.escrowBalanceUsd.toLocaleString()}</div>

          <div className="text-sm text-text-secondary">Settlement</div>
          <div className="font-semibold mb-md">{contract.settlementStatus}</div>

          <div className="text-sm text-text-secondary">Payout Example</div>
          <ul className="mt-sm text-sm">
            <li>Total Pot: ${totalPot.toFixed(2)}</li>
            <li>Protocol Fee (2%): ${protocolFee.toFixed(2)}</li>
            <li>Winner Pot: ${winnerPot.toFixed(2)}</li>
          </ul>
        </div>

        <div>
          <ContractActions contractId={contract.id} onStake={handleStake} onMint={handleMint} />
        </div>
      </div>

      {contract.txHistory && (
        <div className="mt-lg">
          <h4 className="font-semibold mb-sm">Transaction History</h4>
          <div className="space-y-sm">
            {contract.txHistory.map(tx => (
              <div key={tx.hash} className="flex items-center justify-between p-sm rounded-md bg-surface">
                <div>
                  <div className="font-mono text-sm">{tx.type.toUpperCase()}</div>
                  <div className="text-xs text-text-secondary">{new Date(tx.timestamp).toLocaleString()}</div>
                </div>
                <div className="text-right">
                  <div className="font-semibold">${tx.amountUsd.toFixed(2)}</div>
                  <a className="text-xs text-text-secondary hover:underline" href={`https://unichain.explorer/tx/${tx.hash}`} target="_blank" rel="noreferrer">view</a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ContractDetail;
