import { NextResponse } from 'next/server';
import type { Transaction } from '@/store/debateStore';

// Mock transaction log
const mockTransactions: Transaction[] = [
  {
    hash: '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
    type: 'conviction',
    from: '0xJudgeAgent...',
    amount: '0',
    timestamp: Date.now(),
    status: 'confirmed',
  },
  {
    hash: '0x2345678901bcdef1234567890abcdef1234567890abcdef1234567890abcdef1',
    type: 'deposit',
    from: '0xUser123...',
    amount: '0.5',
    timestamp: Date.now() - 3000,
    status: 'confirmed',
  },
  {
    hash: '0x3456789012cdef1234567890abcdef1234567890abcdef1234567890abcdef12',
    type: 'swap',
    from: '0xKeeper...',
    amount: '2500.00',
    timestamp: Date.now() - 6000,
    status: 'confirmed',
    keeperJobId: 'job_kh_abc123xyz',
  },
  {
    hash: '0x4567890123def1234567890abcdef1234567890abcdef1234567890abcdef123',
    type: 'deposit',
    from: '0xBear123...',
    amount: '0.75',
    timestamp: Date.now() - 9000,
    status: 'confirmed',
  },
  {
    hash: '0x56789012345ef1234567890abcdef1234567890abcdef1234567890abcdef1234',
    type: 'conviction',
    from: '0xJudgeAgent...',
    amount: '0',
    timestamp: Date.now() - 12000,
    status: 'pending',
  },
  {
    hash: '0x6789012345f1234567890abcdef1234567890abcdef1234567890abcdef12345',
    type: 'swap',
    from: '0xKeeper...',
    amount: '1800.00',
    timestamp: Date.now() - 15000,
    status: 'confirmed',
    keeperJobId: 'job_kh_xyz789abc',
  },
  {
    hash: '0x789012345f1234567890abcdef1234567890abcdef1234567890abcdef123456',
    type: 'deposit',
    from: '0xWalletA...',
    amount: '1.2',
    timestamp: Date.now() - 18000,
    status: 'confirmed',
  },
];

export async function GET() {
  try {
    return NextResponse.json(mockTransactions);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch transactions' },
      { status: 500 }
    );
  }
}
