import { BASE_URL } from './config';

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

// ── Portfolio endpoints ───────────────────────────────────────────────────────

export interface BackendHolding {
  ticker: string;
  shares: number;
  avg_cost: number;
  updated_at: string;
}

export interface PortfolioHoldingsResponse {
  session_id: string;
  holdings: BackendHolding[];
  count: number;
}

/**
 * Fetch the current paper-portfolio holdings for a backend session.
 * Called after every trading_agent response to sync SQLite → localStorage.
 */
export async function getPortfolioHoldings(
  sessionId: string,
): Promise<PortfolioHoldingsResponse> {
  const res = await fetch(
    `${BASE_URL}/portfolio/holdings/${encodeURIComponent(sessionId)}`,
  );
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json() as Promise<PortfolioHoldingsResponse>;
}

// ── Quiz endpoints ──────────────────────────────────────────────────────────

export interface QuizQuestion {
  question_id: string;
  question: string;
  choices: string[];
}

export async function generateQuiz(topic: string, sessionId?: string | null): Promise<QuizQuestion> {
  const body = new URLSearchParams();
  body.set('topic', topic);
  if (sessionId) body.set('session_id', sessionId);

  const res = await fetch(`${BASE_URL}/quiz/generate?${body.toString()}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Backend error ${res.status}: ${err}`);
  }
  return res.json() as Promise<QuizQuestion>;
}

export async function submitQuizAnswer(questionId: string, selectedIndex: number, sessionId?: string | null) {
  const params = new URLSearchParams();
  params.set('question_id', questionId);
  params.set('selected_index', String(selectedIndex));
  if (sessionId) params.set('session_id', sessionId);

  const res = await fetch(`${BASE_URL}/quiz/answer?${params.toString()}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

export async function getCoinBalance(sessionId: string) {
  const res = await fetch(`${BASE_URL}/quiz/coins/${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}
