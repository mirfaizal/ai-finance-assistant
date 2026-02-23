import { useEffect, useRef, useState } from 'react';
import { MarketChart } from './MarketChart';
import { PortfolioChart } from './PortfolioChart';
import { TrendingUp, TrendingDown } from 'lucide-react';

import { BASE_URL } from '../lib/config';
const CACHE_TTL = 5 * 60 * 1000;
const DEFAULT_SYMBOLS = 'SPY,AAPL,TSLA,NVDA,BTC-USD';

interface TickerData {
    symbol: string;
    price: number | null;
    change_pct: number | null;
    up: boolean | null;
}

export function RightSidebar() {
    const [tickers, setTickers] = useState<TickerData[]>([]);
    const cachedAt = useRef<number>(0);

    useEffect(() => {
        let cancelled = false;
        async function load() {
            if (Date.now() - cachedAt.current < CACHE_TTL && tickers.length > 0) return;
            try {
                const res = await fetch(
                    `${BASE_URL}/market/quotes?symbols=${DEFAULT_SYMBOLS}`,
                );
                if (!res.ok) return;
                const json: Record<string, { price: number; change_pct: number; up: boolean }> =
                    await res.json();
                if (!cancelled) {
                    cachedAt.current = Date.now();
                    setTickers(
                        Object.entries(json).map(([symbol, d]) => ({
                            symbol,
                            price: d.price,
                            change_pct: d.change_pct,
                            up: d.up,
                        })),
                    );
                }
            } catch { /* silently fail — sidebar is non-critical */ }
        }
        load();
        return () => { cancelled = true; };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <aside className="right-sidebar">
            {/* Ticker strip */}
            <div className="ticker-strip">
                {tickers.length === 0
                    ? // Skeleton
                    [1, 2, 3, 4, 5].map((i) => (
                        <div key={i} className="ticker-item" style={{ opacity: 0.3 }}>
                            <span className="ticker-symbol">···</span>
                        </div>
                    ))
                    : tickers.map((t) => (
                        <div key={t.symbol} className="ticker-item">
                            <span className="ticker-symbol">{t.symbol.replace('-USD', '')}</span>
                            <span className="ticker-price">
                                {t.price != null
                                    ? t.price >= 1000
                                        ? t.price.toLocaleString('en-US', { maximumFractionDigits: 0 })
                                        : t.price.toFixed(2)
                                    : '—'}
                            </span>
                            {t.change_pct != null && (
                                <span className={`ticker-change ${t.up ? 'up' : 'down'}`}>
                                    {t.up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                                    {t.up ? '+' : ''}
                                    {t.change_pct.toFixed(2)}%
                                </span>
                            )}
                        </div>
                    ))}
            </div>

            <MarketChart />
            <PortfolioChart />
        </aside>
    );
}

