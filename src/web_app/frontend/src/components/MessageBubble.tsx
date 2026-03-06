import { useState } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ThumbsUp, ThumbsDown, CheckCircle } from 'lucide-react';
import { getAgent } from '../lib/agentEngine';
import { sendFeedback } from '../lib/api';
import type { Message } from '../lib/types';

interface MessageBubbleProps {
    message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const [feedbackState, setFeedbackState] = useState<'none' | 'loading' | 'success' | 'error'>('none');
    const isUser = message.role === 'user';
    const agent = message.agent ? getAgent(message.agent) : null;
    const agentColor = agent?.color ?? '#14b8a6';
    const agentLabel = agent?.title ?? 'Finnie';

    // Use LangSmith run_id when available; fall back to the local message id
    // so thumbs are always shown regardless of whether tracing is configured.
    const feedbackId = message.run_id ?? message.id;

    const handleFeedback = async (score: number) => {
        if (!feedbackId || feedbackState !== 'none') return;
        setFeedbackState('loading');
        try {
            await sendFeedback(feedbackId, score);
            setFeedbackState('success');
        } catch (err) {
            console.error('Failed to send feedback', err);
            setFeedbackState('error');
            setTimeout(() => setFeedbackState('none'), 3000);
        }
    };

    return (
        <motion.div
            className={`message-row ${isUser ? 'user-row' : 'ai-row'}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
        >
            {!isUser && (
                <div className="msg-avatar" style={{ background: agentColor }}>
                    {agentLabel.charAt(0)}
                </div>
            )}

            <div className={`msg-bubble ${isUser ? 'user-bubble' : 'ai-bubble'}`}>
                {!isUser && agent && (
                    <div className="msg-agent-tag" style={{ color: agentColor }}>
                        {agent.title}
                    </div>
                )}

                {isUser ? (
                    <p className="msg-text">{message.content}</p>
                ) : (
                    <div className="msg-markdown">
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                                // Open links in new tab safely
                                a: ({ node: _n, ...props }) => (
                                    <a {...props} target="_blank" rel="noopener noreferrer" />
                                ),
                            }}
                        >
                            {message.content}
                        </ReactMarkdown>
                    </div>
                )}

                {!isUser && (
                    <div className="msg-feedback" style={{ display: 'flex', gap: '8px', marginTop: '12px', alignItems: 'center' }}>
                        {feedbackState === 'none' || feedbackState === 'error' ? (
                            <>
                                <button
                                    onClick={() => handleFeedback(1)}
                                    title="Helpful"
                                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#9ca3af', display: 'flex', alignItems: 'center', padding: '4px', borderRadius: '4px' }}
                                    onMouseOver={(e) => e.currentTarget.style.color = agentColor}
                                    onMouseOut={(e) => e.currentTarget.style.color = '#9ca3af'}
                                >
                                    <ThumbsUp size={14} />
                                </button>
                                <button
                                    onClick={() => handleFeedback(0)}
                                    title="Not helpful"
                                    style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#9ca3af', display: 'flex', alignItems: 'center', padding: '4px', borderRadius: '4px' }}
                                    onMouseOver={(e) => e.currentTarget.style.color = '#ef4444'}
                                    onMouseOut={(e) => e.currentTarget.style.color = '#9ca3af'}
                                >
                                    <ThumbsDown size={14} />
                                </button>
                                {feedbackState === 'error' && <span style={{ fontSize: '11px', color: '#ef4444' }}>Error sending</span>}
                            </>
                        ) : feedbackState === 'loading' ? (
                            <span style={{ fontSize: '11px', color: '#9ca3af' }}>Sending feedback...</span>
                        ) : (
                            <span style={{ fontSize: '11px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <CheckCircle size={12} /> Thank you!
                            </span>
                        )}
                    </div>
                )}

                <span className="msg-time">
                    {new Date(message.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                    })}
                </span>
            </div>

            {isUser && (
                <div className="msg-avatar user-avatar">
                    👤
                </div>
            )}
        </motion.div>
    );
}
