import { BASE_URL } from './config';

// Global token fetcher injected by the Auth0Provider React layer
let _getAccessToken: (() => Promise<string | undefined>) | null = null;
let _userEmail: string | undefined = undefined;

export function setAccessTokenFetcher(fetcher: () => Promise<string | undefined>) {
  _getAccessToken = fetcher;
}

export function setUserEmail(email: string | undefined) {
  _userEmail = email;
}

export async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  if (_getAccessToken) {
    try {
      const token = await _getAccessToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    } catch (err) {
      console.warn("Failed to get Auth0 access token", err);
    }
  }
  if (_userEmail) {
    headers['X-User-Email'] = _userEmail;
  }
  return headers;
}// ── Types ─────────────────────────────────────────────────────────────────────

export interface AskResponse {
  question: string;
  answer: string;
  agent: string;
  session_id: string;  // backend UUID, persisted so future turns keep context
  run_id?: string;
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
  const headers = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/ask`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId ?? undefined, user_email: _userEmail }),
  });

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`Backend error ${res.status}: ${errBody}`);
  }

  return res.json() as Promise<AskResponse>;
}

/**
 * Send feedback for an AI response back to LangSmith.
 * @param runId The LangSmith trace / run UUID.
 * @param score 1 for Thumbs Up, 0 for Thumbs Down.
 */
export async function sendFeedback(runId: string, score: number): Promise<{status: string}> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/feedback`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId, score }),
  });

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`Backend error ${res.status}: ${errBody}`);
  }

  return res.json() as Promise<{status: string}>;
}

/**
 * Fetch the stored conversation history for a backend session.
 * Useful for restoring the chat UI after a page reload.
 */
export async function fetchHistory(
  sessionId: string,
  lastN = 20,
): Promise<HistoryResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${BASE_URL}/history/${encodeURIComponent(sessionId)}?last_n=${lastN}`,
    { headers }
  );

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`Backend error ${res.status}: ${errBody}`);
  }

  return res.json() as Promise<HistoryResponse>;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${BASE_URL}/health`, { headers });
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
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${BASE_URL}/portfolio/holdings/${encodeURIComponent(sessionId)}`,
    { headers }
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

  const headers = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/quiz/generate?${body.toString()}`, {
    method: 'POST',
    headers
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

  const headers = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/quiz/answer?${params.toString()}`, { method: 'POST', headers });
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

export async function getCoinBalance(sessionId: string) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/quiz/coins/${encodeURIComponent(sessionId)}`, { headers });
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}

// ── Quiz Pool (Pinecone-backed, pre-seeded questions) ─────────────────────────

/**
 * Fetch a random unseen quiz question from the Pinecone quiz-pool.
 * Pass sessionId so already-answered questions are skipped.
 * Pass topic to filter by course topic (e.g. 'crypto-basics').
 */
export async function getPoolQuiz(
  sessionId?: string | null,
  topic?: string | null,
): Promise<QuizQuestion> {
  const params = new URLSearchParams();
  if (sessionId) params.set('session_id', sessionId);
  if (topic) params.set('topic', topic);

  const headers = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/quiz/pool/random?${params.toString()}`, { headers });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Backend error ${res.status}: ${err}`);
  }
  return res.json() as Promise<QuizQuestion>;
}

// ── Financial Academy course content (RAG-backed) ─────────────────────────────

export interface CourseBlock {
  text: string;
  score: number;
  doc: string;
}

export interface AcademyCourseResponse {
  slug: string;
  title: string;
  blocks: CourseBlock[];
  from_rag: boolean;
}

/**
 * Fetch RAG-retrieved content blocks for a given course slug.
 * slug: 'investing-101' | 'tax-strategies' | 'market-mechanics' | 'crypto-basics'
 */
export async function getAcademyCourse(slug: string): Promise<AcademyCourseResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${BASE_URL}/academy/course/${encodeURIComponent(slug)}`, { headers });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Backend error ${res.status}: ${err}`);
  }
  return res.json() as Promise<AcademyCourseResponse>;
}

/**
 * Trigger the Pinecone quiz-pool seed (admin / dev helper).
 * Requires RAG_ADMIN_KEY header if the server has RAG_ADMIN_KEY env var set.
 */
export async function seedQuizPool(adminKey?: string): Promise<{ seeded: number }> {
  const headers = await getAuthHeaders();
  if (adminKey) headers['X-RAG-ADMIN-KEY'] = adminKey;
  const res = await fetch(`${BASE_URL}/quiz/seed-pool`, { method: 'POST', headers });
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  return res.json();
}
