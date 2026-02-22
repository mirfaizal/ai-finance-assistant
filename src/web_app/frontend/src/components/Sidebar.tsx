import { motion, AnimatePresence } from 'framer-motion';
import {
    LayoutDashboard, MessageSquare, ChevronLeft, ChevronRight,
    TrendingUp, BookOpen, Sparkles, Clock, Trash2,
} from 'lucide-react';
import type { ChatSession } from '../lib/types';

interface SidebarProps {
    collapsed: boolean;
    onToggle: () => void;
    activeView: 'dashboard' | 'chat';
    onViewChange: (v: 'dashboard' | 'chat') => void;
    sessions: ChatSession[];
    activeSessionId: string | null;
    onSessionSelect: (id: string) => void;
    onNewSession: () => void;
    onDeleteSession: (id: string) => void;
}

const NAV = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
] as const;

export function Sidebar({
    collapsed, onToggle, activeView, onViewChange,
    sessions, activeSessionId, onSessionSelect, onNewSession, onDeleteSession,
}: SidebarProps) {
    return (
        <motion.aside
            animate={{ width: collapsed ? 72 : 260 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="sidebar"
        >
            {/* Logo */}
            <div className="sidebar-logo">
                <div className="logo-icon">
                    <TrendingUp size={20} />
                </div>
                <AnimatePresence>
                    {!collapsed && (
                        <motion.span
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            className="logo-text"
                        >
                            Finnie AI
                        </motion.span>
                    )}
                </AnimatePresence>
                <button className="collapse-btn" onClick={onToggle}>
                    {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
                </button>
            </div>

            {/* New Chat */}
            {!collapsed && (
                <motion.button
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="new-chat-btn"
                    onClick={onNewSession}
                >
                    <Sparkles size={15} />
                    New Chat
                </motion.button>
            )}

            {/* Nav */}
            <nav className="sidebar-nav">
                {NAV.map(({ id, label, icon: Icon }) => (
                    <button
                        key={id}
                        className={`nav-item ${activeView === id ? 'active' : ''}`}
                        onClick={() => onViewChange(id as 'dashboard' | 'chat')}
                    >
                        <Icon size={18} />
                        <AnimatePresence>
                            {!collapsed && (
                                <motion.span
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                >
                                    {label}
                                </motion.span>
                            )}
                        </AnimatePresence>
                    </button>
                ))}
            </nav>

            {/* Sessions */}
            <AnimatePresence>
                {!collapsed && sessions.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="session-list"
                    >
                        <div className="session-list-header">
                            <Clock size={13} />
                            <span>Recent</span>
                        </div>
                        {sessions.slice(0, 8).map((s) => (
                            <div
                                key={s.id}
                                className={`session-item-wrapper ${activeSessionId === s.id ? 'active' : ''}`}
                            >
                                <button
                                    type="button"
                                    className="session-item"
                                    onClick={() => onSessionSelect(s.id)}
                                >
                                    <BookOpen size={13} />
                                    <span className="session-title">{s.title}</span>
                                </button>
                                <button
                                    type="button"
                                    className="session-item-delete"
                                    onClick={() => onDeleteSession(s.id)}
                                    aria-label="Delete chat"
                                >
                                    <Trash2 size={12} />
                                </button>
                            </div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.aside>
    );
}
