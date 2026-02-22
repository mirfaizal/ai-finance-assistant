import { useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { ChatInterface } from './components/ChatInterface';
import { RightSidebar } from './components/RightSidebar';
import { RiskModal } from './components/RiskModal';
import {
  getSessions, createSession, getActiveSessionId, setActiveSessionId, saveProfile, getProfile, deleteSession,
} from './lib/storage';
import type { ChatSession, UserProfile } from './lib/types';

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeView, setActiveView] = useState<'dashboard' | 'chat'>('dashboard');
  const [sessions, setSessions] = useState<ChatSession[]>(() => getSessions());
  const [activeSessionId, setActiveSessionIdState] = useState<string | null>(() => getActiveSessionId());
  const [profile, setProfile] = useState<UserProfile>(() => getProfile());
  const [prefill, setPrefill] = useState<string | undefined>();
  const [showModal, setShowModal] = useState(() => {
    const p = getProfile();
    return p.isNewUser || !p.completedOnboarding;
  });

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
    const sid = ensureSession();
    if (text) setPrefill(text);
    setActiveView('chat');
    if (!activeSessionId) {
      setActiveSessionIdState(sid);
    }
  };

  const handleNewSession = () => {
    const s = createSession();
    setSessions(getSessions());
    setActiveSessionIdState(s.id);
    setActiveView('chat');
    setPrefill(undefined);
  };

  const handleSessionSelect = (id: string) => {
    setActiveSessionId(id);
    setActiveSessionIdState(id);
    setActiveView('chat');
  };

  const handleDeleteSession = (id: string) => {
    deleteSession(id);
    setSessions(getSessions());
    if (activeSessionId === id) {
      setActiveSessionIdState(null);
      setActiveView('dashboard');
    }
  };

  return (
    <>
      {showModal && <RiskModal onComplete={handleModalComplete} />}

      <div className="app-shell">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((c) => !c)}
          activeView={activeView}
          onViewChange={setActiveView}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSessionSelect={handleSessionSelect}
          onNewSession={handleNewSession}
          onDeleteSession={handleDeleteSession}
        />

        <main className="app-main">
          <AnimatePresence mode="wait">
            {activeView === 'dashboard' ? (
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
            ) : (
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
            )}
          </AnimatePresence>
        </main>

        <RightSidebar />
      </div>
    </>
  );
}
