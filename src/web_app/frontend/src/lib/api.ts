const BASE_URL = 'http://localhost:8000';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AskResponse {
  question: string;
  answer: string;
  agent: string;
  session_id: string;  // backend UUID, persisted so future turns keep context
}

export interface HistoryMessage {
  role: 'user' | 'assistant' | 'summary';
  content: string;
}

export interface HistoryResponse {
  session_id: string;
  messages: HistoryMessage[];
}

// ── API helpers ───────────────────────────────────────────────────────────────

/**
 * Send a question to the backend.
 *
 * Pass `sessionId` to continue an existing backend session; omit to start
 * a new one.  The returned `session_id` should be persisted and passed back
 * on every subsequent call within the same chat session.
 */
export async function askQuestion(
  question: string,
  sessionId?: string | null,
): Promise<AskResponse> {
  const res = await fetch(`${BASE_URL}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId ?? undefined }),
  });

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`Backend error ${res.status}: ${errBody}`);
  }

  return res.json() as Promise<AskResponse>;
}

/**
 * Fetch the stored conversation history for a backend session.
 * Useful for restoring the chat UI after a page reload.
 */
export async function fetchHistory(
  sessionId: string,
  lastN = 20,
): Promise<HistoryResponse> {
  const res = await fetch(
    `${BASE_URL}/history/${encodeURIComponent(sessionId)}?last_n=${lastN}`,
  );

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`Backend error ${res.status}: ${errBody}`);
  }

  return res.json() as Promise<HistoryResponse>;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
