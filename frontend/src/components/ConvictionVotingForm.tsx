'use client';

import React, { useState } from 'react';

interface ConvictionVotingFormProps {
  debateId: string;
  side: 'bull' | 'bear';
  isLoading?: boolean;
  minStake?: number;
  maxStake?: number;
  onSubmit: (amount: number) => Promise<void>;
  onCancel?: () => void;
}

/**
 * Conviction Voting Form - Allows users to stake on Bull or Bear
 */
export function ConvictionVotingForm({
  debateId,
  side,
  isLoading = false,
  minStake = 0.01,
  maxStake = 10000,
  onSubmit,
  onCancel,
}: ConvictionVotingFormProps) {
  const [stakeAmount, setStakeAmount] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const numericStake = parseFloat(stakeAmount) || 0;
  const isValid =
    numericStake >= minStake && numericStake <= maxStake && !isLoading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isValid) {
      setError(
        `Stake must be between ${minStake} and ${maxStake} ${side === 'bull' ? 'USDC' : 'USDC'}`
      );
      return;
    }

    try {
      setIsSubmitting(true);
      await onSubmit(numericStake);
      setSuccess(true);
      setStakeAmount('');
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Voting failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const sideLabel = side === 'bull' ? 'Bull' : 'Bear';
  const sideColor = side === 'bull' ? 'bull' : 'bear';
  const sideEmoji = side === 'bull' ? '📈' : '📉';

  return (
    <div className="rounded-lg border border-border-light bg-white p-lg max-w-md">
      {/* Header */}
      <div className="mb-lg flex items-center gap-md">
        <span className="text-2xl">{sideEmoji}</span>
        <h3 className="text-heading-md font-semibold text-text-primary">
          Vote {sideLabel}
        </h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-lg">
        {/* Stake Amount Input */}
        <div className="space-y-sm">
          <label
            htmlFor="stake-amount"
            className="block text-label-md font-semibold text-text-primary"
          >
            Stake Amount (USDC)
          </label>
          <div className="relative">
            <span className="absolute left-md top-1/2 -translate-y-1/2 text-text-secondary">
              $
            </span>
            <input
              id="stake-amount"
              type="number"
              min={minStake}
              max={maxStake}
              step="0.01"
              placeholder="0.00"
              value={stakeAmount}
              onChange={(e) => {
                setStakeAmount(e.target.value);
                setError(null);
              }}
              disabled={isLoading || isSubmitting}
              className="w-full pl-lg pr-md py-md border border-border-light rounded-md focus:outline-none focus:ring-2 focus:ring-offset-0 focus:border-transparent disabled:bg-surface disabled:opacity-50"
              style={{
              }}
            />
          </div>
          <p className="text-label-xs text-text-secondary">
            Min: ${minStake} • Max: ${maxStake}
          </p>
        </div>

        {/* Quick Amount Buttons */}
        <div className="grid grid-cols-4 gap-xs">
          {[10, 25, 50, 100].map((amount) => (
            <button
              key={amount}
              type="button"
              onClick={() => setStakeAmount(amount.toString())}
              disabled={isLoading || isSubmitting || amount > maxStake}
              className={`px-sm py-xs rounded-md text-label-sm font-semibold transition-colors ${
                stakeAmount === amount.toString()
                  ? `bg-${sideColor}-500 text-white`
                  : `bg-${sideColor}-50 text-${sideColor}-600 hover:bg-${sideColor}-100`
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              ${amount}
            </button>
          ))}
        </div>

        {/* Estimated Payout (Info) */}
        {numericStake > 0 && (
          <div className="rounded-md bg-surface p-md space-y-xs">
            <p className="text-label-sm text-text-secondary">
              Your Stake
            </p>
            <p className="text-heading-sm font-bold text-text-primary">
              ${numericStake.toFixed(2)}
            </p>
            <p className="text-label-xs text-text-secondary">
              = {numericStake.toLocaleString()} votes
            </p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="rounded-md bg-warning-50 border border-warning-500 p-md">
            <p className="text-label-sm text-warning-700">{error}</p>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="rounded-md bg-success-50 border border-success-500 p-md">
            <p className="text-label-sm text-success-700">
              ✓ Vote registered successfully!
            </p>
          </div>
        )}

        {/* Submit Buttons */}
        <div className="flex gap-md pt-lg">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading || isSubmitting}
              className="flex-1 px-md py-md bg-border-light hover:bg-border-dark text-text-primary font-semibold rounded-md transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            disabled={!isValid || isLoading || isSubmitting}
            className={`flex-1 px-md py-md text-white font-semibold rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-${sideColor}-500 hover:bg-${sideColor}-600`}
          >
            {isSubmitting || isLoading ? (
              <span className="flex items-center justify-center gap-sm">
                <span className="animate-spin">⟳</span>
                Voting...
              </span>
            ) : (
              `Vote ${sideLabel} ${stakeAmount ? `($${numericStake.toFixed(2)})` : ''}`
            )}
          </button>
        </div>

        {/* Disclaimer */}
        <p className="text-label-xs text-text-secondary text-center pt-md border-t border-border-light">
          Your conviction vote will be locked until debate settlement. You can
          win or lose your stake.
        </p>
      </form>
    </div>
  );
}
