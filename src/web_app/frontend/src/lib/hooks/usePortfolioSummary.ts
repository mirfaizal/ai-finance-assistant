import { useEffect, useState } from 'react';
import { BASE_URL } from '../config';
import { getActiveSessionId, getBackendSessionId } from '../storage';

type RawApi = {
  holdings?: { ticker: string; allocation_pct: number; current_value?: number; shares?: number; avg_cost?: number }[];
  summary?: { total_value?: number; total_pnl?: number; total_pnl_pct?: number; concentration_risk?: string };
} | null;

let cached: RawApi | null = null;
let lastFetchedAt = 0;
const TTL = 5000; // short TTL so components stay reasonably fresh

export function usePortfolioSummary() {
  const [data, setData] = useState<RawApi>(cached);
  const [loaded, setLoaded] = useState<boolean>(cached !== null);

  async function refresh() {
    const frontendSid = getActiveSessionId();
    if (!frontendSid) { setData(null); setLoaded(true); return; }
    const sessionId = getBackendSessionId(frontendSid) ?? frontendSid;
    try {
      const res = await fetch(`${BASE_URL}/portfolio/summary/${sessionId}`);
      if (!res.ok) { setData(null); setLoaded(true); return; }
      const json: RawApi = await res.json();
      cached = json;
      lastFetchedAt = Date.now();
      setData(json);
      setLoaded(true);
    } catch {
      // network error
      setLoaded(true);
    }
  }

  useEffect(() => {
    let mounted = true;
    const shouldFetch = !cached || (Date.now() - lastFetchedAt) > TTL;
    if (shouldFetch) {
      refresh().catch(() => {});
    } else if (mounted) {
      setData(cached);
      setLoaded(true);
    }

    const onUpdate = () => refresh().catch(() => {});
    window.addEventListener('portfolioUpdated', onUpdate);
    return () => { mounted = false; window.removeEventListener('portfolioUpdated', onUpdate); };
  }, []);

  return { data, loaded, refresh } as const;
}
