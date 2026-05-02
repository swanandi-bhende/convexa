import { NextResponse } from 'next/server';

// Mock debate state - in production, this would come from the blockchain
const mockDebateState = {
  currentRound: 5,
  debateActive: true,
  currentBullScore: 42,
  currentBearScore: 38,
  bullStakeTotal: '2.5',
  bearStakeTotal: '1.8',
  connectionStatus: 'live' as const,
};

export async function GET() {
  try {
    return NextResponse.json(mockDebateState);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch debate state' },
      { status: 500 }
    );
  }
}
