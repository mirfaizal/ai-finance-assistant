import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Loader2, AlertCircle, Wifi, WifiOff } from 'lucide-react';

const AGENT_SUGGESTIONS = [
    {
        icon: '💡',
        label: 'Finance Q&A',
        color: '#14b8a6',
        examples: ['What is compound interest?', 'How do ETFs differ from mutual funds?'],
    },
    {
        icon: '📈',
        label: 'Market Analyst',
        color: '#8b5cf6',
        examples: ['How do rising interest rates affect stocks?', "What's driving the S&P 500 today?"],
    },
    {
        icon: '🧾',
        label: 'Tax Educator',
        color: '#f59e0b',
        examples: ['What is the difference between Roth and Traditional IRA?', 'How does capital gains tax work?'],
    },
    {
        icon: '📊',
        label: 'Portfolio Analyst',
        color: '#3b82f6',
        examples: ['How should I diversify my portfolio?', 'What is a good asset allocation for my age?'],
    },
    {
        icon: '🎯',
        label: 'Goal Planner',
        color: '#10b981',
        examples: ['How do I plan for retirement in my 30s?', 'How much should I save for an emergency fund?'],
    },
    {
        icon: '📰',
        label: 'News Synthesizer',
        color: '#ec4899',
        examples: ['What are the latest financial news headlines?', 'Summarize recent Fed announcements'],
    },
    {
        icon: '🔬',
        label: 'Stock Analyst',
        color: '#f97316',
        examples: ['What is AAPL trading at right now?', 'Compare NVDA vs AMD fundamentals', 'Is TSLA overvalued?'],
    },
];
import { MessageBubble } from './MessageBubble';
import { AgentBadge } from './AgentBadge';
import { detectAgent, getAgent, backendAgentToType } from '../lib/agentEngine';
import { askQuestion, getPortfolioHoldings } from '../lib/api';
import { BASE_URL } from '../lib/config';
import { appendMessage, getSession, getBackendSessionId, setBackendSessionId } from '../lib/storage';
import { saveHoldings } from '../lib/holdingsStore';
import type { Message, AgentType } from '../lib/types';

interface ChatInterfaceProps {
    sessionId: string;
    prefillMessage?: string;
    onPrefillConsumed?: () => void;
}

export function ChatInterface({ sessionId, prefillMessage, onPrefillConsumed }: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>(() => {
        return getSession(sessionId)?.messages ?? [];
    });
    const [input, setInput] = useState('');
    const [activeAgent, setActiveAgent] = useState<AgentType>('advisor');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Reset messages when session changes
    useEffect(() => {
        setMessages(getSession(sessionId)?.messages ?? []);
        setError(null);
    }, [sessionId]);

    // Prefill message from dashboard quick actions
    useEffect(() => {
        if (prefillMessage) {
            setInput(prefillMessage);
            onPrefillConsumed?.();
            inputRef.current?.focus();
        }
    }, [prefillMessage, onPrefillConsumed]);

    // Auto-scroll
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    // Check backend health on mount
    useEffect(() => {
        fetch(`${BASE_URL}/health`)
            .then((r) => setBackendOnline(r.ok))
            .catch(() => setBackendOnline(false));
    }, []);

    const handleSend = useCallback(async () => {
        const text = input.trim();
        if (!text || loading) return;

        const detectedAgent = detectAgent(text);
        setActiveAgent(detectedAgent);
        setInput('');
        setError(null);

        const userMsg: Message = {
            id: crypto.randomUUID(),
            role: 'user',
            content: text,
            timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, userMsg]);
        appendMessage(sessionId, userMsg);

        setLoading(true);
        try {
            // Pass the backend session UUID so the server can recall prior turns
            const backendSid = getBackendSessionId(sessionId);
            const res = await askQuestion(text, backendSid);
            // Persist the backend UUID for subsequent messages in this session
            setBackendSessionId(sessionId, res.session_id);
            // Use the backend's actual agent, not the client-side guess
            const confirmedAgent = backendAgentToType(res.agent);
            setActiveAgent(confirmedAgent);

            // If the trading agent executed a trade, sync SQLite holdings → localStorage
            // so PortfolioChart updates automatically without a page refresh.
            if (res.agent === 'trading_agent') {
                try {
                    const ph = await getPortfolioHoldings(res.session_id);
                    if (ph.holdings.length > 0) {
                        saveHoldings(
                            ph.holdings.map((h) => ({
                                ticker: h.ticker,
                                shares: h.shares,
                                avg_cost: h.avg_cost,
                            })),
                        );
                    }
                } catch {
                    // Non-fatal: chart will just not update this turn
                }
            }

            const aiMsg: Message = {
                id: crypto.randomUUID(),
                role: 'assistant',
                content: res.answer,
                agent: confirmedAgent,
                timestamp: Date.now(),
            };
            setMessages((prev) => [...prev, aiMsg]);
            appendMessage(sessionId, aiMsg);
            setBackendOnline(true);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Unknown error';
            setError(msg);
            setBackendOnline(false);
        } finally {
            setLoading(false);
        }
    }, [input, loading, sessionId]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const agent = getAgent(activeAgent);

    return (
        <div className="chat-container">
            {/* Header */}
            <div className="chat-header">
                <div className="chat-header-left">
                    <h2>Research</h2>
                    <div className={`backend-status ${backendOnline === false ? 'offline' : 'online'}`}>
                        {backendOnline === false ? <WifiOff size={12} /> : <Wifi size={12} />}
                        {backendOnline === false ? 'Backend offline' : 'Connected'}
                    </div>
                </div>
                <AgentBadge agent={agent} pulse={loading} />
            </div>

            {/* Messages */}
            <div className="chat-messages">
                {messages.length === 0 && (
                    <motion.div
                        className="chat-empty"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                    >
                        <div className="empty-icon">💬</div>
                        <h3>Ask Finnie anything</h3>
                        <div className="agent-hints">
                            <span style={{ color: '#14b8a6' }}>💡 Finance Q&A</span>
                            <span style={{ color: '#8b5cf6' }}>📈 Market Analyst</span>
                            <span style={{ color: '#f59e0b' }}>🧾 Tax Educator</span>
                            <span style={{ color: '#3b82f6' }}>📊 Portfolio Analyst</span>
                            <span style={{ color: '#10b981' }}>🎯 Goal Planner</span>
                            <span style={{ color: '#ec4899' }}>📰 News Synthesizer</span>
                            <span style={{ color: '#f97316' }}>🔬 Stock Analyst</span>
                        </div>
                        <p className="empty-hint">The right agent is automatically selected based on your question.</p>
                    </motion.div>
                )}

                {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} />
                ))}

                {loading && (
                    <motion.div
                        className="message-row ai-row"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                    >
                        <div className="msg-avatar" style={{ background: agent.color }}>
                            <Loader2 size={14} className="spin" />
                        </div>
                        <div className="msg-bubble ai-bubble typing-bubble">
                            <span className="typing-dot" />
                            <span className="typing-dot" />
                            <span className="typing-dot" />
                        </div>
                    </motion.div>
                )}

                <AnimatePresence>
                    {error && (
                        <motion.div
                            className="chat-error"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                        >
                            <AlertCircle size={15} />
                            {error}
                        </motion.div>
                    )}
                </AnimatePresence>

                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="chat-input-bar">
                <AnimatePresence>
                    {showSuggestions && (
                        <motion.div
                            className="suggestions-panel"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 10 }}
                            transition={{ duration: 0.18 }}
                        >
                            <p className="suggestions-title">What can I help you with?</p>
                            <div className="suggestions-grid">
                                {AGENT_SUGGESTIONS.map((agent) => (
                                    <div key={agent.label} className="suggestion-agent-card">
                                        <div className="suggestion-agent-header" style={{ color: agent.color }}>
                                            <span>{agent.icon}</span>
                                            <span className="suggestion-agent-name">{agent.label}</span>
                                        </div>
                                        {agent.examples.map((ex) => (
                                            <button
                                                key={ex}
                                                className="suggestion-item"
                                                onMouseDown={(e) => {
                                                    e.preventDefault();
                                                    setInput(ex);
                                                    setActiveAgent(detectAgent(ex));
                                                    setShowSuggestions(false);
                                                    inputRef.current?.focus();
                                                }}
                                            >
                                                {ex}
                                            </button>
                                        ))}
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
                <div className="input-wrapper">
                    <textarea
                        ref={inputRef}
                        className="chat-input"
                        placeholder="Ask about taxes, markets, budgeting…"
                        value={input}
                        onChange={(e) => {
                            setInput(e.target.value);
                            if (e.target.value) {
                                setActiveAgent(detectAgent(e.target.value));
                                setShowSuggestions(false);
                            } else {
                                setShowSuggestions(true);
                            }
                        }}
                        onFocus={() => { if (!input) setShowSuggestions(true); }}
                        onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                        onKeyDown={handleKeyDown}
                        rows={1}
                    />
                    <button
                        className="send-btn"
                        onClick={handleSend}
                        disabled={!input.trim() || loading}
                        style={{ background: agent.color }}
                    >
                        {loading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
                    </button>
                </div>
                <p className="input-hint">
                    Press Enter to send · Shift+Enter for new line
                </p>
            </div>
        </div>
    );
}
