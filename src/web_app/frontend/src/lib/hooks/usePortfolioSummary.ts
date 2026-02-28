import { useEffect, useState, useCallback } from 'react';
import { BASE_URL } from '../config';

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
  const [data, setData] = useState<RawApi>(cached);
  const [loaded, setLoaded] = useState<boolean>(cached !== null);

  const refresh = useCallback(async (force = false) => {
    const sessionId = resolveBackendSid();
    if (!sessionId) { setData(null); setLoaded(true); return; }

    // Respect TTL unless forced (e.g. after a trade)
    if (!force && cached && (Date.now() - lastFetchedAt) < TTL) {
      setData(cached);
      setLoaded(true);
      return;
    }

    try {
      const res = await fetch(`${BASE_URL}/portfolio/summary/${sessionId}`);
      if (!res.ok) { setData(null); setLoaded(true); return; }
      const json: RawApi = await res.json();
      cached = json;
      lastFetchedAt = Date.now();
      setData(json);
      setLoaded(true);
    } catch {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    refresh();

    // After a trade, bust cache and force an immediate re-fetch
    const onUpdate = () => {
      cached = null;
      lastFetchedAt = 0;
      refresh(true).catch(() => {});
    };
    window.addEventListener('portfolioUpdated', onUpdate);
    return () => window.removeEventListener('portfolioUpdated', onUpdate);
  }, [refresh]);

  return { data, loaded, refresh } as const;
}

