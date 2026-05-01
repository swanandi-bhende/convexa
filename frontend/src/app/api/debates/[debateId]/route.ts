import { NextRequest, NextResponse } from 'next/server';
import { DebateSessionResponse, ErrorResponse } from '@/types/api';

/**
 * GET /api/debates/[debateId]
 * Fetch a complete debate session with all rounds, arguments, and verdicts
 * 
 * This is a server-side API that will eventually:
 * 1. Query the Python backend database (SQLite via REST API)
 * 2. Format the data into the API response types
 * 3. Return cached data with appropriate headers
 */

interface RouteParams {
  debateId: string;
}

// Simulated database query (will be replaced with actual backend API call)
async function fetchDebateFromBackend(
  debateId: string
): Promise<DebateSessionResponse | null> {
  try {
    // TODO: Replace with actual backend API call
    // Example: const response = await fetch(`${BACKEND_URL}/api/debates/${debateId}`);
    // For now, return null to indicate real data isn't available yet
    return null;
  } catch (error) {
    console.error(`Error fetching debate ${debateId}:`, error);
    throw error;
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<RouteParams> }
) {
  const { debateId } = await params;

  try {
    // Validate debateId format
    if (!debateId || typeof debateId !== 'string') {
      return NextResponse.json<ErrorResponse>(
        {
          error: 'Invalid debate ID',
          code: 'INVALID_DEBATE_ID',
        },
        { status: 400 }
      );
    }

    // Attempt to fetch from backend
    const debate = await fetchDebateFromBackend(debateId);

    if (!debate) {
      return NextResponse.json<ErrorResponse>(
        {
          error: 'Debate not found',
          code: 'DEBATE_NOT_FOUND',
        },
        { status: 404 }
      );
    }

    // Return with cache control headers
    // Cache for 5 seconds (debates update frequently during rounds)
    return NextResponse.json<DebateSessionResponse>(debate, {
      headers: {
        'Cache-Control': 'private, max-age=5, stale-while-revalidate=10',
      },
    });
  } catch (error) {
    console.error('API Error:', error);

    return NextResponse.json<ErrorResponse>(
      {
        error: 'Internal server error',
        code: 'INTERNAL_ERROR',
        details: process.env.NODE_ENV === 'development' ? { message: String(error) } : undefined,
      },
      { status: 500 }
    );
  }
}
