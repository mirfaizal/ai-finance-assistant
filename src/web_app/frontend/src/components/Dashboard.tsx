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
}

interface LiveMetrics {
  totalBalance: number;
  totalPnl: number;
  totalPnlPct: number;
}

export function Dashboard({ onStartChat }: DashboardProps) {
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
  const displayBalance  = portfolioLoaded ? (live?.totalBalance  ?? 0) : m.totalBalance;
  const displayPnl      = portfolioLoaded ? (live?.totalPnl      ?? 0) : m.balanceChange;
  const displayPnlPct   = portfolioLoaded ? (live?.totalPnlPct   ?? 0) : m.balanceChangePct;
  const pnlPositive     = displayPnl >= 0;

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
        <motion.div className="metric-card icon-card" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22 }}>
          <PieChart size={20} />
          <span>Balanced Allocation</span>
        </motion.div>
      </section>

      {/* Recent Insights (alerts) */}
      <section className="section">
        <h2 className="section-title">Recent Insights</h2>
        <div className="insights-grid">
          {RECENT_INSIGHTS_ALERTS.map((alert, i) => (
            <motion.div
              key={alert.id}
              className="insight-card alert"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.24 + i * 0.06 }}
            >
              <span className="insight-dot" style={{ background: alert.dotColor }} />
              <div className="insight-content">
                <div className="insight-title">{alert.title}</div>
                <div className="insight-desc">{alert.desc}</div>
                <span className="insight-time">{alert.timeAgo}</span>
              </div>
            </motion.div>
          ))}
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
