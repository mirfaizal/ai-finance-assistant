import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList } from 'recharts';
import { Download, Clock } from 'lucide-react';
import { usePortfolioSummary } from '../lib/hooks/usePortfolioSummary';

const PIE_COLORS = ['#14b8a6', '#8b5cf6', '#3b82f6', '#f59e0b', '#10b981', '#ec4899', '#f97316', '#6b7280'];

interface HoldingRow { ticker: string; pct: number; value: number; }
interface AllocBar { name: string; pct: number; dollarValue: string; fill: string; }
interface Summary { total_value: number; total_pnl: number; total_pnl_pct: number; concentration_risk: string; }

type ApiData = {
  holdings?: { ticker: string; allocation_pct: number; current_value?: number }[];
  summary?: { total_value?: number; total_pnl?: number; total_pnl_pct?: number; concentration_risk?: string };
} | null;

function applyData(
  data: ApiData,
  setSummary: (s: Summary | null) => void,
  setTopHoldings: (h: HoldingRow[]) => void,
  setAllocBars: (b: AllocBar[]) => void,
) {
  const holdings = data?.holdings ?? [];
  const summarySafe = data?.summary ?? null;
  setSummary(summarySafe as Summary | null);
  setTopHoldings(
    holdings.map((h) => ({ ticker: h.ticker, pct: Math.round(h.allocation_pct), value: Math.round(h.current_value ?? 0) }))
  );
  setAllocBars(
    [...holdings]
      .sort((a, b) => b.allocation_pct - a.allocation_pct)
        .map((h, i) => ({
        name: h.ticker,
        pct: parseFloat(h.allocation_pct.toFixed(1)),
        dollarValue: `$${Math.round(h.current_value ?? 0).toLocaleString()}`,
        fill: PIE_COLORS[i % PIE_COLORS.length],
      }))
  );
}

export function PortfolioPage() {
  const [topHoldings, setTopHoldings] = useState<HoldingRow[]>([]);
  const [allocBars, setAllocBars] = useState<AllocBar[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loaded, setLoaded] = useState(false);

  // Compute concentration/diversification risk for display. Prefer backend `summary.concentration_risk` when available.
  const getRiskInfo = (summaryObj: Summary | null, bars: AllocBar[]) => {
    const backendRisk = summaryObj?.concentration_risk;
    if (backendRisk) {
      const level = String(backendRisk).toLowerCase();
      const color = level === 'high' ? '#f59e0b' : level === 'medium' ? '#f97316' : '#10b981';
      return { level, color, reason: `Backend assessment: ${level}` };
    }
    const largest = bars.length ? Math.max(...bars.map((b) => b.pct)) : 0;
    let level: 'low' | 'medium' | 'high' = 'low';
    if (largest >= 50) level = 'high';
    else if (largest >= 30) level = 'medium';
    const color = level === 'high' ? '#f59e0b' : level === 'medium' ? '#f97316' : '#10b981';
    const reason = largest > 0 ? `Largest position is ${largest.toFixed(1)}% of the portfolio.` : 'No positions to evaluate.';
    return { level, color, reason };
  };

  const { data, loaded: psLoaded } = usePortfolioSummary();
  useEffect(() => {
    // whenever shared summary updates, apply it locally
    applyData(data, setSummary, setTopHoldings, setAllocBars);
    setLoaded(psLoaded);
  }, [data, psLoaded]);

  const handleExport = () => {
    if (typeof window.print === 'function') window.print();
    else alert('Export: use browser Print to save as PDF.');
  };

  const isEmpty = loaded && allocBars.length === 0;

  const riskInfo = getRiskInfo(summary, allocBars);

  return (
    <div className="page-common">
      <div className="portfolio-page-header">
        <motion.h1
          className="page-title"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          Portfolio Analysis
        </motion.h1>
        <button type="button" className="export-report-btn" onClick={handleExport}>
          <Download size={16} />
          Export Report
        </button>
      </div>

      <section className="allocation-section">
        <div className="allocation-card">
          <div className="allocation-card-header">
            <Clock size={18} />
            <h2 className="section-title">Allocation Breakdown</h2>
          </div>
          <h3 className="section-subtitle">
            {summary ? (
              <>
                Total Balance:&nbsp;
                <span style={{ color: '#14b8a6', fontWeight: 700 }}>
                  ${summary.total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                &nbsp;·&nbsp;
                <span style={{ color: summary.total_pnl >= 0 ? '#10b981' : '#ef4444' }}>
                  {summary.total_pnl >= 0 ? '+' : ''}{summary.total_pnl_pct.toFixed(2)}% P&amp;L
                </span>
                &nbsp;·&nbsp;
                <span
                  title={riskInfo.reason}
                  style={{
                    background: riskInfo.color,
                    color: '#071025',
                    padding: '4px 8px',
                    borderRadius: 12,
                    fontWeight: 700,
                    fontSize: 12,
                    verticalAlign: 'middle'
                  }}
                >
                  {`Risk: ${String(riskInfo.level).charAt(0).toUpperCase() + String(riskInfo.level).slice(1)}`}
                </span>
              </>
            ) : loaded ? 'No holdings yet' : 'Loading…'}
          </h3>
          {isEmpty ? (
            <p style={{ color: '#6b7280', fontSize: 13, padding: '24px 0', textAlign: 'center' }}>
              No holdings found. Ask the assistant to buy a stock to get started!
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(200, allocBars.length * 44)}>
              <BarChart data={allocBars} layout="vertical" margin={{ top: 4, right: 90, left: 64, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
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
        </div>
      </section>

      <section className="holdings-section">
        <h2 className="section-title">Top Holdings</h2>
        {isEmpty && (
          <p style={{ color: '#6b7280', fontSize: 13 }}>No holdings yet.</p>
        )}
        <ul className="holdings-list">
          {topHoldings.map((h, i) => (
            <motion.li
              key={h.ticker}
              className="holding-row"
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <span className="holding-ticker">{h.ticker}</span>
              <span className="holding-pct">{h.pct}%</span>
              <span className="holding-value">${typeof h.value === 'number' ? h.value.toLocaleString() : h.value}</span>
            </motion.li>
          ))}
        </ul>
      </section>
    </div>
  );
}
