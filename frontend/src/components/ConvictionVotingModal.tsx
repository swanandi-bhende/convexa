'use client';

import React from 'react';
import { ConvictionVotingForm } from './ConvictionVotingForm';

interface ConvictionVotingModalProps {
  debateId: string;
  isOpen: boolean;
  side: 'bull' | 'bear';
  onClose: () => void;
  onVote: (amount: number) => Promise<void>;
  isLoading?: boolean;
}

/**
 * ConvictionVotingModal - Modal for submitting conviction votes
 */
export function ConvictionVotingModal({
  debateId,
  isOpen,
  side,
  onClose,
  onVote,
  isLoading = false,
}: ConvictionVotingModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="max-w-md w-full mx-auto">
        <ConvictionVotingForm
          debateId={debateId}
          side={side}
          onSubmit={onVote}
          onCancel={onClose}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
