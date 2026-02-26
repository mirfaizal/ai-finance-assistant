import { useState, useCallback, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, NavLink } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { LayoutDashboard, MessageSquare, TrendingUp, BookOpen, Briefcase } from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { ChatInterface } from './components/ChatInterface';
import { RightSidebar } from './components/RightSidebar';
import { MarketsPage } from './components/MarketsPage';
import { LearningPage } from './components/LearningPage';
import { PortfolioPage } from './components/PortfolioPage';
import { RiskModal } from './components/RiskModal';
import {
  getSessions, createSession, getActiveSessionId, setActiveSessionId, saveProfile, getProfile, deleteSession,
} from './lib/storage';
import type { ChatSession, UserProfile } from './lib/types';

const MOBILE_NAV = [
  { path: '/', label: 'Home', icon: LayoutDashboard },
  { path: '/assistant', label: 'Chat', icon: MessageSquare },
  { path: '/markets', label: 'Markets', icon: TrendingUp },
  { path: '/learn', label: 'Learn', icon: BookOpen },
  { path: '/portfolio', label: 'Portfolio', icon: Briefcase },
] as const;

function MobileNav() {
  return (
    <nav className="mobile-nav" aria-label="Mobile navigation">
      {MOBILE_NAV.map(({ path, label, icon: Icon }) => (
        <NavLink
          key={path}
          to={path}
          end={path === '/'}
          className={({ isActive }) => `mobile-nav-item${isActive ? ' active' : ''}`}
        >
          <Icon size={20} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

function AppContent() {
  const navigate = useNavigate();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => window.innerWidth <= 1024);
  const [sessions, setSessions] = useState<ChatSession[]>(() => getSessions());
  const [activeSessionId, setActiveSessionIdState] = useState<string | null>(() => getActiveSessionId());
  const [profile, setProfile] = useState<UserProfile>(() => getProfile());
  const [prefill, setPrefill] = useState<string | undefined>();
  const [showModal, setShowModal] = useState(() => {
    const p = getProfile();
    return p.isNewUser || !p.completedOnboarding;
  });

  // Auto-collapse sidebar on tablet / expand on desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 1024) {
        setSidebarCollapsed(true);
      } else {
        setSidebarCollapsed(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleModalComplete = (updates: Partial<UserProfile>) => {
    const updated = { ...profile, ...updates };
    saveProfile(updated);
    setProfile(updated);
    setShowModal(false);
  };

  const ensureSession = useCallback(() => {
    if (!activeSessionId) {
      const s = createSession();
      setActiveSessionIdState(s.id);
      setSessions(getSessions());
      return s.id;
    }
    return activeSessionId;
  }, [activeSessionId]);

  const handleStartChat = (text?: string) => {
    ensureSession();
    if (text) setPrefill(text);
    navigate('/assistant');
  };

  const handleNewSession = () => {
    const s = createSession();
    setSessions(getSessions());
    setActiveSessionIdState(s.id);
    navigate('/assistant');
    setPrefill(undefined);
  };

  const handleSessionSelect = (id: string) => {
    setActiveSessionId(id);
    setActiveSessionIdState(id);
    navigate('/assistant');
  };

  const handleDeleteSession = (id: string) => {
    deleteSession(id);
    setSessions(getSessions());
    if (activeSessionId === id) {
      setActiveSessionIdState(null);
      navigate('/');
    }
  };

  return (
    <>
      {showModal && <RiskModal onComplete={handleModalComplete} />}

      <div className="app-shell">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((c) => !c)}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
          onDeleteSession={handleDeleteSession}
        />

        <main className="app-main">
          <AnimatePresence mode="wait">
            <Routes>
              <Route
                path="/"
                element={
                  <motion.div
                    key="dashboard"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.25 }}
                    className="view-wrapper"
                  >
                    <Dashboard onStartChat={handleStartChat} />
                  </motion.div>
                }
              />
              <Route
                path="/assistant"
                element={
                  <motion.div
                    key="chat"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    transition={{ duration: 0.25 }}
                    className="view-wrapper"
                  >
                    <ChatInterface
                      sessionId={ensureSession()}
                      prefillMessage={prefill}
                      onPrefillConsumed={() => setPrefill(undefined)}
                    />
                  </motion.div>
                }
              />
              <Route
                path="/markets"
                element={
                  <motion.div
                    key="markets"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="view-wrapper"
                  >
                    <MarketsPage />
                  </motion.div>
                }
              />
              <Route
                path="/learn"
                element={
                  <motion.div
                    key="learn"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="view-wrapper"
                  >
                    <LearningPage />
                  </motion.div>
                }
              />
              <Route
                path="/portfolio"
                element={
                  <motion.div
                    key="portfolio"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="view-wrapper"
                  >
                    <PortfolioPage />
                  </motion.div>
                }
              />
            </Routes>
          </AnimatePresence>
        </main>

        <RightSidebar />
      </div>

      <MobileNav />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
