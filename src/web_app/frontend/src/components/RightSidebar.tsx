import { useEffect, useRef, useState } from 'react';
import { MarketChart } from './MarketChart';
import { PortfolioChart } from './PortfolioChart';
import { TrendingUp, TrendingDown, ExternalLink } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell } from 'recharts';
import { BASE_URL } from '../lib/config';
import { usePortfolioSummary } from '../lib/hooks/usePortfolioSummary';

const CACHE_TTL = 5 * 60 * 1000;
const INDEX_SYMBOLS = 'SPY,QQQ';
const WATCHLIST_SYMBOLS = 'AAPL,MSFT,GOOGL,TSLA';
const PIE_COLORS = ['#14b8a6', '#8b5cf6', '#3b82f6', '#f59e0b', '#10b981', '#ec4899', '#f97316', '#6b7280'];

interface QuoteRow {
  symbol: string;
  price: number | null;
  change_pct: number | null;
  up: boolean | null;
}

interface AllocBar { name: string; value: number; fill: string; }

// shared hook provides the summary shape; explicit local type removed to avoid duplication

interface NewsArticle {
  title: string;
  publisher: string;
  link: string;
  published_at: string;
  ticker: string;
}

const WATCHLIST_LABELS: Record<string, string> = {
  AAPL: 'Tech', MSFT: 'Tech', GOOGL: 'Tech', TSLA: 'EV',
};

function timeAgo(iso: string): string {
  if (!iso) return '';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function RightSidebar() {
  const [indices, setIndices] = useState<QuoteRow[]>([]);
  const [watchlist, setWatchlist] = useState<QuoteRow[]>([]);
  const { data: portfolioSummary } = usePortfolioSummary();
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);
  const cachedAt = useRef<number>(0);
  const newsCachedAt = useRef<number>(0);

  // ── Market quotes ──────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (Date.now() - cachedAt.current < CACHE_TTL && indices.length > 0) return;
      try {
        const res = await fetch(
          `${BASE_URL}/market/quotes?symbols=${INDEX_SYMBOLS},${WATCHLIST_SYMBOLS}`,
        );
        if (!res.ok) return;
        const json: Record<string, { price: number; change_pct: number; up: boolean }> =
          await res.json();
        if (!cancelled) {
          cachedAt.current = Date.now();
          const indexList = INDEX_SYMBOLS.split(',').map((symbol) => {
            const d = json[symbol];
            return {
              symbol: symbol === 'SPY' ? 'S&P 500' : symbol === 'QQQ' ? 'NASDAQ' : symbol,
              price: d?.price ?? null,
              change_pct: d?.change_pct ?? null,
              up: d?.up ?? null,
            };
          });
          const watchList = WATCHLIST_SYMBOLS.split(',').map((symbol) => ({
            symbol,
            price: json[symbol]?.price ?? null,
            change_pct: json[symbol]?.change_pct ?? null,
            up: json[symbol]?.up ?? null,
          }));
          setIndices(indexList);
          setWatchlist(watchList);
        }
      } catch {
        setIndices([
          { symbol: 'S&P 500', price: null, change_pct: null, up: null },
          { symbol: 'NASDAQ',  price: null, change_pct: null, up: null },
        ]);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // ── Portfolio summary from SQLite WAL ─────────────────────────────────────
  // hook handles fetch + refresh and adds event listener

  // ── Market News from yfinance ─────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    async function loadNews() {
      if (Date.now() - newsCachedAt.current < CACHE_TTL && news.length > 0) return;
      setNewsLoading(true);
      try {
        const res = await fetch(`${BASE_URL}/market/news?limit=8`);
        if (!res.ok) return;
        const data: { articles: NewsArticle[] } = await res.json();
        if (!cancelled) {
          newsCachedAt.current = Date.now();
          setNews(data.articles ?? []);
        }
      } catch {
        // no news available
      } finally {
        if (!cancelled) setNewsLoading(false);
      }
    }
    loadNews();
    return () => { cancelled = true; };
  }, []);

  // ── Allocation bar data: live from SQLite holdings ─────────────────────────
  const allocBarData: AllocBar[] = (portfolioSummary && portfolioSummary.holdings && portfolioSummary.holdings.length > 0)
    ? portfolioSummary.holdings
        .sort((a, b) => b.allocation_pct - a.allocation_pct)
        .slice(0, 6)
        .map((h, i) => ({ name: h.ticker, value: parseFloat(h.allocation_pct.toFixed(1)), fill: PIE_COLORS[i % PIE_COLORS.length] }))
    : [{ name: 'No positions', value: 100, fill: '#1e2a3a' }];

  const hasSummary = (portfolioSummary?.summary?.total_value ?? 0) > 0;

  return (
    <aside className="right-sidebar">
      {/* Market Overview */}
      <div className="right-sidebar-block market-overview-block">
        <h3 className="right-sidebar-title">Market Overview</h3>
        <p className="right-sidebar-subtitle">Real-time data updates</p>
        <div className="market-overview-indices">
          {indices.length === 0 ? (
            <>
              <div className="index-row"><span className="index-name">S&P 500</span><span className="index-value">—</span></div>
              <div className="index-row"><span className="index-name">NASDAQ</span><span className="index-value">—</span></div>
            </>
          ) : (
            indices.map((row) => (
              <div key={row.symbol} className="index-row">
                <span className="index-name">{row.symbol}</span>
                <div className="index-right">
                  <span className="index-value">
                    {row.price != null
                      ? row.price >= 10000
                        ? row.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                        : row.price.toFixed(2)
                      : '—'}
                  </span>
                  {row.change_pct != null && (
                    <span className={`index-change ${row.up ? 'up' : 'down'}`}>
                      {row.up ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      {row.up ? '+' : ''}{row.change_pct.toFixed(2)}%
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Portfolio Performance – SPY/QQQ/DIA from yfinance */}
      <div className="right-sidebar-block">
        <h3 className="right-sidebar-title">PORTFOLIO PERFORMANCE</h3>
        <p className="right-sidebar-subtitle">Market Trends</p>
        <MarketChart hideHeader />
      </div>

      {/* Asset Allocation – live from SQLite WAL */}
      <div className="right-sidebar-block">
        <h3 className="right-sidebar-title">ASSET ALLOCATION</h3>
        <p className="right-sidebar-subtitle">
          {hasSummary
            ? `$${portfolioSummary?.summary?.total_value?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '0.00'} · ${portfolioSummary?.holdings?.length ?? 0} position${(portfolioSummary?.holdings?.length ?? 0) !== 1 ? 's' : ''}`
            : 'Portfolio Allocation'}
        </p>
        {hasSummary && (
          <p style={{ fontSize: 10, marginBottom: 4, color: (portfolioSummary?.summary?.total_pnl ?? 0) >= 0 ? '#10b981' : '#ef4444' }}>
            P&amp;L: {(portfolioSummary?.summary?.total_pnl ?? 0) >= 0 ? '+' : ''}
            {(portfolioSummary?.summary?.total_pnl_pct ?? 0).toFixed(2)}%
          </p>
        )}
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={allocBarData} layout="vertical" margin={{ top: 4, right: 16, left: 56, bottom: 4 }}>
            <XAxis type="number" tick={{ fontSize: 9, fill: '#6b7280' }} domain={[0, 100]} unit="%" />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#e5e7eb' }} width={52} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {allocBarData.map((entry, i) => (
                <Cell key={entry.name} fill={entry.fill ?? PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Watchlist */}
      <div className="right-sidebar-block">
        <h3 className="right-sidebar-title">WATCHLIST</h3>
        <div className="watchlist-list">
          {watchlist.length === 0
            ? [1, 2, 3, 4].map((i) => (
                <div key={i} className="watchlist-row" style={{ opacity: 0.4 }}>
                  <span className="watchlist-avatar">·</span>
                  <span className="watchlist-symbol">—</span>
                  <span className="watchlist-price">—</span>
                </div>
              ))
            : watchlist.map((row) => (
                <div key={row.symbol} className="watchlist-row">
                  <span className="watchlist-avatar">{row.symbol.slice(0, 1)}</span>
                  <div className="watchlist-info">
                    <span className="watchlist-symbol">{row.symbol}</span>
                    <span className="watchlist-type">{WATCHLIST_LABELS[row.symbol] ?? '—'}</span>
                  </div>
                  <div className="watchlist-right">
                    <span className="watchlist-price">
                      ${row.price != null ? row.price.toFixed(2) : '—'}
                    </span>
                    {row.change_pct != null && (
                      <span className={`watchlist-change ${row.up ? 'up' : 'down'}`}>
                        {row.up ? '+' : ''}{row.change_pct.toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
        </div>
      </div>

      {/* Market News – from yfinance */}
      <div className="right-sidebar-block">
        <h3 className="right-sidebar-title">MARKET NEWS</h3>
        <p className="right-sidebar-subtitle">Latest from yFinance</p>
        {newsLoading && (
          <p style={{ fontSize: 11, color: '#6b7280', padding: '8px 0' }}>Loading…</p>
        )}
        {!newsLoading && news.length === 0 && (
          <p style={{ fontSize: 11, color: '#6b7280', padding: '8px 0' }}>No news available</p>
        )}
        <div className="sidebar-news-list">
          {news.map((article, i) => (
            <a
              key={i}
              href={article.link || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="news-item"
            >
              <div className="news-item-header">
                <span className="news-ticker-badge">{article.ticker}</span>
                <span className="news-time">{timeAgo(article.published_at)}</span>
              </div>
              <p className="news-title">{article.title}</p>
              <div className="news-footer">
                <span className="news-publisher">{article.publisher}</span>
                {article.link && <ExternalLink size={10} className="news-link-icon" />}
              </div>
            </a>
          ))}
        </div>
      </div>

      {/* Portfolio Allocation pie – from SQLite WAL */}
      <PortfolioChart />
    </aside>
  );
}
