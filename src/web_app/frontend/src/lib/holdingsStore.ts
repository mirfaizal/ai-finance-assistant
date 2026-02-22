/**
 * Persistent holdings store backed by localStorage.
 *
 * A "holding" is a position the user owns: { ticker, shares, avg_cost }.
 * The backend /portfolio/analyze endpoint accepts this shape directly.
 *
 * Nothing is sent to the server automatically — the chart components
 * POST to /portfolio/analyze on demand using whatever is stored here.
 */

const HOLDINGS_KEY = 'finnie_holdings';

export interface Holding {
  ticker: string;
  shares: number;
  avg_cost: number;
}

// ── Persistence ───────────────────────────────────────────────────────────────

export function getHoldings(): Holding[] {
  try {
    return JSON.parse(localStorage.getItem(HOLDINGS_KEY) ?? '[]');
  } catch {
    return [];
  }
}

export function saveHoldings(holdings: Holding[]): void {
  localStorage.setItem(HOLDINGS_KEY, JSON.stringify(holdings));
}

export function addHolding(h: Holding): void {
  const existing = getHoldings();
  // Merge duplicate tickers by averaging cost and summing shares
  const idx = existing.findIndex(
    (e) => e.ticker.toUpperCase() === h.ticker.toUpperCase(),
  );
  if (idx !== -1) {
    const prev = existing[idx];
    const totalShares = prev.shares + h.shares;
    existing[idx] = {
      ticker: h.ticker.toUpperCase(),
      shares: totalShares,
      avg_cost:
        (prev.avg_cost * prev.shares + h.avg_cost * h.shares) / totalShares,
    };
  } else {
    existing.push({ ...h, ticker: h.ticker.toUpperCase() });
  }
  saveHoldings(existing);
}

export function removeHolding(ticker: string): void {
  saveHoldings(
    getHoldings().filter(
      (h) => h.ticker.toUpperCase() !== ticker.toUpperCase(),
    ),
  );
}

export function clearHoldings(): void {
  localStorage.removeItem(HOLDINGS_KEY);
}
