import { NextResponse } from 'next/server';
import type { RoundResult } from '@/store/debateStore';

// Mock round history - in production, this would query SQLite or a database
const mockRoundHistory: RoundResult[] = [
  {
    roundNumber: 5,
    bullScore: 42,
    bearScore: 38,
    winner: 'bull',
    judgeReasoning: 'Bull presented stronger technical analysis with clear market dynamics',
    timestamp: Date.now() - 5000,
  },
  {
    roundNumber: 4,
    bullScore: 35,
    bearScore: 41,
    winner: 'bear',
    judgeReasoning: 'Bear correctly identified support level breach and momentum shift',
    timestamp: Date.now() - 15000,
  },
  {
    roundNumber: 3,
    bullScore: 38,
    bearScore: 35,
    winner: 'bull',
    judgeReasoning: 'Bull bullish momentum and on-chain whale accumulation data was convincing',
    timestamp: Date.now() - 25000,
  },
  {
    roundNumber: 2,
    bullScore: 31,
    bearScore: 36,
    winner: 'bear',
    judgeReasoning: 'Bear macro headwinds argument more compelling',
    timestamp: Date.now() - 35000,
  },
  {
    roundNumber: 1,
    bullScore: 28,
    bearScore: 32,
    winner: 'bear',
    judgeReasoning: 'Initial round - Bear starts with technical weakness argument',
    timestamp: Date.now() - 45000,
  },
];

export async function GET() {
  try {
    return NextResponse.json(mockRoundHistory);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch round history' },
      { status: 500 }
    );
  }
}
