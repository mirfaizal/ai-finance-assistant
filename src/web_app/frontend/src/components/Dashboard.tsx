import { motion } from 'framer-motion';
import { MessageSquare, BookOpen, ArrowRight } from 'lucide-react';
import { QUICK_INSIGHTS, QUICK_ACTIONS, EDUCATIONAL_CARDS } from '../lib/mockData';

interface DashboardProps {
    onStartChat: (prefill?: string) => void;
}

export function Dashboard({ onStartChat }: DashboardProps) {
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

            {/* Insights */}
            <section className="section">
                <h2 className="section-title">Today's Insights</h2>
                <div className="insights-grid">
                    {QUICK_INSIGHTS.map((ins, i) => (
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
                <h2 className="section-title">Learn & Grow</h2>
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
