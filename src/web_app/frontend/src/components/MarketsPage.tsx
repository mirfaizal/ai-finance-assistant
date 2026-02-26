import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { BarChart, Bar, Cell, LabelList } from 'recharts';
import { BASE_URL } from '../lib/config';
import { getActiveSessionId, getBackendSessionId } from '../lib/storage';

interface ChartPoint { date: string; value: number; }
interface AllocBar { name: string; pct: number; dollarValue: string; fill: string; }

const PIE_COLORS = ['#14b8a6', '#8b5cf6', '#3b82f6', '#f59e0b', '#10b981', '#ec4899', '#f97316', '#6b7280'];

interface PortfolioSummary {
  holdings: { ticker: string; allocation_pct: number; current_value: number }[];
  summary: { total_value: number; total_pnl: number; total_pnl_pct: number };
}

export function MarketsPage() {
  const [chartData, setChartData] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [portfolioLoaded, setPortfolioLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${BASE_URL}/market/chart`);
        if (!res.ok) throw new Error('');
        const raw: { date: string; sp500: number; nasdaq: number; dow: number }[] = await res.json();
        if (!cancelled) {
          const byWeek = raw.slice(-7).map((d) => ({
            date: d.date.length >= 3 ? d.date.slice(0, 3) : d.date,
            value: d.sp500 ?? 0,
          }));
          setChartData(byWeek.length ? byWeek : [
            { date: 'Mon', value: 5200 }, { date: 'Tue', value: 5280 }, { date: 'Wed', value: 5350 },
            { date: 'Thu', value: 5320 }, { date: 'Fri', value: 5380 }, { date: 'Sun', value: 5420 },
          ]);
        }
      } catch {
        if (!cancelled) {
          setChartData([
            { date: 'Mon', value: 5200 }, { date: 'Tue', value: 5280 }, { date: 'Wed', value: 5350 },
            { date: 'Thu', value: 5320 }, { date: 'Fri', value: 5380 }, { date: 'Sun', value: 5420 },
          ]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const frontendSid = getActiveSessionId();
    if (!frontendSid) return;
    const sessionId = getBackendSessionId(frontendSid) ?? frontendSid;
    fetch(`${BASE_URL}/portfolio/summary/${sessionId}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { setPortfolioLoaded(true); if (data?.summary?.total_value > 0) setPortfolio(data); })
      .catch(() => { setPortfolioLoaded(true); });
    const onUpdate = () => {
      const sid = getBackendSessionId(getActiveSessionId() ?? '') ?? getActiveSessionId() ?? '';
      if (!sid) return;
      fetch(`${BASE_URL}/portfolio/summary/${sid}`)
        .then((r) => r.ok ? r.json() : null)
        .then((data) => { if (data?.summary?.total_value > 0) setPortfolio(data); })
        .catch(() => {});
    };
    window.addEventListener('portfolioUpdated', onUpdate);
    return () => window.removeEventListener('portfolioUpdated', onUpdate);
  }, []);

  const allocBars: AllocBar[] = portfolio && portfolio.holdings.length > 0
    ? portfolio.holdings
        .sort((a, b) => b.allocation_pct - a.allocation_pct)
        .slice(0, 8)
        .map((h, i) => ({
          name: h.ticker,
          pct: parseFloat(h.allocation_pct.toFixed(1)),
          dollarValue: `$${Math.round(h.current_value).toLocaleString()}`,
          fill: PIE_COLORS[i % PIE_COLORS.length],
        }))
    : [];

  const portfolioEmpty = portfolioLoaded && allocBars.length === 0;

  return (
    <div className="page-common">
      <motion.h1
        className="page-title"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        Market Analysis
      </motion.h1>

      <section className="chart-section">
        <h2 className="section-subtitle">Market Trends</h2>
        {loading ? (
          <div className="chart-skeleton" style={{ height: 280 }} />
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="marketGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#14b8a6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} domain={[0, 'auto']} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #1e2a3a', borderRadius: 8 }}
                formatter={(v: number | undefined) => [(v ?? 0).toFixed(0), 'S&P 500']}
              />
              <Area type="monotone" dataKey="value" stroke="#14b8a6" strokeWidth={2} fill="url(#marketGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </section>

      <section className="chart-section">
        <h2 className="section-subtitle">
          Portfolio Allocation
          {portfolio && (
            <span style={{ fontSize: 12, fontWeight: 400, color: '#9ca3af', marginLeft: 10 }}>
              ${portfolio.summary.total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              &nbsp;·&nbsp;
              <span style={{ color: portfolio.summary.total_pnl >= 0 ? '#10b981' : '#ef4444' }}>
                {portfolio.summary.total_pnl >= 0 ? '+' : ''}{portfolio.summary.total_pnl_pct.toFixed(2)}%
              </span>
            </span>
          )}
        </h2>
        {portfolioEmpty ? (
          <p style={{ color: '#6b7280', fontSize: 13, padding: '20px 0' }}>
            No holdings yet — start trading to see your allocation.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(180, allocBars.length * 44)}>
            <BarChart data={allocBars} layout="vertical" margin={{ top: 4, right: 90, left: 60, bottom: 4 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: '#e5e7eb' }} width={56} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #1e2a3a', borderRadius: 8 }}
                formatter={(v: number | undefined) => [`${(v ?? 0).toFixed(1)}%`, 'Allocation']}
              />
              <Bar dataKey="pct" radius={[0, 4, 4, 0]}>
                {allocBars.map((entry, i) => (
                  <Cell key={entry.name} fill={entry.fill ?? PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
                <LabelList dataKey="dollarValue" position="right" style={{ fontSize: 11, fill: '#e5e7eb', fontWeight: 500 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </section>

      <LiveNewsSection />
    </div>
  );
}

// ── Live News from yfinance ───────────────────────────────────────────────────
interface NewsArticle { title: string; publisher: string; link: string; published_at: string; ticker: string; }

function timeAgo(iso: string): string {
  if (!iso) return '';
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function LiveNewsSection() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`${BASE_URL}/market/news?limit=10`)
      .then((r) => r.ok ? r.json() : { articles: [] })
      .then((d) => { if (!cancelled) { setArticles(d.articles ?? []); setNewsLoading(false); } })
      .catch(() => { if (!cancelled) setNewsLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="news-section">
      <h2 className="section-title">Market News</h2>
      {newsLoading && <p style={{ color: '#6b7280', fontSize: 13 }}>Loading…</p>}
      <div className="news-list">
        {articles.map((item, i) => (
          <motion.a
            key={i}
            href={item.link || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="news-card"
            style={{ textDecoration: 'none', display: 'block', cursor: 'pointer' }}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <div className="news-img-placeholder" style={{ background: PIE_COLORS[i % PIE_COLORS.length] + '33', display: 'flex', alignItems: 'center', justifyContent: 'center', color: PIE_COLORS[i % PIE_COLORS.length], fontWeight: 700, fontSize: 13 }}>{item.ticker}</div>
            <div className="news-body">
              <span className="news-tag">{item.publisher}</span>
              <h3 className="news-headline">{item.title}</h3>
              <p className="news-snippet" style={{ color: '#6b7280', fontSize: 11 }}>{timeAgo(item.published_at)}</p>
            </div>
          </motion.a>
        ))}
      </div>
    </section>
  );
}
