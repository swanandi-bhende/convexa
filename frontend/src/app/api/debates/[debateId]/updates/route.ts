import { NextRequest, NextResponse } from 'next/server';
import { WebSocketMessage } from '@/types/api';

/**
 * GET /api/debates/[debateId]/updates
 * Server-Sent Events (SSE) endpoint for real-time debate updates
 * 
 * This endpoint streams real-time updates as they happen:
 * - Round started/completed
 * - Verdict revealed
 * - Timer ticks
 * - Conviction updates
 * - Debate completed
 */

interface RouteParams {
  debateId: string;
}

// In-memory store of active SSE connections (temporary - would use Redis in production)
const activeConnections = new Map<string, Set<ReadableStreamDefaultController>>();

/**
 * Broadcast a message to all connected clients for a debate
 */
export function broadcastDebateUpdate(debateId: string, message: WebSocketMessage) {
  const controllers = activeConnections.get(debateId);
  if (!controllers) return;

  const data = `data: ${JSON.stringify(message)}\n\n`;

  controllers.forEach((controller) => {
    try {
      controller.enqueue(new TextEncoder().encode(data));
    } catch (error) {
      // Connection closed, will be removed on next check
      console.error('Error sending SSE message:', error);
    }
  });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<RouteParams> }
) {
  const { debateId } = await params;

  if (!debateId || typeof debateId !== 'string') {
    return NextResponse.json({ error: 'Invalid debate ID' }, { status: 400 });
  }

  // Check if client supports SSE
  const acceptHeader = request.headers.get('accept') || '';
  if (!acceptHeader.includes('text/event-stream')) {
    return NextResponse.json(
      { error: 'This endpoint requires text/event-stream accept header' },
      { status: 406 }
    );
  }

  let controller: ReadableStreamDefaultController;

  const stream = new ReadableStream({
    start(ctrl) {
      controller = ctrl;

      // Add this connection to the active set
      if (!activeConnections.has(debateId)) {
        activeConnections.set(debateId, new Set());
      }
      activeConnections.get(debateId)!.add(controller);

      // Send initial connection message
      const welcome: WebSocketMessage = {
        type: 'timer_tick',
        payload: { message: 'Connected to debate stream' },
        timestamp: new Date().toISOString(),
      };
      const data = `data: ${JSON.stringify(welcome)}\n\n`;
      ctrl.enqueue(new TextEncoder().encode(data));
    },
    cancel() {
      // Remove this connection from the active set
      const controllers = activeConnections.get(debateId);
      if (controllers) {
        controllers.delete(controller);
        if (controllers.size === 0) {
          activeConnections.delete(debateId);
        }
      }
    },
  });

  return new NextResponse(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
