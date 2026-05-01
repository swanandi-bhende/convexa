import { NextRequest, NextResponse } from 'next/server';
import { VoteRequest, VoteResponse, UserVote } from '@/types/conviction';
import { ErrorResponse } from '@/types/api';

/**
 * POST /api/debates/[debateId]/votes
 * Submit a user conviction vote (stake on Bull or Bear)
 * 
 * Request:
 * {
 *   userId: "user-123",
 *   side: "bull" | "bear",
 *   stakeAmount: 25.00,
 *   stakeTokenAddress: "0x..." (optional)
 * }
 * 
 * Response:
 * {
 *   success: true,
 *   vote: { ...UserVote },
 *   newConvictionState: { ...ConvictionState },
 *   estimatedPayout: 50.25,
 *   txHash: "0x..."
 * }
 */

interface RouteParams {
  debateId: string;
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<RouteParams> }
) {
  const { debateId } = await params;

  if (!debateId) {
    return NextResponse.json<ErrorResponse>(
      {
        error: 'Debate ID is required',
        code: 'INVALID_DEBATE_ID',
      },
      { status: 400 }
    );
  }

  let body: VoteRequest;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json<ErrorResponse>(
      {
        error: 'Invalid request body',
        code: 'INVALID_REQUEST',
      },
      { status: 400 }
    );
  }

  const { userId, side, stakeAmount } = body;

  // Validate inputs
  if (!userId || typeof userId !== 'string') {
    return NextResponse.json<ErrorResponse>(
      {
        error: 'User ID is required',
        code: 'MISSING_USER_ID',
      },
      { status: 400 }
    );
  }

  if (!side || !['bull', 'bear'].includes(side)) {
    return NextResponse.json<ErrorResponse>(
      {
        error: 'Side must be "bull" or "bear"',
        code: 'INVALID_SIDE',
      },
      { status: 400 }
    );
  }

  if (!stakeAmount || stakeAmount <= 0 || stakeAmount > 10000) {
    return NextResponse.json<ErrorResponse>(
      {
        error: 'Stake amount must be between 0.01 and 10000',
        code: 'INVALID_STAKE_AMOUNT',
      },
      { status: 400 }
    );
  }

  try {
    // TODO: Implement actual vote submission
    // 1. Verify user has sufficient balance
    // 2. Lock tokens in escrow contract
    // 3. Insert vote into database
    // 4. Update conviction scores
    // 5. Broadcast update via SSE
    
    // Mock implementation for MVP
    const mockVote: UserVote = {
      id: Math.floor(Math.random() * 1000000),
      debateId,
      userId,
      side,
      stakeAmount,
      stakeUsd: stakeAmount,
      votedAt: new Date().toISOString(),
      roundNumber: 7,
      status: 'confirmed',
      txHash: `0x${Math.random().toString(16).slice(2)}`,
    };

    const mockResponse: VoteResponse = {
      success: true,
      vote: mockVote,
      newConvictionState: {
        debateId,
        roundNumber: 7,
        bullVotes: 520,
        bearVotes: 408,
        bullStaked: 15200,
        bearStaked: 11200,
        totalParticipants: 145,
        uniqueBullVoters: 82,
        uniqueBearVoters: 63,
        lastUpdated: new Date().toISOString(),
      },
      estimatedPayout: stakeAmount * 1.15, // Mock 15% potential return
      txHash: mockVote.txHash,
    };

    return NextResponse.json<VoteResponse>(mockResponse);
  } catch (error) {
    console.error('Vote submission error:', error);

    return NextResponse.json<ErrorResponse>(
      {
        error: 'Failed to submit vote',
        code: 'VOTE_SUBMISSION_FAILED',
        details: process.env.NODE_ENV === 'development' 
          ? { message: error instanceof Error ? error.message : String(error) }
          : undefined,
      },
      { status: 500 }
    );
  }
}

/**
 * GET /api/debates/[debateId]/votes/user?userId=...
 * Get user's conviction votes for a debate
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<RouteParams> }
) {
  const { debateId } = await params;
  const userId = request.nextUrl.searchParams.get('userId');

  if (!debateId) {
    return NextResponse.json<ErrorResponse>(
      {
        error: 'Debate ID is required',
        code: 'INVALID_DEBATE_ID',
      },
      { status: 400 }
    );
  }

  if (!userId) {
    return NextResponse.json<ErrorResponse>(
      {
        error: 'User ID is required',
        code: 'MISSING_USER_ID',
      },
      { status: 400 }
    );
  }

  try {
    // TODO: Query user votes from database
    // For now, return mock data
    const userVotes: UserVote[] = [];

    return NextResponse.json({ votes: userVotes });
  } catch (error) {
    console.error('Error fetching user votes:', error);

    return NextResponse.json<ErrorResponse>(
      {
        error: 'Failed to fetch votes',
        code: 'FETCH_FAILED',
      },
      { status: 500 }
    );
  }
}
