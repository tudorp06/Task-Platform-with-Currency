/**
 * CI (e.g. Vercel): set APP_API_BASE_URL to your backend API root, including `/api` suffix
 * (e.g. https://your-service.onrender.com/api). Writes frontend/js/api-config.js before publish.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(__dirname, "..", "frontend", "js", "api-config.js");
const raw = (process.env.APP_API_BASE_URL || process.env.VERCEL_APP_API_BASE_URL || "").trim();
let normalized = raw.replace(/\/+$/, "");
if (normalized && !normalized.endsWith("/api")) {
  normalized = `${normalized}/api`;
}
const body = `// Generated at build time from APP_API_BASE_URL (do not put secrets here; URL is public).
window.__APP_API_BASE_URL__ = ${JSON.stringify(normalized)};
`;
fs.writeFileSync(out, body, "utf8");
