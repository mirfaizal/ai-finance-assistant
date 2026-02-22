import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getAgent } from '../lib/agentEngine';
import type { Message } from '../lib/types';

interface MessageBubbleProps {
    message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === 'user';
    const agent = message.agent ? getAgent(message.agent) : null;
    const agentColor = agent?.color ?? '#14b8a6';
    const agentLabel = agent?.title ?? 'Finnie';

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
