import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BookOpen, FileText, Video, CheckCircle } from 'lucide-react';
import { LEARNING_COURSES } from '../lib/mockData';
import { generateQuiz, submitQuizAnswer, getCoinBalance } from '../lib/api';
import { getActiveSessionId, getBackendSessionId } from '../lib/storage';

const ICON_MAP = [BookOpen, FileText, Video, CheckCircle];

export function LearningPage() {
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

      <section className="courses-section">
        <div className="courses-grid">
          {LEARNING_COURSES.map((course, i) => {
            const Icon = ICON_MAP[i % ICON_MAP.length];
            return (
              <motion.div
                key={course.id}
                className="course-card"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
              >
                <div className="course-card-icon">
                  <Icon size={24} />
                </div>
                <h3 className="course-card-title">{course.title}</h3>
                <p className="course-card-desc">{course.desc}</p>
                <div className="course-progress-wrap">
                  <div className="course-progress-bar">
                    <div
                      className="course-progress-fill"
                      style={{ width: `${course.progress}%` }}
                    />
                  </div>
                  <span className="course-progress-label">{course.progress}% Complete</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </section>

      <motion.section
        className="daily-quiz-section"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <h2 className="daily-quiz-title">Daily Quiz</h2>
        <p className="daily-quiz-desc">Test your knowledge on compound interest and earn coins.</p>

        <QuizWidget />
      </motion.section>
    </div>
  );
}

function QuizWidget() {
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState<any>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [result, setResult] = useState<any>(null);
  const [coins, setCoins] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const frontendSid = getActiveSessionId() ?? '';
  const sessionId = getBackendSessionId(frontendSid) ?? frontendSid;

  useEffect(() => {
    if (!sessionId) return;
    getCoinBalance(sessionId)
      .then((r) => setCoins(r.coins))
      .catch(() => {});
  }, [sessionId]);

  async function startQuiz() {
    setLoading(true);
    setResult(null);
    setSelected(null);
    setError(null);
    try {
      const q = await generateQuiz('compound interest', sessionId || undefined);
      setQuestion(q);
    } catch (err) {
      console.error('Quiz generate failed', err);
      setQuestion(null);
      setError('Failed to generate question. Please try again.');
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

  return (
    <div className="quiz-widget">
      <div className="quiz-coins">Coins: {coins}</div>

      {!question && (
        <div>
          <p>Ready for a quick question?</p>
          <button className="daily-quiz-btn" onClick={startQuiz} disabled={loading}>
            {loading ? 'Loading…' : 'Start Quiz'}
          </button>
          {error && <div className="quiz-error">{error}</div>}
        </div>
      )}

      {question && (
        <div className="quiz-question">
          <h3>{question.question}</h3>
          <ul className="quiz-choices">
            {question.choices.map((c: string, i: number) => (
              <li key={i}>
                <button
                  className={`quiz-choice ${selected !== null ? (i === selected ? 'selected' : '') : ''}`}
                  onClick={() => submitAnswer(i)}
                  disabled={loading || selected !== null}
                >
                  {c}
                </button>
              </li>
            ))}
          </ul>
          {error && <div className="quiz-error">{error}</div>}
        </div>
      )}

      {result && (
        <div className="quiz-result">
          {result.correct ? (
            <div className="quiz-correct">Correct! +{result.awarded} coins</div>
          ) : (
            <div className="quiz-incorrect">Incorrect — no coins awarded</div>
          )}
          <div className="quiz-balance">Balance: {result.coins} coins</div>
          <button className="daily-quiz-btn" onClick={() => { setQuestion(null); setResult(null); setSelected(null); }}>
            Next
          </button>
        </div>
      )}
    </div>
  );
}
