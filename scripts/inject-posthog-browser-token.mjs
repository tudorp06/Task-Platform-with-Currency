/**
 * Netlify (or any CI): set POSTHOG_BROWSER_PROJECT_TOKEN to your PostHog **project API key**
 * (the phc_… token from PostHog → Project settings). This writes frontend/posthog.browser.js before publish.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(__dirname, "..", "frontend", "posthog.browser.js");
const token = (process.env.POSTHOG_BROWSER_PROJECT_TOKEN || "").trim();
const body = `// Generated at build time from POSTHOG_BROWSER_PROJECT_TOKEN (do not commit real tokens).
window.__POSTHOG_PROJECT_TOKEN__ = ${JSON.stringify(token)};
`;
fs.writeFileSync(out, body, "utf8");
