const SESSION_KEY = "app_contributor_session";
const USERS_DB_KEY = "app_contributor_users_db";
const AUTH_TOKEN_KEY = "app_contributor_auth_token";
const API_BASE_URL = (() => {
  const configured = String(window.__APP_API_BASE_URL__ || "").trim();
  const base = configured || "https://appcontributor-backend.onrender.com/api";
  const normalized = base.replace(/\/+$/, "");
  return normalized.endsWith("/api") ? normalized : `${normalized}/api`;
})();

const navbarRight = document.getElementById("navbar-right");
const onboardingForm = document.getElementById("onboarding-form");
const countryInput = document.getElementById("country-input");
const qualificationInput = document.getElementById("qualification-input");
const experienceInput = document.getElementById("experience-input");
const skillsInput = document.getElementById("skills-input");
const githubInput = document.getElementById("github-input");
const bioInput = document.getElementById("bio-input");
const sortingAnswerInput = document.getElementById("sorting-answer-input");

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

function loadUsersDb() {
  return loadJson(USERS_DB_KEY, []);
}

function saveUsersDb(items) {
  saveJson(USERS_DB_KEY, items);
}

function readCookie(name) {
  const target = `${name}=`;
  const cookie = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(target));
  return cookie ? decodeURIComponent(cookie.slice(target.length)) : "";
}

async function markProfileCompleted() {
  const token = sessionStorage.getItem(AUTH_TOKEN_KEY) || "";
  const csrfToken = readCookie("appcontributor_csrf");
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/auth/profile-complete`, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      },
      body: JSON.stringify({ profileCompleted: true }),
    });
  } catch (error) {
    throw new Error(
      "Could not reach backend API. Check Netlify APP_API_BASE_URL and backend CORS/cookie settings."
    );
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.detail || "Could not save profile completion state.");
  }
  return body;
}

function normalizeSortingAnswer(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .join(",");
}

function renderNavbar(session) {
  navbarRight.innerHTML = `
    <span class="chip">Signed in: ${session.fullName}</span>
  `;
}

const session = loadSession();
if (!session) {
  window.location.href = "./index.html";
} else if (session.profileCompleted) {
  window.location.href = session.role === "contributor" ? "./tasks.html" : "./dashboard.html";
} else if (session.role === "startup") {
  window.location.href = "./startup-onboarding.html";
} else {
  renderNavbar(session);
}

onboardingForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const country = countryInput.value.trim();
  const qualification = qualificationInput.value.trim();
  const yearsOfExperience = Number.parseInt(experienceInput.value, 10);
  const skills = skillsInput.value
    .split(",")
    .map((skill) => skill.trim())
    .filter(Boolean);
  const githubUrl = githubInput.value.trim();
  const bio = bioInput.value.trim();
  const sortingAnswer = normalizeSortingAnswer(sortingAnswerInput.value);
  const sortingChallengePassed = sortingAnswer === "1,3,5,7,9";

  if (!country || !qualification || !Number.isFinite(yearsOfExperience) || yearsOfExperience < 0 || skills.length === 0) {
    alert("Please complete all required profile fields.");
    return;
  }
  if (!githubUrl.startsWith("http://") && !githubUrl.startsWith("https://")) {
    alert("Please enter a valid GitHub URL.");
    return;
  }

  const users = loadUsersDb();
  const user = users.find((item) => item.id === session.userId || item.email === session.email);
  if (!user) {
    alert("Could not find your account. Please sign in again.");
    window.location.href = "./index.html";
    return;
  }

  user.country = country;
  user.qualification = qualification;
  user.yearsOfExperience = yearsOfExperience;
  user.skills = skills;
  user.githubUrl = githubUrl;
  user.bio = bio;
  user.sortingChallengePassed = sortingChallengePassed;
  user.profileCompleted = true;
  user.updatedAt = new Date().toISOString();
  saveUsersDb(users);

  session.profileCompleted = true;
  session.fullName = user.fullName || session.fullName;

  try {
    const auth = await markProfileCompleted();
    session.profileCompleted = Boolean(auth.profileCompleted);
  } catch (error) {
    alert(error?.message || "Profile saved locally, but backend sync failed. Please retry.");
    return;
  }
  saveSession(session);

  if (!sortingChallengePassed) {
    alert("Profile saved. Your sorting answer was not fully correct, but you can still continue and improve later.");
  }
  window.location.href = session.role === "contributor" ? "./tasks.html" : "./dashboard.html";
});
