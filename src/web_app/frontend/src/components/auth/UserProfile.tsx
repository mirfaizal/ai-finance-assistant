import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { UserCircle } from 'lucide-react';
import { LogoutButton } from './LogoutButton';

export const UserProfile: React.FC = () => {
    const { user, isAuthenticated, isLoading } = useAuth0();

    if (isLoading || !isAuthenticated || !user) {
        return null;
    }

    return (
        <div className="user-profile-container">
            <div className="user-profile-header">
                {user.picture ? (
                    <img src={user.picture} alt={user.name} className="user-avatar" />
                ) : (
                    <UserCircle size={36} className="user-avatar-fallback" />
                )}
                <div className="user-info">
                    <span className="user-name">{user.name}</span>
                    <span className="user-email">{user.email}</span>
                </div>
            </div>
            <LogoutButton />
        </div>
    );
};
