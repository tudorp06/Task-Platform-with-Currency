// Default for local dev / pre-build: empty string â†’ JS bundles use their built-in fallback URL.
// Vercel build runs scripts/inject-api-base-url.mjs and overwrites this file.
window.__APP_API_BASE_URL__ = "";

