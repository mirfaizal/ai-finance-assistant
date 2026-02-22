import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronRight, Target, TrendingUp, Shield } from 'lucide-react';
import type { UserProfile } from '../lib/types';

interface RiskModalProps {
    onComplete: (profile: Partial<UserProfile>) => void;
}

const RISK_OPTIONS = [
    {
        id: 'conservative',
        icon: Shield,
        label: 'Conservative',
        desc: 'Preserve capital, minimal risk',
        color: '#3b82f6',
    },
    {
        id: 'moderate',
        icon: Target,
        label: 'Moderate',
        desc: 'Balanced growth and safety',
        color: '#14b8a6',
    },
    {
        id: 'aggressive',
        icon: TrendingUp,
        label: 'Aggressive',
        desc: 'Maximum growth, higher risk',
        color: '#8b5cf6',
    },
] as const;

const GOAL_OPTIONS = [
    'Build an emergency fund',
    'Save for retirement',
    'Buy a home',
    'Pay off debt',
    'Grow investments',
    'Plan for college',
];

export function RiskModal({ onComplete }: RiskModalProps) {
    const [step, setStep] = useState(0);
    const [risk, setRisk] = useState<'conservative' | 'moderate' | 'aggressive' | null>(null);
    const [goals, setGoals] = useState<string[]>([]);

    const toggleGoal = (g: string) => {
        setGoals((prev) => prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]);
    };

    const handleFinish = () => {
        onComplete({ riskTolerance: risk, investmentGoals: goals, completedOnboarding: true, isNewUser: false });
    };

    return (
        <AnimatePresence>
            <motion.div
                className="modal-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
            >
                <motion.div
                    className="modal-card"
                    initial={{ scale: 0.9, y: 30, opacity: 0 }}
                    animate={{ scale: 1, y: 0, opacity: 1 }}
                    exit={{ scale: 0.9, y: 30, opacity: 0 }}
                    transition={{ type: 'spring', damping: 20 }}
                >
                    {/* Header */}
                    <div className="modal-header">
                        <div>
                            <h2>Welcome to Finnie AI</h2>
                            <p>Let's personalise your experience — takes 30 seconds.</p>
                        </div>
                        <button className="modal-close" onClick={() => onComplete({ isNewUser: false, completedOnboarding: false })}>
                            <X size={18} />
                        </button>
                    </div>

                    {/* Progress */}
                    <div className="modal-progress">
                        {[0, 1].map((i) => (
                            <div key={i} className={`progress-dot ${step >= i ? 'active' : ''}`} />
                        ))}
                    </div>

                    <AnimatePresence mode="wait">
                        {step === 0 && (
                            <motion.div
                                key="step0"
                                initial={{ opacity: 0, x: 30 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -30 }}
                                className="modal-step"
                            >
                                <h3>What's your risk tolerance?</h3>
                                <div className="risk-options">
                                    {RISK_OPTIONS.map(({ id, icon: Icon, label, desc, color }) => (
                                        <button
                                            key={id}
                                            className={`risk-option ${risk === id ? 'selected' : ''}`}
                                            style={{ '--opt-color': color } as React.CSSProperties}
                                            onClick={() => setRisk(id)}
                                        >
                                            <Icon size={22} style={{ color }} />
                                            <div>
                                                <div className="opt-label">{label}</div>
                                                <div className="opt-desc">{desc}</div>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                                <button
                                    className="modal-next"
                                    disabled={!risk}
                                    onClick={() => setStep(1)}
                                >
                                    Next <ChevronRight size={16} />
                                </button>
                            </motion.div>
                        )}

                        {step === 1 && (
                            <motion.div
                                key="step1"
                                initial={{ opacity: 0, x: 30 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -30 }}
                                className="modal-step"
                            >
                                <h3>What are your financial goals?</h3>
                                <p className="step-sub">Select all that apply.</p>
                                <div className="goal-grid">
                                    {GOAL_OPTIONS.map((g) => (
                                        <button
                                            key={g}
                                            className={`goal-chip ${goals.includes(g) ? 'selected' : ''}`}
                                            onClick={() => toggleGoal(g)}
                                        >
                                            {g}
                                        </button>
                                    ))}
                                </div>
                                <button className="modal-next" onClick={handleFinish}>
                                    Get Started 🚀
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
