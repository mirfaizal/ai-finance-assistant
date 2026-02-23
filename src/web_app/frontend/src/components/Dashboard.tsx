import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { MessageSquare, BookOpen, ArrowRight } from 'lucide-react';
import { QUICK_ACTIONS, EDUCATIONAL_CARDS } from '../lib/mockData';

import { BASE_URL } from '../lib/config';
const CACHE_TTL = 5 * 60 * 1000;

interface Insight {
    id: number;
    icon: string;
    title: string;
    desc: string;
    badge: string;
    badgeColor: string;
}

// Fallback shown while loading or if backend is offline
const FALLBACK_INSIGHTS: Insight[] = [
    { id: 1, icon: '📈', title: 'S&P 500', desc: 'Loading live data…', badge: 'Markets', badgeColor: '#8b5cf6' },
    { id: 2, icon: '📊', title: 'Nasdaq 100', desc: 'Loading live data…', badge: 'Markets', badgeColor: '#14b8a6' },
    { id: 3, icon: '⚡', title: 'Volatility (VIX)', desc: 'The VIX fear index measures market risk.', badge: 'Risk', badgeColor: '#f59e0b' },
];

function buildInsights(overview: Record<string, { price: number | null; change_pct: number | null }>): Insight[] {
    const fmt = (v: number | null) => v != null ? `${v >= 0 ? '+' : ''}${v.toFixed(2)}%` : '—';
    const fmtPx = (v: number | null) => v != null ? `$${v.toFixed(2)}` : '—';
    const color = (v: number | null) => v != null && v >= 0 ? '#10b981' : '#ef4444';

    const spy = overview['SPY'];
    const qqq = overview['QQQ'];
    const vix = overview['^VIX'];

    return [
        {
            id: 1,
            icon: spy?.change_pct != null && spy.change_pct >= 0 ? '📈' : '📉',
            title: `S&P 500  ${fmtPx(spy?.price ?? null)}`,
            desc: `Day change: ${fmt(spy?.change_pct ?? null)}`,
            badge: 'Markets',
            badgeColor: color(spy?.change_pct ?? null),
        },
        {
            id: 2,
            icon: qqq?.change_pct != null && qqq.change_pct >= 0 ? '🚀' : '📉',
            title: `Nasdaq 100  ${fmtPx(qqq?.price ?? null)}`,
            desc: `Day change: ${fmt(qqq?.change_pct ?? null)}`,
            badge: 'Tech',
            badgeColor: '#14b8a6',
        },
        {
            id: 3,
            icon: '⚡',
            title: `VIX  ${vix?.price != null ? vix.price.toFixed(2) : '—'}`,
            desc: vix?.price != null
                ? vix.price < 20 ? 'Low volatility — markets are calm.'
                    : vix.price < 30 ? 'Moderate volatility — some uncertainty.'
                        : 'High volatility — elevated market fear.'
                : 'Fear index data loading…',
            badge: 'Risk',
            badgeColor: vix?.price != null && vix.price > 25 ? '#f59e0b' : '#6b7280',
        },
    ];
}

interface DashboardProps {
    onStartChat: (prefill?: string) => void;
}

export function Dashboard({ onStartChat }: DashboardProps) {
    const [insights, setInsights] = useState<Insight[]>(FALLBACK_INSIGHTS);
    const cachedAt = useRef<number>(0);

    useEffect(() => {
        let cancelled = false;
        async function load() {
            if (Date.now() - cachedAt.current < CACHE_TTL) return;
            try {
                const res = await fetch(`${BASE_URL}/market/overview`);
                if (!res.ok) return;
                const json = await res.json();
                if (!cancelled) {
                    cachedAt.current = Date.now();
                    setInsights(buildInsights(json));
                }
            } catch { /* keep fallback */ }
        }
        load();
        return () => { cancelled = true; };
    }, []);

    return (
        <div className="dashboard">
            {/* Hero */}
            <motion.div
                className="dashboard-hero"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <div className="hero-glow" />
                <h1>Good morning 👋</h1>
                <p>Your AI-powered financial intelligence, always on.</p>
                <button className="hero-cta" onClick={() => onStartChat()}>
                    <MessageSquare size={18} />
                    Ask Finnie something
                </button>
            </motion.div>

            {/* Live Insights */}
            <section className="section">
                <h2 className="section-title">Today's Insights</h2>
                <div className="insights-grid">
                    {insights.map((ins, i) => (
                        <motion.div
                            key={ins.id}
                            className="insight-card"
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                        >
                            <div className="insight-icon">{ins.icon}</div>
                            <div>
                                <div className="insight-title">{ins.title}</div>
                                <div className="insight-desc">{ins.desc}</div>
                            </div>
                            <span
                                className="insight-badge"
                                style={{ background: `${ins.badgeColor}22`, color: ins.badgeColor }}
                            >
                                {ins.badge}
                            </span>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* Quick Actions */}
            <section className="section">
                <h2 className="section-title">Quick Actions</h2>
                <div className="actions-row">
                    {QUICK_ACTIONS.map((a) => (
                        <button
                            key={a.id}
                            className="action-btn"
                            onClick={() => onStartChat(a.label)}
                        >
                            <span className="action-icon">{a.icon}</span>
                            <span>{a.label}</span>
                        </button>
                    ))}
                </div>
            </section>

            {/* Educational */}
            <section className="section">
                <h2 className="section-title">Learn &amp; Grow</h2>
                <div className="edu-list">
                    {EDUCATIONAL_CARDS.map((card, i) => (
                        <motion.button
                            key={i}
                            className="edu-card"
                            initial={{ opacity: 0, x: -16 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.1 }}
                            onClick={() => onStartChat(card.title)}
                        >
                            <BookOpen size={16} className="edu-icon" />
                            <div className="edu-content">
                                <div className="edu-title">{card.title}</div>
                                <div className="edu-meta">
                                    <span>{card.category}</span>
                                    <span>·</span>
                                    <span>{card.readTime} read</span>
                                </div>
                            </div>
                            <ArrowRight size={14} className="edu-arrow" />
                        </motion.button>
                    ))}
                </div>
            </section>
        </div>
    );
}

