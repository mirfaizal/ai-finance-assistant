import { motion } from 'framer-motion';
import type { Agent } from '../lib/types';

interface AgentBadgeProps {
    agent: Agent;
    pulse?: boolean;
}

export function AgentBadge({ agent, pulse = false }: AgentBadgeProps) {
    return (
        <motion.div
            layout
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="agent-badge"
            style={{ '--agent-color': agent.color } as React.CSSProperties}
        >
            {pulse && (
                <span className="badge-pulse" style={{ background: agent.color }} />
            )}
            <span className="badge-dot" style={{ background: agent.color }} />
            <span className="badge-name">{agent.name}</span>
            <span className="badge-title">{agent.title}</span>
        </motion.div>
    );
}
