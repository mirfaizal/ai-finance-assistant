import { motion, AnimatePresence } from 'framer-motion';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, MessageSquare, ChevronLeft, ChevronRight,
  TrendingUp, BookOpen, Sparkles, Clock, Trash2, LogOut, Briefcase,
} from 'lucide-react';
import type { ChatSession } from '../lib/types';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSessionSelect: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
}

const NAV = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/assistant', label: 'Assistant', icon: MessageSquare },
  { path: '/markets', label: 'Markets', icon: TrendingUp },
  { path: '/learn', label: 'Learning', icon: BookOpen },
  { path: '/portfolio', label: 'Portfolio', icon: Briefcase },
] as const;

export function Sidebar({
  collapsed, onToggle,
  sessions, activeSessionId, onSessionSelect, onNewSession, onDeleteSession,
}: SidebarProps) {
  const navigate = useNavigate();

  const handleSignOut = () => {
    // Placeholder: clear local session state if needed; could call auth API later
    navigate('/');
  };

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 260 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="sidebar"
    >
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
              FinAI
            </motion.span>
          )}
        </AnimatePresence>
        <button className="collapse-btn" onClick={onToggle} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {!collapsed && (
        <motion.button
          type="button"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="new-chat-btn"
          onClick={onNewSession}
        >
          <Sparkles size={15} />
          New Chat
        </motion.button>
      )}

      <nav className="sidebar-nav">
        {NAV.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon size={18} />
            <AnimatePresence>
              {!collapsed && (
                <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  {label}
                </motion.span>
              )}
            </AnimatePresence>
          </NavLink>
        ))}
      </nav>

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
                  onClick={() => {
                    onSessionSelect(s.id);
                    navigate('/assistant');
                  }}
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

      {!collapsed && (
        <button type="button" className="nav-item sign-out-btn" onClick={handleSignOut}>
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      )}
    </motion.aside>
  );
}
