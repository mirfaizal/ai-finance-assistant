import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { LogOut } from 'lucide-react';

export const LogoutButton: React.FC = () => {
    const { logout } = useAuth0();

    return (
        <button
            onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
            className="logout-btn"
        >
            <LogOut size={16} />
            <span>Log Out</span>
        </button>
    );
};
