'use client';

import React, { useState } from 'react';

interface ContractActionsProps {
  contractId: string;
  onStake?: (amountUsd: number) => Promise<void> | void;
  onMint?: (amountUsd: number) => Promise<void> | void;
  disabled?: boolean;
}

export const ContractActions: React.FC<ContractActionsProps> = ({ contractId, onStake, onMint, disabled = false }) => {
  const [amount, setAmount] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const submit = async (type: 'stake' | 'mint') => {
    setError(null);
    const val = parseFloat(amount);
    if (isNaN(val) || val <= 0) {
      setError('Enter a valid amount');
      return;
    }
    setLoading(true);
    try {
      if (type === 'stake') {
        await onStake?.(val);
      } else {
        await onMint?.(val);
      }
      setSuccess(`${type === 'stake' ? 'Staked' : 'Minted'} $${val.toFixed(2)}`);
      setAmount('');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-border-light bg-white p-lg">
      <h4 className="font-semibold mb-sm">Actions</h4>
      <div className="flex items-center gap-md">
        <input
          value={amount}
          onChange={e => setAmount(e.target.value)}
          placeholder="Amount (USD)"
          className="px-md py-sm border rounded-md w-48"
          disabled={disabled || loading}
        />
        <button className="px-md py-sm bg-bull-500 text-white rounded-md" onClick={() => submit('stake')} disabled={disabled || loading}>Stake</button>
        <button className="px-md py-sm bg-bear-500 text-white rounded-md" onClick={() => submit('mint')} disabled={disabled || loading}>Mint</button>
      </div>
      {error && <div className="text-sm text-danger-600 mt-sm">{error}</div>}
      {success && <div className="text-sm text-success-600 mt-sm">{success}</div>}
    </div>
  );
};

export default ContractActions;
