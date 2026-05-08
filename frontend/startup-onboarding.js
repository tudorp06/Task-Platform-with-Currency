const SESSION_KEY = "app_contributor_session";
const AUTH_TOKEN_KEY = "app_contributor_auth_token";
const API_BASE_URL = "http://127.0.0.1:8000/api";

const navbarRight = document.getElementById("navbar-right");
const form = document.getElementById("startup-onboarding-form");
const feedback = document.getElementById("startup-onboarding-feedback");
const brandLink = document.getElementById("brand-link");
const companyNameInput = document.getElementById("startup-company-name");
const websiteInput = document.getElementById("startup-website-url");
const industryInput = document.getElementById("startup-industry");
const productStageInput = document.getElementById("startup-product-stage");
const techStackInput = document.getElementById("startup-tech-stack");
const teamSizeInput = document.getElementById("startup-team-size");
const squadSummaryInput = document.getElementById("startup-squad-summary");
const intentionsInput = document.getElementById("startup-intentions");

function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveSession(session) {
  const { authToken, ...safeSession } = session || {};
  localStorage.setItem(SESSION_KEY, JSON.stringify(safeSession));
}

function showFeedback(message) {
  feedback.textContent = message;
  feedback.classList.remove("hidden");
}

function hideFeedback() {
  feedback.textContent = "";
  feedback.classList.add("hidden");
}

function renderNavbar(session) {
  navbarRight.innerHTML = `<span class="chip">Signed in: ${session.fullName}</span>`;
}

function readCookie(name) {
  const target = `${name}=`;
  const cookie = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(target));
  return cookie ? decodeURIComponent(cookie.slice(target.length)) : "";
}

async function registerStartup(payload) {
  const token = sessionStorage.getItem(AUTH_TOKEN_KEY) || "";
  const csrfToken = readCookie("appcontributor_csrf");
  const response = await fetch(`${API_BASE_URL}/startups/register`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.detail || "Startup registration failed");
  }
  return body;
}

const session = loadSession();
if (!session) {
  window.location.href = "./index.html";
} else if (session.role !== "startup") {
  window.location.href = session.role === "contributor" ? "./onboarding.html" : "./dashboard.html";
} else if (session.profileCompleted) {
  window.location.href = "./dashboard.html";
} else {
  renderNavbar(session);
  if (brandLink) brandLink.href = "./startup-onboarding.html";
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFeedback();
  const currentSession = loadSession();
  if (!currentSession?.isAuthenticated) {
    showFeedback("Session expired. Please sign in again.");
    return;
  }

  try {
    await registerStartup({
      companyName: companyNameInput.value.trim(),
      websiteUrl: websiteInput.value.trim(),
      industry: industryInput.value.trim(),
      productStage: productStageInput.value.trim(),
      techStack: techStackInput.value.trim(),
      teamSize: Number.parseInt(teamSizeInput.value, 10),
      squadSummary: squadSummaryInput.value.trim(),
      intentions: intentionsInput.value.trim(),
    });
    currentSession.profileCompleted = true;
    saveSession(currentSession);
    window.location.href = "./dashboard.html";
  } catch (error) {
    showFeedback(error?.message || "Could not submit startup registration.");
  }
});
