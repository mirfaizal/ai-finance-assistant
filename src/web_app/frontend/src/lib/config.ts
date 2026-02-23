/**
 * Centralized API base URL configuration.
 *
 * In Docker / production:
 *   VITE_API_BASE_URL is "" (empty) → all calls are relative paths.
 *   Nginx proxies  /api/*  →  backend:8000  (stripping the /api prefix).
 *   So a fetch to "/api/market/overview" hits backend's "/market/overview".
 *
 * In local Vite dev (npm run dev):
 *   VITE_API_BASE_URL is also "" (env not set).
 *   Vite dev-server proxy handles  /api/*  →  http://localhost:8000.
 *
 * If you need to point directly at a remote backend (e.g. staging), set:
 *   VITE_API_BASE_URL=https://api.example.com  in .env.local
 *   (and remove or adjust the /api prefix below accordingly)
 */

const _raw = import.meta.env.VITE_API_BASE_URL as string | undefined;

/**
 * Prefix to prepend to every API path.
 * - "" (default)  → relative URLs via nginx/Vite proxy  (/api/<path>)
 * - "https://..."  → direct backend URL, no /api prefix needed
 */
export const BASE_URL: string =
  _raw !== undefined && _raw !== ''
    ? _raw          // explicit override (e.g. https://api.example.com)
    : '/api';       // default: relative, proxied by nginx / Vite
