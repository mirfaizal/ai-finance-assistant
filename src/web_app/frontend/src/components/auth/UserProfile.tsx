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
        <div className="flex flex-col border-t border-[#1e2d42] mt-auto bg-transparent pt-3 mt-4">
            <div className="flex items-center gap-3 mb-2 px-2">
                {user.picture ? (
                    <img src={user.picture} alt={user.name} className="w-9 h-9 rounded-full border border-[#1e2d42]" />
                ) : (
                    <UserCircle size={36} className="text-[#8a9ab5]" />
                )}
                <div className="flex flex-col min-w-0">
                    <span className="font-semibold text-sm text-[#e8edf5] truncate">{user.name}</span>
                    <span className="text-xs text-[#8a9ab5] truncate">{user.email}</span>
                </div>
            </div>
            <LogoutButton />
        </div>
    );
};
