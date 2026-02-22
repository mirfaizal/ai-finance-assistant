import type { ChatSession, Message, UserProfile } from './types';

// ── Keys ─────────────────────────────────────────────────────────────────────
const SESSIONS_KEY = 'finnie_sessions';
const ACTIVE_SESSION_KEY = 'finnie_active_session';
const PROFILE_KEY = 'finnie_profile';
/** Maps frontend session UUID → backend session UUID for memory continuity. */
const BACKEND_SESSION_MAP_KEY = 'finnie_backend_session_map';

// ── Sessions ──────────────────────────────────────────────────────────────────

export function getSessions(): ChatSession[] {
  try {
    return JSON.parse(localStorage.getItem(SESSIONS_KEY) ?? '[]');
  } catch {
    return [];
  }
}

export function saveSessions(sessions: ChatSession[]): void {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
}

export function getActiveSessionId(): string | null {
  return localStorage.getItem(ACTIVE_SESSION_KEY);
}

export function setActiveSessionId(id: string): void {
  localStorage.setItem(ACTIVE_SESSION_KEY, id);
}

export function createSession(): ChatSession {
  const session: ChatSession = {
    id: crypto.randomUUID(),
    title: 'New conversation',
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
  const sessions = getSessions();
  sessions.unshift(session);
  saveSessions(sessions);
  setActiveSessionId(session.id);
  return session;
}

export function getSession(id: string): ChatSession | null {
  return getSessions().find((s) => s.id === id) ?? null;
}

export function deleteSession(sessionId: string): void {
  const sessions = getSessions().filter((s) => s.id !== sessionId);
  saveSessions(sessions);
  if (getActiveSessionId() === sessionId) {
    localStorage.removeItem(ACTIVE_SESSION_KEY);
  }
  removeBackendSessionId(sessionId);
}

export function appendMessage(sessionId: string, message: Message): void {
  const sessions = getSessions();
  const session = sessions.find((s) => s.id === sessionId);
  if (!session) return;

  session.messages.push(message);
  session.updatedAt = Date.now();

  // Auto-title: use first user message (max 40 chars)
  if (session.title === 'New conversation' && message.role === 'user') {
    session.title = message.content.length > 40
      ? message.content.slice(0, 40) + '…'
      : message.content;
  }

  saveSessions(sessions);
}

// ── Backend session mapping ───────────────────────────────────────────────────

/**
 * Retrieve the backend UUID associated with a frontend chat session.
 * Returns `null` on the first message of a brand-new session.
 */
export function getBackendSessionId(frontendSessionId: string): string | null {
  try {
    const map: Record<string, string> = JSON.parse(
      localStorage.getItem(BACKEND_SESSION_MAP_KEY) ?? '{}',
    );
    return map[frontendSessionId] ?? null;
  } catch {
    return null;
  }
}

/**
 * Persist the backend UUID for a frontend chat session so that future
 * messages are sent with the correct session context.
 */
export function setBackendSessionId(
  frontendSessionId: string,
  backendSessionId: string,
): void {
  try {
    const map: Record<string, string> = JSON.parse(
      localStorage.getItem(BACKEND_SESSION_MAP_KEY) ?? '{}',
    );
    map[frontendSessionId] = backendSessionId;
    localStorage.setItem(BACKEND_SESSION_MAP_KEY, JSON.stringify(map));
  } catch {
    // localStorage unavailable — silently ignore (session will be stateless)
  }
}

/**
 * Remove the backend session mapping when the user deletes a chat session,
 * so stale UUIDs don't accumulate in localStorage.
 */
export function removeBackendSessionId(frontendSessionId: string): void {
  try {
    const map: Record<string, string> = JSON.parse(
      localStorage.getItem(BACKEND_SESSION_MAP_KEY) ?? '{}',
    );
    delete map[frontendSessionId];
    localStorage.setItem(BACKEND_SESSION_MAP_KEY, JSON.stringify(map));
  } catch {
    // ignore
  }
}

// ── Profile ───────────────────────────────────────────────────────────────────

const DEFAULT_PROFILE: UserProfile = {
  isNewUser: true,
  riskTolerance: null,
  investmentGoals: [],
  completedOnboarding: false,
};

export function getProfile(): UserProfile {
  try {
    return JSON.parse(localStorage.getItem(PROFILE_KEY) ?? 'null') ?? DEFAULT_PROFILE;
  } catch {
    return DEFAULT_PROFILE;
  }
}

export function saveProfile(profile: UserProfile): void {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
}
