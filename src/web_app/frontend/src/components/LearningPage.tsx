import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, FileText, Video, CheckCircle, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { submitQuizAnswer, getCoinBalance, getPoolQuiz, getAcademyCourse } from '../lib/api';
import type { CourseBlock } from '../lib/api';
import { getActiveSessionId, getBackendSessionId } from '../lib/storage';

// ── Course catalogue ───────────────────────────────────────────────────────────

const COURSES = [
  {
    id: '1',
    slug: 'investing-101',
    title: 'Investing 101',
    desc: 'Start your journey here.',
    quizTopic: 'investing-basics',
    icon: BookOpen,
    color: '#14b8a6',
  },
  {
    id: '2',
    slug: 'tax-strategies',
    title: 'Tax Strategies',
    desc: 'Keep more of what you earn.',
    quizTopic: 'tax-strategies',
    icon: FileText,
    color: '#8b5cf6',
  },
  {
    id: '3',
    slug: 'market-mechanics',
    title: 'Market Mechanics',
    desc: 'How stock exchanges work.',
    quizTopic: 'market-mechanics',
    icon: Video,
    color: '#3b82f6',
  },
  {
    id: '4',
    slug: 'crypto-basics',
    title: 'Crypto Basics',
    desc: 'Understanding blockchain.',
    quizTopic: 'crypto-basics',
    icon: CheckCircle,
    color: '#f59e0b',
  },
];

// ── Main Page ─────────────────────────────────────────────────────────────────

export function LearningPage() {
  const [activeCourseSlug, setActiveCourseSlug] = useState<string | null>(null);
  const [quizTopic, setQuizTopic] = useState<string | null>(null);

  function handleQuizTopic(topic: string) {
    setQuizTopic(topic);
    // Scroll down to quiz section
    setTimeout(() => {
      document.getElementById('daily-quiz-section')?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  }

  return (
    <div className="page-common">
      <motion.h1
        className="page-title"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        Financial Academy
      </motion.h1>

      {/* Course Cards */}
      <section className="courses-section">
        <div className="courses-grid">
          {COURSES.map((course, i) => {
            const Icon = course.icon;
            const isOpen = activeCourseSlug === course.slug;
            return (
              <CourseCard
                key={course.id}
                course={course}
                Icon={Icon}
                isOpen={isOpen}
                index={i}
                onToggle={() => setActiveCourseSlug(isOpen ? null : course.slug)}
                onQuiz={() => handleQuizTopic(course.quizTopic)}
              />
            );
          })}
        </div>
      </section>

      {/* Daily Quiz */}
      <motion.section
        id="daily-quiz-section"
        className="daily-quiz-section"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <h2 className="daily-quiz-title">Daily Quiz</h2>
        <p className="daily-quiz-desc">
          {quizTopic
            ? `Testing your knowledge on ${COURSES.find(c => c.quizTopic === quizTopic)?.title ?? quizTopic}.`
            : 'Test your financial knowledge and earn coins.'}
          {quizTopic && (
            <button
              className="quiz-topic-reset"
              onClick={() => setQuizTopic(null)}
              style={{ marginLeft: 8, fontSize: '0.8rem', opacity: 0.7, cursor: 'pointer', background: 'none', border: 'none', color: 'inherit', textDecoration: 'underline' }}
            >
              (any topic)
            </button>
          )}
        </p>
        <QuizWidget topic={quizTopic} />
      </motion.section>
    </div>
  );
}

// ── Course Card (expandable with RAG content) ─────────────────────────────────

interface CourseCardProps {
  course: typeof COURSES[0];
  Icon: typeof BookOpen;
  isOpen: boolean;
  index: number;
  onToggle: () => void;
  onQuiz: () => void;
}

function CourseCard({ course, Icon, isOpen, index, onToggle, onQuiz }: CourseCardProps) {
  const [loading, setLoading] = useState(false);
  const [blocks, setBlocks] = useState<CourseBlock[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || blocks !== null) return;  // already loaded or closed
    setLoading(true);
    setError(null);
    getAcademyCourse(course.slug)
      .then(res => setBlocks(res.from_rag ? res.blocks : []))
      .catch(err => {
        console.error('Academy course fetch failed', err);
        setError('Could not load content. Is Pinecone configured?');
        setBlocks([]);
      })
      .finally(() => setLoading(false));
  }, [isOpen, course.slug, blocks]);

  return (
    <motion.div
      className="course-card"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      style={{ cursor: 'pointer' }}
    >
      {/* Card header — always visible */}
      <div
        className="course-card-header"
        onClick={onToggle}
        style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}
      >
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flex: 1 }}>
          <div className="course-card-icon" style={{ color: course.color, flexShrink: 0 }}>
            <Icon size={24} />
          </div>
          <div>
            <h3 className="course-card-title">{course.title}</h3>
            <p className="course-card-desc">{course.desc}</p>
          </div>
        </div>
        <div style={{ flexShrink: 0, opacity: 0.5 }}>
          {isOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </div>

      {/* Expandable RAG content */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="content"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: 'hidden' }}
          >
            <div className="course-rag-content" style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
              {loading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, opacity: 0.7, fontSize: '0.85rem' }}>
                  <Loader2 size={14} className="spin" />
                  Loading from knowledge base…
                </div>
              )}
              {error && (
                <p style={{ color: '#f87171', fontSize: '0.82rem' }}>{error}</p>
              )}
              {!loading && blocks !== null && blocks.length === 0 && !error && (
                <p style={{ opacity: 0.6, fontSize: '0.85rem' }}>
                  No content found in Pinecone yet. Seed the knowledge base via{' '}
                  <code>POST /rag/seed</code>.
                </p>
              )}
              {blocks && blocks.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {blocks.map((block, i) => (
                    <div
                      key={i}
                      className="rag-block"
                      style={{
                        background: 'rgba(255,255,255,0.04)',
                        borderRadius: 8,
                        padding: '10px 14px',
                        fontSize: '0.88rem',
                        lineHeight: 1.6,
                      }}
                    >
                      {block.text}
                    </div>
                  ))}
                </div>
              )}

              {/* Button to run a quiz on this course's topic */}
              {!loading && (
                <button
                  className="daily-quiz-btn"
                  onClick={e => { e.stopPropagation(); onQuiz(); }}
                  style={{ marginTop: 12, fontSize: '0.82rem', padding: '6px 14px' }}
                >
                  Quiz me on {course.title}
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Quiz Widget ───────────────────────────────────────────────────────────────

interface QuizWidgetProps {
  topic: string | null;
}

function QuizWidget({ topic }: QuizWidgetProps) {
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState<any>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [result, setResult] = useState<any>(null);
  const [coins, setCoins] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [questionCount, setQuestionCount] = useState(0);

  const frontendSid = getActiveSessionId() ?? '';
  const sessionId = getBackendSessionId(frontendSid) ?? frontendSid;

  useEffect(() => {
    if (!sessionId) return;
    getCoinBalance(sessionId)
      .then(r => setCoins(r.coins))
      .catch(() => {});
  }, [sessionId]);

  // When topic changes, reset and auto-load a new question
  useEffect(() => {
    if (topic !== null) {
      fetchQuestion();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topic]);

  async function fetchQuestion() {
    setLoading(true);
    setResult(null);
    setSelected(null);
    setError(null);
    try {
      const q = await getPoolQuiz(sessionId || undefined, topic || undefined);
      setQuestion(q);
      setQuestionCount(prev => prev + 1);
    } catch (err) {
      console.error('Quiz fetch failed', err);
      setQuestion(null);
      setError('Failed to load question. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function submitAnswer(idx: number) {
    if (!question) return;
    setLoading(true);
    setError(null);
    try {
      const res = await submitQuizAnswer(question.question_id, idx, sessionId || undefined);
      setSelected(idx);
      setResult(res);
      if (res && typeof res.coins === 'number') setCoins(res.coins);
    } catch (err) {
      console.error('Submit answer failed', err);
      setError('Failed to submit answer. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  function handleNext() {
    setQuestion(null);
    setResult(null);
    setSelected(null);
    fetchQuestion();
  }

  // Topic label for display
  const topicLabel = topic
    ? COURSES.find(c => c.quizTopic === topic)?.title ?? topic
    : 'All Topics';

  return (
    <div className="quiz-widget">
      <div className="quiz-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="quiz-coins">🪙 Coins: {coins}</div>
        {questionCount > 0 && (
          <div style={{ fontSize: '0.78rem', opacity: 0.55 }}>
            #{questionCount} · {topicLabel}
          </div>
        )}
      </div>

      {/* Initial state — before first question */}
      {!question && !loading && (
        <div>
          <p style={{ marginBottom: 12 }}>Ready for a quick question? Questions come from the Financial Academy knowledge base.</p>
          <button className="daily-quiz-btn" onClick={fetchQuestion} disabled={loading}>
            {loading ? 'Loading…' : 'Start Quiz'}
          </button>
          {error && <div className="quiz-error" style={{ marginTop: 10 }}>{error}</div>}
        </div>
      )}

      {/* Loading spinner */}
      {!question && loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, opacity: 0.7, padding: '12px 0' }}>
          <Loader2 size={16} className="spin" />
          Fetching question from Pinecone…
        </div>
      )}

      {/* Question */}
      {question && (
        <div className="quiz-question">
          <h3 style={{ marginBottom: 12, lineHeight: 1.5 }}>{question.question}</h3>
          <ul className="quiz-choices" style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {question.choices.map((c: string, i: number) => {
              let btnClass = 'quiz-choice';
              if (selected !== null && result) {
                if (i === selected && result.correct) btnClass += ' quiz-choice-correct';
                else if (i === selected && !result.correct) btnClass += ' quiz-choice-wrong';
              } else if (i === selected) {
                btnClass += ' selected';
              }
              return (
                <li key={i}>
                  <button
                    className={btnClass}
                    onClick={() => submitAnswer(i)}
                    disabled={loading || selected !== null}
                    style={{ width: '100%', textAlign: 'left' }}
                  >
                    <span style={{ opacity: 0.5, marginRight: 8 }}>{String.fromCharCode(65 + i)}.</span>
                    {c}
                  </button>
                </li>
              );
            })}
          </ul>
          {error && <div className="quiz-error" style={{ marginTop: 8 }}>{error}</div>}
        </div>
      )}

      {/* Result feedback */}
      {result && (
        <div className="quiz-result" style={{ marginTop: 14 }}>
          {result.correct ? (
            <div className="quiz-correct">✅ Correct! +{result.awarded} coins</div>
          ) : (
            <div className="quiz-incorrect">❌ Incorrect — no coins awarded</div>
          )}
          <div className="quiz-balance" style={{ marginTop: 4, fontSize: '0.85rem', opacity: 0.7 }}>
            Balance: {result.coins} coins
          </div>
          <button
            className="daily-quiz-btn"
            onClick={handleNext}
            style={{ marginTop: 12 }}
          >
            Next Question →
          </button>
        </div>
      )}
    </div>
  );
}

