const SESSION_KEY = "app_contributor_session";
const USERS_DB_KEY = "app_contributor_users_db";
const LAST_PAGE_KEY = "app_contributor_last_page";
const AUTH_TOKEN_KEY = "app_contributor_auth_token";
const API_BASE_URL = "https://appcontributor-backend.onrender.com/api";

const navbarRight = document.getElementById("navbar-right");
const authModal = document.getElementById("auth-modal");
const authForm = document.getElementById("auth-form");
const closeModalBtn = document.getElementById("close-modal");
const contributorBtn = document.getElementById("join-contributor");
const startupBtn = document.getElementById("join-startup");
const authRoleLabel = document.getElementById("auth-role-label");
const brandLink = document.getElementById("brand-link");
const authModeLoginBtn = document.getElementById("auth-mode-login");
const authModeSignupBtn = document.getElementById("auth-mode-signup");
const authFeedback = document.getElementById("auth-feedback");
const nameInput = document.getElementById("input-name");
const emailInput = document.getElementById("input-email");
const passwordInput = document.getElementById("input-password");
const metricAvgEarnings = document.getElementById("metric-avg-earnings");
const metricReviewHours = document.getElementById("metric-review-hours");
const metricApprovedToday = document.getElementById("metric-approved-today");

let activeRole = "contributor";
let authMode = "login";
const isOpsAccess = new URLSearchParams(window.location.search).get("ops") === "1";
let authModalPointerDownOnBackdrop = false;

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function loadSession() {
  return loadJson(SESSION_KEY, null);
}

function saveSession(session) {
  const { authToken, ...safeSession } = session || {};
  saveJson(SESSION_KEY, safeSession);
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

function setAuthToken(token) {
  if (!token) return;
  sessionStorage.setItem(AUTH_TOKEN_KEY, token);
}

function clearAuthToken() {
  sessionStorage.removeItem(AUTH_TOKEN_KEY);
}

function loadUsersDb() {
  return loadJson(USERS_DB_KEY, []);
}

function saveUsersDb(items) {
  saveJson(USERS_DB_KEY, items);
}

function recordUserActivity(session) {
  const users = loadUsersDb();
  const existing = users.find((item) => item.email === session.email);
  if (existing) {
    existing.role = session.role;
    existing.lastLoginAt = new Date().toISOString();
    existing.fullName = session.fullName;
  } else {
    users.push({
      id: session.userId,
      fullName: session.fullName,
      email: session.email,
      role: session.role,
      tasksDone: 0,
      qualityScore: "N/A",
      lastLoginAt: new Date().toISOString(),
      profileCompleted: false,
      yearsOfExperience: 0,
      skills: [],
      githubUrl: "",
      country: "",
      bio: "",
      qualification: "",
      sortingChallengePassed: false,
    });
  }
  saveUsersDb(users);
}

function parseApiError(error, fallback) {
  if (error?.message) return error.message;
  return fallback;
}

function readCookie(name) {
  const target = `${name}=`;
  const cookie = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(target));
  return cookie ? decodeURIComponent(cookie.slice(target.length)) : "";
}

function roleLabel(role) {
  if (role === "startup") return "startup";
  if (role === "admin") return "admin";
  return "contributor";
}

async function trackEvent(sessionLike, event, metadata = {}) {
  const csrfToken = readCookie("appcontributor_csrf");
  try {
    await fetch(`${API_BASE_URL}/analytics/event`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
      body: JSON.stringify({
        event,
        source: "landing",
        userId: sessionLike?.userId ?? null,
        role: sessionLike?.role ?? activeRole,
        metadata,
      }),
    });
  } catch {
    // Non-blocking analytics
  }
}

async function logoutRequest() {
  const csrfToken = readCookie("appcontributor_csrf");
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
    });
  } catch {
    // Ignore logout transport errors; local session is still cleared.
  }
  clearAuthToken();
}

async function postJson(path, payload) {
  const csrfToken = readCookie("appcontributor_csrf");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.detail || "Request failed");
  }
  return body;
}

async function signupRequest({ fullName, email, password, role }) {
  return postJson("/auth/signup", {
    fullName,
    email,
    password,
    role,
  });
}

async function loginRequest({ email, password }) {
  return postJson("/auth/login", {
    email,
    password,
  });
}

async function loadOverviewMetrics() {
  if (!metricAvgEarnings || !metricReviewHours || !metricApprovedToday) return;
  try {
    const response = await fetch(`${API_BASE_URL}/metrics/overview`);
    if (!response.ok) throw new Error("Metrics unavailable");
    const data = await response.json();
    metricAvgEarnings.textContent = `$${Number(data.todayAverageEarnings || 0).toFixed(2)}`;
    metricReviewHours.textContent = `${Number(data.averageReviewHours || 0).toFixed(1)}h`;
    metricApprovedToday.textContent = String(Number(data.tasksApprovedToday || 0));
  } catch {
    metricAvgEarnings.textContent = "$0.00";
    metricReviewHours.textContent = "0.0h";
    metricApprovedToday.textContent = "0";
  }
}

function nextRouteForRole(session) {
  if (session.role === "admin") {
    return "./dashboard.html";
  }
  if (session.role === "contributor") {
    return session.profileCompleted ? "./tasks.html" : "./onboarding.html";
  }
  if (session.role === "startup") {
    return session.profileCompleted ? "./dashboard.html" : "./startup-onboarding.html";
  }
  return session.profileCompleted ? "./dashboard.html" : "./onboarding.html";
}

function setupRouteForRole(role) {
  if (role === "admin") return "./dashboard.html";
  return role === "startup" ? "./startup-onboarding.html" : "./onboarding.html";
}

function openModal(defaultRole = "contributor") {
  activeRole = defaultRole;
  authRoleLabel.textContent =
    defaultRole === "startup"
      ? "Continue as startup founder."
      : defaultRole === "admin"
        ? "Continue as admin supervisor."
        : "Continue as freelance contributor.";
  updateAuthFormMode();
  hideAuthFeedback();
  authModal.classList.remove("hidden");
  authModal.setAttribute("aria-hidden", "false");
}

function closeModal() {
  authModal.classList.add("hidden");
  authModal.setAttribute("aria-hidden", "true");
  hideAuthFeedback();
}

function renderNavbar() {
  const session = loadSession();
  if (!session || !session.isAuthenticated) {
    const opsButton = isOpsAccess ? `<button class="btn btn-primary" id="nav-signin-admin">Ops access</button>` : "";
    navbarRight.innerHTML = `
      <button class="btn btn-ghost" id="nav-signin-contributor">Sign in</button>
      <button class="btn btn-ghost" id="nav-signin-startup">Startup access</button>
      ${opsButton}
    `;
    document
      .getElementById("nav-signin-contributor")
      .addEventListener("click", () => openModal("contributor"));
    document.getElementById("nav-signin-startup").addEventListener("click", () => openModal("startup"));
    if (isOpsAccess) {
      document
        .getElementById("nav-signin-admin")
        .addEventListener("click", () => openModal("admin"));
    }
    return;
  }

  if (!session.profileCompleted) {
    const setupRoute = setupRouteForRole(session.role);
    navbarRight.innerHTML = `
      <span class="chip">Complete setup to unlock workspace</span>
      <a class="btn btn-primary" href="${setupRoute}">Continue setup</a>
      <button class="btn btn-ghost" id="logout-btn">Logout</button>
      <a class="btn btn-ghost user-profile-btn" href="${setupRoute}" title="Open your profile">
        <img class="user-icon-img" src="./icon-user.svg" alt="" />
        Profile
      </a>
    `;
    document.getElementById("logout-btn").addEventListener("click", async () => {
      await logoutRequest();
      clearSession();
      renderNavbar();
    });
    return;
  }

  const tasksLink = session.role === "contributor" ? `<a class="btn btn-ghost" href="./tasks.html">Tasks</a>` : "";
  navbarRight.innerHTML = `
    ${tasksLink}
    <a class="btn btn-ghost" href="./dashboard.html">Dashboard</a>
    <button class="btn btn-ghost" id="logout-btn">Logout</button>
    <span class="chip"><img class="money-icon-img" src="./icon-wallet.svg" alt="" /> Balance: $${Number(session.balance).toFixed(2)}</span>
    <a class="btn btn-ghost user-profile-btn" href="./dashboard.html" title="Open your profile">
      <img class="user-icon-img" src="./icon-user.svg" alt="" />
      Profile
    </a>
  `;

  document.getElementById("logout-btn").addEventListener("click", async () => {
    await logoutRequest();
    clearSession();
    renderNavbar();
  });
}

function setBrandLinkTarget() {
  const session = loadSession();
  if (!session) {
    brandLink.href = "./index.html";
    return;
  }
  if (!session.profileCompleted) {
    brandLink.href = setupRouteForRole(session.role);
    return;
  }
  const lastPage = sessionStorage.getItem(LAST_PAGE_KEY);
  brandLink.href = lastPage || (session.role === "contributor" ? "./tasks.html" : "./dashboard.html");
}

function updateAuthFormMode() {
  const submitBtn = authForm.querySelector("button[type='submit']");
  const isSignup = authMode === "signup";
  nameInput.required = isSignup;
  nameInput.parentElement.classList.toggle("hidden", !isSignup);
  submitBtn.textContent = isSignup ? "Create account" : "Sign in";
  authModeLoginBtn.classList.toggle("active", !isSignup);
  authModeSignupBtn.classList.toggle("active", isSignup);
  authModeLoginBtn.setAttribute("aria-selected", String(!isSignup));
  authModeSignupBtn.setAttribute("aria-selected", String(isSignup));
}

function showAuthFeedback(message) {
  authFeedback.textContent = message;
  authFeedback.classList.remove("hidden");
}

function hideAuthFeedback() {
  authFeedback.textContent = "";
  authFeedback.classList.add("hidden");
}

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideAuthFeedback();
  const action = authMode;
  const fullName = nameInput.value.trim();
  const email = emailInput.value.trim();
  const password = passwordInput.value;
  const users = loadUsersDb();
  const existing = users.find((item) => item.email.toLowerCase() === email.toLowerCase());

  try {
    let authData;
    if (action === "signup") {
      if (fullName.length < 2) {
        showAuthFeedback("Please enter your full name (minimum 2 characters).");
        return;
      }
      authData = await signupRequest({
        fullName,
        email,
        password,
        role: activeRole,
      });
      await trackEvent({ role: activeRole }, "signup_completed", { accessPath: activeRole });
    } else {
      authData = await loginRequest({
        email,
        password,
      });
      if (authData.role !== activeRole) {
        showAuthFeedback(
          `This account is registered as ${roleLabel(authData.role)}. Please use ${roleLabel(authData.role)} access.`
        );
        return;
      }
      await trackEvent({ userId: authData.userId, role: authData.role }, "login_success", { accessPath: activeRole });
    }

    const session = {
      isAuthenticated: true,
      userId: authData.userId,
      fullName: authData.fullName,
      email: authData.email,
      role: authData.role,
      balance: 0,
      profileCompleted: Boolean(authData.profileCompleted ?? existing?.profileCompleted),
    };
    setAuthToken(authData.token || "");

    saveSession(session);
    recordUserActivity(session);
    closeModal();
    renderNavbar();
    window.location.href = nextRouteForRole(session);
  } catch (error) {
    if (action === "login") {
      await trackEvent({ role: activeRole }, "login_failed", { accessPath: activeRole });
    }
    showAuthFeedback(parseApiError(error, "Authentication failed. Make sure backend API is running."));
  }
});

contributorBtn.addEventListener("click", () => {
  trackEvent({ role: "contributor" }, "cta_contributor_clicked");
  openModal("contributor");
});
startupBtn.addEventListener("click", () => {
  trackEvent({ role: "startup" }, "cta_startup_clicked");
  openModal("startup");
});
closeModalBtn.addEventListener("click", closeModal);
authModeLoginBtn.addEventListener("click", () => {
  authMode = "login";
  updateAuthFormMode();
});
authModeSignupBtn.addEventListener("click", () => {
  authMode = "signup";
  updateAuthFormMode();
});

authModal.addEventListener("mousedown", (event) => {
  authModalPointerDownOnBackdrop = event.target === authModal;
});

authModal.addEventListener("mouseup", (event) => {
  const shouldClose = authModalPointerDownOnBackdrop && event.target === authModal;
  authModalPointerDownOnBackdrop = false;
  if (shouldClose) closeModal();
});

document.getElementById("footer-signup-link")?.addEventListener("click", (event) => {
  event.preventDefault();
  authMode = "signup";
  updateAuthFormMode();
  openModal("contributor");
});

document.getElementById("footer-login-link")?.addEventListener("click", (event) => {
  event.preventDefault();
  authMode = "login";
  updateAuthFormMode();
  openModal("contributor");
});

const bootstrapSession = loadSession();
if (bootstrapSession?.isAuthenticated && !bootstrapSession.profileCompleted) {
  window.location.href = setupRouteForRole(bootstrapSession.role);
} else {
  renderNavbar();
  sessionStorage.setItem(LAST_PAGE_KEY, "./index.html");
  setBrandLinkTarget();
  updateAuthFormMode();
  loadOverviewMetrics();
}
