import type { ChatSession, Message, UserProfile } from './types';

// ── Keys ─────────────────────────────────────────────────────────────────────
const SESSIONS_KEY = 'finnie_sessions';
const ACTIVE_SESSION_KEY = 'finnie_active_session';
const PROFILE_KEY = 'finnie_profile';

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
