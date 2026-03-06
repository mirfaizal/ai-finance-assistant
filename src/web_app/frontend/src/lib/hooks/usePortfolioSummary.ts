import { useEffect, useState, useCallback } from 'react';
import { BASE_URL } from '../config';
import { getAuthHeaders } from '../api';
import { useAuth0 } from '@auth0/auth0-react';

type RawApi = {
  holdings?: { ticker: string; allocation_pct: number; current_value?: number; shares?: number; avg_cost?: number }[];
  summary?: { total_value?: number; total_pnl?: number; total_pnl_pct?: number; concentration_risk?: string };
} | null;

let cached: RawApi | null = null;
let lastFetchedAt = 0;
const TTL = 10_000; // 10 s normal TTL

/** Resolve the backend session UUID from localStorage.
 *
 * Priority order:
 * 1. Active frontend session → backend UUID via finnie_backend_session_map
 * 2. Most recently updated frontend session → backend UUID
 * 3. Any backend UUID from the map (first found)
 * Returns null only when no mapping exists at all.
 */
function resolveBackendSid(): string | null {
  // ── 1. Active session ────────────────────────────────────────────────────
  const activeFrontend = localStorage.getItem('finnie_active_session');
  if (activeFrontend) {
    try {
      const map: Record<string, string> = JSON.parse(
        localStorage.getItem('finnie_backend_session_map') ?? '{}',
      );
      if (map[activeFrontend]) return map[activeFrontend];
    } catch { /* continue */ }
  }

  // ── 2. Walk all sessions in recency order ────────────────────────────────
  try {
    const sessions: { id: string; updatedAt?: number }[] = JSON.parse(
      localStorage.getItem('finnie_sessions') ?? '[]',
    );
    const map: Record<string, string> = JSON.parse(
      localStorage.getItem('finnie_backend_session_map') ?? '{}',
    );
    // Sessions are stored newest-first; iterate to find first with a backend ID
    for (const s of sessions) {
      if (map[s.id]) return map[s.id];
    }
    // ── 3. Any backend ID at all ───────────────────────────────────────────
    const values = Object.values(map);
    if (values.length > 0) return values[values.length - 1];
  } catch { /* ignore */ }

  return null;
}


export function usePortfolioSummary() {
  const { user } = useAuth0();
  const userEmail = user?.email;
  
  const [data, setData] = useState<RawApi>(cached);
  const [loaded, setLoaded] = useState<boolean>(cached !== null);

  const refresh = useCallback(async (force = false) => {
    const sessionId = resolveBackendSid();
    const headers = await getAuthHeaders();
    
    // Fallback: If App.tsx hasn't populated api.ts yet, manually inject from useAuth0
    if (userEmail && !headers['X-User-Email']) {
      headers['X-User-Email'] = userEmail;
    }
    
    // If the user is neither logged in via Auth0 nor has an anonymous chat session, block.
    if (!sessionId && !headers['X-User-Email']) { 
      setData(null); 
      setLoaded(true); 
      return; 
    }

    // Respect TTL unless forced (e.g. after a trade)
    if (!force && cached && (Date.now() - lastFetchedAt) < TTL) {
      setData(cached);
      setLoaded(true);
      return;
    }

    try {
      // The backend prioritizes X-User-Email over the session_id path parameter.
      // If we don't have a local session_id but we have an email, pass 'default' to satisfy the URL path.
      const targetSession = sessionId || 'default';
      const res = await fetch(`${BASE_URL}/portfolio/summary/${targetSession}`, { headers });
      if (!res.ok) { setData(null); setLoaded(true); return; }
      const json: RawApi = await res.json();
      cached = json;
      lastFetchedAt = Date.now();
      setData(json);
      setLoaded(true);
    } catch {
      setLoaded(true);
    }
  }, [userEmail]);

  useEffect(() => {
    // Force a fetch immediately when userEmail resolves from undefined to a string
    refresh(!!userEmail);

    // After a trade, bust cache and force an immediate re-fetch
    const onUpdate = () => {
      cached = null;
      lastFetchedAt = 0;
      refresh(true).catch(() => {});
    };
    window.addEventListener('portfolioUpdated', onUpdate);
    return () => window.removeEventListener('portfolioUpdated', onUpdate);
  }, [refresh, userEmail]);

  return { data, loaded, refresh } as const;
}

