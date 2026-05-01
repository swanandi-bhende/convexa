/**
 * Conviction Tracker Types
 * Types for user voting, stake tracking, and conviction payout calculations
 */

export interface UserVote {
  id: number;
  debateId: string;
  userId: string;
  side: 'bull' | 'bear';
  stakeAmount: number; // In tokens (ETH, USDC, etc.)
  stakeUsd: number; // USD equivalent at time of vote
  votedAt: string; // ISO 8601
  roundNumber: number;
  txHash?: string; // Blockchain transaction hash
  status: 'pending' | 'confirmed' | 'failed';
}

export interface ConvictionState {
  debateId: string;
  roundNumber: number;
  bullVotes: number; // Total conviction count (sum of user votes)
  bearVotes: number; // Total conviction count (sum of user votes)
  bullStaked: number; // Total USD value staked on bull
  bearStaked: number; // Total USD value staked on bear
  totalParticipants: number;
  uniqueBullVoters: number;
  uniqueBearVoters: number;
  lastUpdated: string; // ISO 8601
}

export interface UserVoteSummary {
  userId: string;
  debateId: string;
  totalStaked: number; // Total USD staked
  bullStaked: number;
  bearStaked: number;
  bullVotes: number;
  bearVotes: number;
  bullWins: number;
  bearWins: number;
  totalWins: number;
  winRate: number; // percentage
  estimatedPayout?: number; // If debate still active
  actualPayout?: number; // If debate settled
}

export interface VotingStats {
  debateId: string;
  totalValueLocked: number; // USD value of all stakes
  largestVote: number;
  smallestVote: number;
  averageVote: number;
  medianVote: number;
  bullParticipationRate: number; // % of total votes
  bearParticipationRate: number; // % of total votes
  volatility: number; // How much conviction changes per minute
}

export interface ConvictionPayout {
  debateId: string;
  userId: string;
  winingSide: 'bull' | 'bear';
  yourVotes: number;
  totalWinningVotes: number;
  totalPot: number; // Sum of all stakes
  yourShare: number; // percentage
  payoutAmount: number;
  status: 'pending' | 'claimed' | 'failed';
  claimedAt?: string; // ISO 8601
  txHash?: string;
}

export interface VoteRequest {
  debateId: string;
  userId: string;
  side: 'bull' | 'bear';
  stakeAmount: number;
  stakeTokenAddress?: string; // For multi-token support
}

export interface VoteResponse {
  success: boolean;
  vote: UserVote;
  newConvictionState: ConvictionState;
  estimatedPayout?: number;
  txHash?: string;
}

export interface ConvictionLeaderboard {
  debateId: string;
  topVoters: Array<{
    userId: string;
    stakeAmount: number;
    side: 'bull' | 'bear';
    rank: number;
  }>;
  yourRank?: number;
}

/**
 * Conviction Calculator Functions
 */

export function calculateVoteWeight(stakeAmount: number): number {
  // 1 USD stake = 1 vote (vote weight is proportional to stake)
  return Math.round(stakeAmount);
}

export function calculatePayoutPercentage(
  yourVotes: number,
  totalWinningVotes: number
): number {
  if (totalWinningVotes === 0) return 0;
  return (yourVotes / totalWinningVotes) * 100;
}

export function calculatePayoutAmount(
  yourVotes: number,
  totalWinningVotes: number,
  totalPot: number,
  feePercentage: number = 2 // Protocol fee %
): number {
  if (totalWinningVotes === 0) return 0;

  const yourShare = (yourVotes / totalWinningVotes) * totalPot;
  const fee = (yourShare * feePercentage) / 100;
  return yourShare - fee;
}

export function calculateImpliedOdds(
  bullVotes: number,
  bearVotes: number
): { bullOdds: number; bearOdds: number } {
  const total = bullVotes + bearVotes;
  if (total === 0) return { bullOdds: 1, bearOdds: 1 };

  return {
    bullOdds: total / bullVotes,
    bearOdds: total / bearVotes,
  };
}

export function calculateBreakeven(
  stakeAmount: number,
  totalVotes: number,
  yourVotes: number,
  totalPot: number,
  feePercentage: number = 2
): number {
  if (totalVotes === 0) return 0;

  const payoutIfWin = calculatePayoutAmount(
    yourVotes,
    totalVotes,
    totalPot,
    feePercentage
  );
  return payoutIfWin / stakeAmount;
}
