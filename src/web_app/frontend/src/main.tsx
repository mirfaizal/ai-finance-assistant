import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Auth0Provider } from '@auth0/auth0-react';
import './index.css';
import App from './App.tsx';

// Load Auth0 config either from Vite's build-time env or the runtime-inserted window object
const getEnv = (key: string) => {
  return import.meta.env[`VITE_${key}`] || (window as any).ENV?.[key] || '';
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Auth0Provider
      domain={getEnv('AUTH0_DOMAIN')}
      clientId={getEnv('AUTH0_CLIENT_ID')}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: getEnv('AUTH0_AUDIENCE'),
      }}
      onRedirectCallback={(appState) => {
        // After Auth0 processes the callback, navigate to the intended URL
        // (or fall back to the current path stripped of auth query params).
        window.history.replaceState(
          {},
          document.title,
          appState?.returnTo ?? window.location.pathname,
        );
      }}
    >
      <App />
    </Auth0Provider>
  </StrictMode>
);
