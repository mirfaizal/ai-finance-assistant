import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { MessageSquare, BookOpen, ArrowRight, TrendingUp, PieChart } from 'lucide-react';
import {
  DASHBOARD_METRICS,
  RECENT_INSIGHTS_ALERTS,
  DASHBOARD_QUICK_ACTIONS,
  RECOMMENDED_LEARNING,
} from '../lib/mockData';
import { usePortfolioSummary } from '../lib/hooks/usePortfolioSummary';

interface DashboardProps {
  onStartChat: (prefill?: string) => void;
  onNavigate?: (tab: string) => void;
}

interface LiveMetrics {
  totalBalance: number;
  totalPnl: number;
  totalPnlPct: number;
}

export function Dashboard({ onStartChat, onNavigate }: DashboardProps) {
  const m = DASHBOARD_METRICS;
  const [live, setLive] = useState<LiveMetrics | null>(null);
  const [portfolioLoaded, setPortfolioLoaded] = useState(false);

  const applyPortfolioData = (data: { summary?: { total_value?: number; total_pnl?: number; total_pnl_pct?: number } } | null) => {
    setPortfolioLoaded(true);
    const s = data?.summary;
    if (s?.total_value != null) {
      setLive({ totalBalance: s.total_value, totalPnl: s.total_pnl ?? 0, totalPnlPct: s.total_pnl_pct ?? 0 });
    } else {
      setLive({ totalBalance: 0, totalPnl: 0, totalPnlPct: 0 });
    }
  };

  const { data, loaded } = usePortfolioSummary();
  useEffect(() => {
    applyPortfolioData(data);
    // reflect that we've loaded portfolio data (even if empty)
    setPortfolioLoaded(loaded);
  }, [data, loaded]);

  // Before API responds show mock; once loaded always show live (even if $0)
  const displayBalance = portfolioLoaded ? (live?.totalBalance ?? 0) : m.totalBalance;
  const displayPnl = portfolioLoaded ? (live?.totalPnl ?? 0) : m.balanceChange;
  const displayPnlPct = portfolioLoaded ? (live?.totalPnlPct ?? 0) : m.balanceChangePct;
  const pnlPositive = displayPnl >= 0;

  return (
    <div className="dashboard">
      {/* Welcome hero */}
      <motion.div
        className="dashboard-hero"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="hero-glow" />
        <div className="dashboard-hero-top">
          <div>
            <h1>Welcome back, User</h1>
            <p>Here&apos;s your financial snapshot for today.</p>
          </div>
          <button className="hero-cta" onClick={() => onStartChat()}>
            <MessageSquare size={18} />
            Ask Assistant
          </button>
        </div>
      </motion.div>

      {/* Metric cards */}
      <section className="metrics-row">
        <motion.div
          className="metric-card primary"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <span className="metric-label">Total Balance</span>
          <span className="metric-value">
            ${displayBalance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </span>
          {portfolioLoaded && displayBalance === 0 ? (
            <span className="metric-change" style={{ color: '#6b7280', fontSize: 11 }}>
              No holdings yet — start trading!
            </span>
          ) : (
            <span className={`metric-change ${pnlPositive ? 'positive' : 'negative'}`}>
              {pnlPositive ? '+' : ''}${Math.abs(displayPnl).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })} ({pnlPositive ? '+' : ''}{displayPnlPct.toFixed(2)}%)
            </span>
          )}
        </motion.div>
        <motion.div className="metric-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }}>
          <span className="metric-label">YTD Return</span>
          <span className="metric-value accent">+{m.ytdReturn}%</span>
        </motion.div>
        <motion.div className="metric-card icon-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.14 }}>
          <TrendingUp size={20} />
          <span>Outperforming S&P 500</span>
        </motion.div>
        <motion.div className="metric-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}>
          <span className="metric-label">Est. Savings</span>
          <span className="metric-value">${m.estSavings.toLocaleString()}</span>
        </motion.div>
        <motion.div className="metric-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}>
          <span className="metric-label">Tax Efficiency</span>
          <span className="metric-value">{m.taxEfficiency}</span>
        </motion.div>
        <motion.div className="metric-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <span className="metric-label">Risk Level</span>
          <span className="metric-value">{m.riskLevel}</span>
        </motion.div>
        <motion.div
          className="metric-card icon-card allocation-card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.22 }}
          style={{ cursor: 'pointer', minWidth: 160 }}
          onClick={() => onNavigate ? onNavigate('portfolio') : onStartChat('Show my portfolio allocation')}
          title="View portfolio allocation"
        >
          <PieChart size={18} style={{ flexShrink: 0 }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: 4 }}>
              Allocation
            </span>
            {(() => {
              const holdings = data?.holdings;
              if (!portfolioLoaded) {
                return <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Loading…</span>;
              }
              if (!holdings || holdings.length === 0) {
                return <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>No holdings yet</span>;
              }
              const COLORS = ['#58a6ff', '#3fb950', '#bc8cff', '#f0883e', '#ff6eb3', '#39d0d8', '#e3b341'];
              const top = [...holdings].sort((a, b) => b.allocation_pct - a.allocation_pct).slice(0, 4);
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {top.map((h, i) => (
                    <div key={h.ticker} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', width: 34, flexShrink: 0 }}>{h.ticker}</span>
                      <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(h.allocation_pct, 100)}%`, height: '100%', background: COLORS[i % COLORS.length], borderRadius: 2 }} />
                      </div>
                      <span style={{ fontSize: '0.68rem', color: COLORS[i % COLORS.length], width: 30, textAlign: 'right', flexShrink: 0 }}>
                        {h.allocation_pct.toFixed(0)}%
                      </span>
                    </div>
                  ))}
                  {holdings.length > 4 && (
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 1 }}>+{holdings.length - 4} more</span>
                  )}
                </div>
              );
            })()}
          </div>
        </motion.div>
      </section>

      {/* Recent Insights (alerts) */}
      <section className="section">
        <h2 className="section-title">Recent Insights</h2>
        <div className="insights-grid">
          {(() => {
            // Synthesize live insights from portfolio data when available
            const holdings = data?.holdings ?? [];
            const summary = data?.summary;

            // Build dynamic insight list, replacing relevant mock items
            const live = RECENT_INSIGHTS_ALERTS.map((alert) => {
              if (alert.type === 'rebalance' && holdings.length > 0) {
                // Find the most concentrated holding
                const top = [...holdings].sort((a, b) => b.allocation_pct - a.allocation_pct)[0];
                const risk = summary?.concentration_risk ?? 'low';
                if (top && top.allocation_pct > 40) {
                  return {
                    ...alert,
                    title: 'Concentration Risk Detected',
                    desc: `${top.ticker} makes up ${top.allocation_pct.toFixed(0)}% of your portfolio — consider rebalancing.`,
                    dotColor: risk === 'high' ? '#ef4444' : '#f59e0b',
                    chatPrompt: `My portfolio has ${top.ticker} at ${top.allocation_pct.toFixed(0)}% allocation. Should I rebalance? What would a more balanced allocation look like?`,
                    actionLabel: `Ask about ${top.ticker} concentration →`,
                  };
                }
              }
              if (alert.type === 'dividend' && holdings.length > 0) {
                const tickers = holdings.map((h) => h.ticker).slice(0, 4).join(', ');
                return {
                  ...alert,
                  title: 'Dividend & Income Tracking',
                  desc: `Check dividend yields for your holdings: ${tickers}.`,
                  chatPrompt: `What are the dividend yields for ${tickers}? Which of my holdings pay the best dividends?`,
                  actionLabel: `Check dividend yields →`,
                };
              }
              return alert;
            });

            return live.map((alert, i) => (
              <motion.button
                key={alert.id}
                className="insight-card alert"
                style={{ cursor: 'pointer', textAlign: 'left', background: 'none', border: 'none', width: '100%', padding: 0 }}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.24 + i * 0.06 }}
                onClick={() => onStartChat(alert.chatPrompt)}
                title={alert.actionLabel}
              >
                <span className="insight-dot" style={{ background: alert.dotColor }} />
                <div className="insight-content">
                  <div className="insight-title">{alert.title}</div>
                  <div className="insight-desc">{alert.desc}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
                    <span className="insight-time">{alert.timeAgo}</span>
                    <span style={{ fontSize: '0.7rem', color: alert.dotColor, opacity: 0.85 }}>{alert.actionLabel}</span>
                  </div>
                </div>
              </motion.button>
            ));
          })()}
        </div>
      </section>

      {/* Quick Actions */}
      <section className="section">
        <h2 className="section-title">Quick Actions</h2>
        <div className="actions-row">
          {DASHBOARD_QUICK_ACTIONS.map((a, i) => (
            <motion.button
              key={a.id}
              className="action-btn"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.05 }}
              onClick={() => onStartChat(a.label)}
            >
              <span className="action-icon">{a.icon}</span>
              <span>{a.label}</span>
            </motion.button>
          ))}
        </div>
      </section>

      {/* Recommended Learning */}
      <section className="section">
        <h2 className="section-title">Recommended Learning</h2>
        <div className="edu-list">
          {RECOMMENDED_LEARNING.map((item, i) => (
            <motion.button
              key={i}
              className="edu-card"
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + i * 0.08 }}
              onClick={() => onStartChat(item.title)}
            >
              <BookOpen size={16} className="edu-icon" />
              <div className="edu-content">
                <span className="edu-category">{item.category}</span>
                <div className="edu-title">{item.title}</div>
                <p className="edu-desc">{item.desc}</p>
                <div className="edu-meta">
                  {'progress' in item && item.progress != null
                    ? `${item.progress}% Complete`
                    : 'readTime' in item
                      ? item.readTime
                      : ''}
                </div>
                {'progress' in item && (
                  <div className="edu-progress-bar">
                    <div className="edu-progress-fill" style={{ width: `${(item as { progress?: number }).progress ?? 0}%` }} />
                  </div>
                )}
              </div>
              <ArrowRight size={14} className="edu-arrow" />
            </motion.button>
          ))}
        </div>
      </section>
    </div>
  );
}
