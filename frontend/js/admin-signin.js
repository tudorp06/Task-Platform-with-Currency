const SESSION_KEY = "app_contributor_session";
const AUTH_TOKEN_KEY = "app_contributor_auth_token";
const USERS_DB_KEY = "app_contributor_users_db";
const API_BASE_URL = (() => {
  const configured = String(window.__APP_API_BASE_URL__ || "").trim();
  const base = configured || "https://appcontributor-backend.onrender.com/api";
  const normalized = base.replace(/\/+$/, "");
  return normalized.endsWith("/api") ? normalized : `${normalized}/api`;
})();

const form = document.getElementById("admin-auth-form");
const feedback = document.getElementById("admin-auth-feedback");
const modeLoginBtn = document.getElementById("admin-mode-login");
const modeSignupBtn = document.getElementById("admin-mode-signup");
const nameLabel = document.getElementById("admin-name-label");
const codeLabel = document.getElementById("admin-code-label");
const nameInput = document.getElementById("admin-input-name");
const codeInput = document.getElementById("admin-input-code");
const emailInput = document.getElementById("admin-input-email");
const passwordInput = document.getElementById("admin-input-password");
const submitBtn = document.getElementById("admin-submit-btn");

let authMode = "login";

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

function setAuthToken(token) {
  if (!token) return;
  sessionStorage.setItem(AUTH_TOKEN_KEY, token);
}

function loadUsersDb() {
  return loadJson(USERS_DB_KEY, []);
}

function readCookie(name) {
  const target = `${name}=`;
  const cookie = document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(target));
  return cookie ? decodeURIComponent(cookie.slice(target.length)) : "";
}

function showFeedback(message) {
  feedback.textContent = message;
  feedback.classList.remove("hidden");
}

function hideFeedback() {
  feedback.textContent = "";
  feedback.classList.add("hidden");
}

function updateFormMode() {
  const isSignup = authMode === "signup";
  nameLabel.classList.toggle("hidden", !isSignup);
  codeLabel.classList.toggle("hidden", !isSignup);
  nameInput.required = isSignup;
  codeInput.required = isSignup;
  submitBtn.textContent = isSignup ? "Create account" : "Sign in";
  modeLoginBtn.classList.toggle("active", !isSignup);
  modeSignupBtn.classList.toggle("active", isSignup);
  modeLoginBtn.setAttribute("aria-selected", String(!isSignup));
  modeSignupBtn.setAttribute("aria-selected", String(isSignup));
}

async function postJson(path, payload) {
  const csrfToken = readCookie("appcontributor_csrf");
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("Could not reach backend API. Check APP_API_BASE_URL and backend CORS/cookie settings.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.detail || "Request failed");
  }
  return body;
}

async function signupAdmin({ fullName, email, password, adminCode }) {
  return postJson("/auth/signup", {
    fullName,
    email,
    password,
    role: "admin",
    adminCode,
  });
}

async function loginRequest({ email, password }) {
  return postJson("/auth/login", { email, password });
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
  saveJson(USERS_DB_KEY, users);
}

modeLoginBtn.addEventListener("click", () => {
  authMode = "login";
  updateFormMode();
  hideFeedback();
});

modeSignupBtn.addEventListener("click", () => {
  authMode = "signup";
  updateFormMode();
  hideFeedback();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();
  const email = emailInput.value.trim();
  const password = passwordInput.value;
  const users = loadUsersDb();
  const existing = users.find((item) => item.email.toLowerCase() === email.toLowerCase());

  try {
    let authData;
    if (authMode === "signup") {
      const fullName = nameInput.value.trim();
      if (fullName.length < 2) {
        showFeedback("Please enter your full name (minimum 2 characters).");
        return;
      }
      const adminCode = codeInput.value.trim();
      if (!adminCode) {
        showFeedback("Invite code is required for admin account creation.");
        return;
      }
      authData = await signupAdmin({ fullName, email, password, adminCode });
    } else {
      authData = await loginRequest({ email, password });
      if (authData.role !== "admin") {
        showFeedback("This page is for administrator accounts only. Use the main site for contributor or startup login.");
        return;
      }
    }

    if (authData.role !== "admin") {
      showFeedback("Administrator role was not granted. Check invite code and server settings.");
      return;
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
    window.location.href = "/views/dashboard.html";
  } catch (err) {
    showFeedback(err?.message || "Authentication failed.");
  }
});

const existing = loadSession();
if (existing?.isAuthenticated && existing.role === "admin") {
  window.location.href = "/views/dashboard.html";
} else {
  updateFormMode();
}

