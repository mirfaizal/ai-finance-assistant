import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { TrendingUp, LogIn, UserPlus, Shield } from 'lucide-react';
import { motion } from 'framer-motion';

export const AuthPage: React.FC = () => {
    const { loginWithRedirect } = useAuth0();

    return (
        <div className="auth-page">
            <div className="auth-glow-1" />
            <div className="auth-glow-2" />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="auth-card"
            >
                <div className="auth-header">
                    <div className="auth-logo">
                        <TrendingUp size={32} />
                    </div>
                    <h1 className="auth-title">FinAI Assistant</h1>
                    <p className="auth-subtitle">
                        Sign in to securely access your portfolio, chat history, and personalized market insights.
                    </p>
                </div>

                <div className="auth-actions">
                    <button
                        onClick={() => loginWithRedirect()}
                        className="auth-btn auth-btn-primary"
                    >
                        <LogIn size={18} />
                        <span>Log In</span>
                    </button>

                    <button
                        onClick={() => loginWithRedirect({ authorizationParams: { screen_hint: 'signup' } })}
                        className="auth-btn auth-btn-secondary"
                    >
                        <UserPlus size={18} />
                        <span>Create Account</span>
                    </button>
                </div>

                <div className="auth-footer">
                    <Shield size={14} />
                    <span>Secured by Auth0 Enterprise</span>
                </div>
            </motion.div>
        </div>
    );
};
