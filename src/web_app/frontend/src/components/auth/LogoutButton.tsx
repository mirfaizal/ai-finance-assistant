import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { LogOut } from 'lucide-react';

export const LogoutButton: React.FC = () => {
    const { logout } = useAuth0();

    return (
        <button
            onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
            className="flex items-center gap-2 px-3 py-2 w-full text-left rounded-md transition-colors text-[#8a9ab5] hover:text-[#e8edf5] hover:bg-[#161e2e]"
        >
            <LogOut size={16} />
            <span className="font-medium text-sm">Log Out</span>
        </button>
    );
};
