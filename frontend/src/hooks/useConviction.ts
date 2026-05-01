import { useCallback, useState } from 'react';
import { UserVote, VoteResponse } from '@/types/conviction';
import { ErrorResponse } from '@/types/api';

/**
 * useConvictionVote - Submit a conviction vote (stake on Bull or Bear)
 */
export function useConvictionVote(debateId: string, userId?: string) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [success, setSuccess] = useState(false);
  const [lastVote, setLastVote] = useState<UserVote | null>(null);

  const submitVote = useCallback(
    async (side: 'bull' | 'bear', stakeAmount: number) => {
      if (!userId) {
        setError({
          error: 'User ID is required',
          code: 'MISSING_USER_ID',
        });
        return;
      }

      try {
        setIsLoading(true);
        setError(null);

        const response = await fetch(`/api/debates/${debateId}/votes`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            userId,
            side,
            stakeAmount,
          }),
        });

        if (!response.ok) {
          const errorData = (await response.json()) as ErrorResponse;
          setError(errorData);
          return;
        }

        const data = (await response.json()) as VoteResponse;
        setLastVote(data.vote);
        setSuccess(true);

        // Reset success message after 3 seconds
        setTimeout(() => setSuccess(false), 3000);
      } catch (err) {
        setError({
          error: err instanceof Error ? err.message : 'Voting failed',
          code: 'VOTE_FAILED',
        });
      } finally {
        setIsLoading(false);
      }
    },
    [debateId, userId]
  );

  return {
    submitVote,
    isLoading,
    error,
    success,
    lastVote,
  };
}

/**
 * useUserVotes - Fetch user's conviction votes for a debate
 */
export function useUserVotes(debateId: string, userId?: string) {
  const [votes, setVotes] = useState<UserVote[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ErrorResponse | null>(null);

  const fetchVotes = useCallback(async () => {
    if (!userId) return;

    try {
      setLoading(true);
      const response = await fetch(
        `/api/debates/${debateId}/votes/user?userId=${userId}`
      );

      if (!response.ok) {
        const errorData = (await response.json()) as ErrorResponse;
        setError(errorData);
        return;
      }

      const data = await response.json() as { votes: UserVote[] };
      setVotes(data.votes);
      setError(null);
    } catch (err) {
      setError({
        error: err instanceof Error ? err.message : 'Failed to fetch votes',
        code: 'FETCH_FAILED',
      });
    } finally {
      setLoading(false);
    }
  }, [debateId, userId]);

  return {
    votes,
    loading,
    error,
    refetch: fetchVotes,
  };
}

/**
 * useConvictionStats - Calculate conviction-related statistics
 */
export function useConvictionStats(
  bullVotes: number,
  bearVotes: number,
  bullStaked: number,
  bearStaked: number
) {
  const total = bullVotes + bearVotes;
  const totalStaked = bullStaked + bearStaked;

  const bullPercent = total > 0 ? (bullVotes / total) * 100 : 50;
  const bearPercent = total > 0 ? (bearVotes / total) * 100 : 50;

  const bullStakedPercent =
    totalStaked > 0 ? (bullStaked / totalStaked) * 100 : 50;
  const bearStakedPercent =
    totalStaked > 0 ? (bearStaked / totalStaked) * 100 : 50;

  // Implied odds (inverse of probability)
  const bullImpliedOdds = total > 0 && bullVotes > 0 ? total / bullVotes : 1;
  const bearImpliedOdds = total > 0 && bearVotes > 0 ? total / bearVotes : 1;

  // Weighted confidence (based on staked amount)
  const bullWeightedConfidence = totalStaked > 0 ? bullStaked / totalStaked : 0;
  const bearWeightedConfidence = totalStaked > 0 ? bearStaked / totalStaked : 0;

  // Volatility (difference between vote % and stake %)
  const volatility = Math.abs(bullPercent - bullStakedPercent);

  return {
    bullPercent,
    bearPercent,
    bullStakedPercent,
    bearStakedPercent,
    bullImpliedOdds,
    bearImpliedOdds,
    bullWeightedConfidence,
    bearWeightedConfidence,
    volatility,
    totalVotes: total,
    totalStaked,
  };
}
