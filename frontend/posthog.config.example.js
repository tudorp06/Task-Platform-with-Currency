// Production (Netlify): set env POSTHOG_BROWSER_PROJECT_TOKEN to your PostHog project key (phc_…).
// The build runs scripts/inject-posthog-browser-token.mjs and overwrites posthog.browser.js.
//
// Local dev without a build: copy this file to posthog.local.js, put your phc_ token in it, and add
//   <script src="./posthog.local.js"></script>
// before posthog.browser.js in the HTML page you are testing (posthog.local.js stays gitignored).
window.__POSTHOG_PROJECT_TOKEN__ = "phc_replace_with_your_project_token";
