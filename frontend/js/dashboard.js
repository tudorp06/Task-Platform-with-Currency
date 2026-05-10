const SESSION_KEY = "app_contributor_session";
const AUTH_TOKEN_KEY = "app_contributor_auth_token";
const USERS_DB_KEY = "app_contributor_users_db";
const SUBMISSIONS_DB_KEY = "app_contributor_submissions_db";
const TASKS_DB_KEY = "app_contributor_tasks_db";
const LAST_PAGE_KEY = "app_contributor_last_page";
const TASK_SHORTLIST_KEY = "app_contributor_task_shortlist";
const PAYOUT_METHODS_DB_KEY = "app_contributor_payout_methods_db";
const PAYOUT_REQUESTS_DB_KEY = "app_contributor_payout_requests_db";
const BALANCES_DB_KEY = "app_contributor_balances_db";
const RECEIPTS_DB_KEY = "app_contributor_receipts_db";
const API_BASE_URL = (() => {
  const configured = String(window.__APP_API_BASE_URL__ || "").trim();
  const base = configured || "https://appcontributor-backend.onrender.com/api";
  const normalized = base.replace(/\/+$/, "");
  return normalized.endsWith("/api") ? normalized : `${normalized}/api`;
})();

const navbarRight = document.getElementById("navbar-right");
const dashboardList = document.getElementById("dashboard-list");
const contributorSection = document.getElementById("contributor-section");
const adminSection = document.getElementById("admin-section");
const adminTaskList = document.getElementById("admin-task-list");
const adminAnalyticsOverview = document.getElementById("admin-analytics-overview");
const adminPayoutList = document.getElementById("admin-payout-list");
const adminSubmissionList = document.getElementById("admin-submission-list");
const adminDisputeList = document.getElementById("admin-dispute-list");
const adminStartupList = document.getElementById("admin-startup-list");
const adminStartupTaskRequestList = document.getElementById("admin-startup-task-request-list");
const adminUserList = document.getElementById("admin-user-list");
const adminTaskCreateForm = document.getElementById("admin-task-create-form");
const adminTaskIdInput = document.getElementById("admin-task-id");
const adminTaskTitleInput = document.getElementById("admin-task-title");
const adminTaskLanguageInput = document.getElementById("admin-task-language");
const adminTaskRewardInput = document.getElementById("admin-task-reward");
const adminTaskStatusInput = document.getElementById("admin-task-status");
const adminTaskStartupInput = document.getElementById("admin-task-startup");
const adminTaskSummaryInput = document.getElementById("admin-task-summary");
const adminTaskDescriptionInput = document.getElementById("admin-task-description");
const adminTaskEndpointsInput = document.getElementById("admin-task-endpoints");
const adminTaskLayoutInput = document.getElementById("admin-task-layout");
const adminTaskRunInput = document.getElementById("admin-task-run");
const adminTaskCreateFeedback = document.getElementById("admin-task-create-feedback");
const adminUserSaveFeedback = document.getElementById("admin-user-save-feedback");
const startupSection = document.getElementById("startup-section");
const startupStatusCard = document.getElementById("startup-status-card");
const startupTaskRequestForm = document.getElementById("startup-task-request-form");
const startupTaskRequestList = document.getElementById("startup-task-request-list");
const startupSubmissionFeedbackList = document.getElementById("startup-submission-feedback-list");
const startupTaskDeletionRequestList = document.getElementById("startup-task-deletion-request-list");
const startupTaskTitle = document.getElementById("startup-task-title");
const startupTaskLanguage = document.getElementById("startup-task-language");
const startupTaskReward = document.getElementById("startup-task-reward");
const startupTaskDetails = document.getElementById("startup-task-details");
const startupTaskRules = document.getElementById("startup-task-rules");
const startupTaskPublishHint = document.getElementById("startup-task-publish-hint");
const userProfileCard = document.getElementById("user-profile-card");
const shortlistList = document.getElementById("shortlist-list");
const walletSummary = document.getElementById("wallet-summary");
const paymentMethodForm = document.getElementById("payment-method-form");
const paymentMethodType = document.getElementById("payment-method-type");
const paypalEmailWrap = document.getElementById("paypal-email-wrap");
const cardNumberWrap = document.getElementById("card-number-wrap");
const cardNameWrap = document.getElementById("card-name-wrap");
const cardEmailWrap = document.getElementById("card-email-wrap");
const paypalEmailInput = document.getElementById("paypal-email-input");
const stripeCardElementHost = document.getElementById("stripe-card-element");
const stripeCardError = document.getElementById("stripe-card-error");
const cardNameInput = document.getElementById("card-name-input");
const cardEmailInput = document.getElementById("card-email-input");
const paymentMethodList = document.getElementById("payment-method-list");
const payoutRequestForm = document.getElementById("payout-request-form");
const payoutAmountInput = document.getElementById("payout-amount-input");
const payoutMethodSelect = document.getElementById("payout-method-select");
const payoutRequestList = document.getElementById("payout-request-list");
const receiptList = document.getElementById("receipt-list");
let contributorPaymentMethods = [];
const adminUserCollapsed = new Set();

function showActionFeedback(element, message, isError = false) {
  if (!element) return;
  element.textContent = message;
  element.classList.remove("hidden", "error");
  if (isError) element.classList.add("error");
  window.setTimeout(() => {
    element.classList.add("hidden");
    element.classList.remove("error");
  }, 2600);
}
let stripeClient = null;
let stripeElements = null;
let stripeCardElement = null;
let stripeMountAttempted = false;
const REJECTION_REASONS = [
  "100% AI code",
  "A lot of syntax error, code is written too fast and chaotically",
  "Does not respect original file syntax and layout -> Isn't relevant",
  "No clear reasoning path, hard to review technical intent",
  "Patch solves a different issue than the startup reported",
  "Not reproducible from the provided context/endpoints",
];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatAttachmentSize(bytes) {
  const value = Number(bytes || 0);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function renderSubmissionAttachments(attachments = [], submissionId = null) {
  if (!Array.isArray(attachments) || attachments.length === 0) return "";
  return `<details class="review-details">
    <summary>Attachments (${attachments.length})</summary>
    <div class="submission-attachments-list">
      ${attachments
        .map(
          (file) => `<div class="submission-attachment-item">
          <span>${escapeHtml(file.fileName || "Attachment")} â€¢ ${formatAttachmentSize(file.sizeBytes)}</span>
          <button type="button" class="btn btn-ghost submission-download-btn" data-attachment-id="${Number(file.id || 0)}" ${
            submissionId ? `data-submission-id="${submissionId}"` : ""
          }>Download</button>
        </div>`
        )
        .join("")}
    </div>
  </details>`;
}

async function downloadSubmissionAttachment(session, attachmentId, fallbackName = "attachment.bin") {
  const token = sessionStorage.getItem(AUTH_TOKEN_KEY) || "";
  const response = await fetch(`${API_BASE_URL}/submissions/attachments/${attachmentId}/download`, {
    method: "GET",
    credentials: "include",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || "Could not download attachment");
  }
  const blob = await response.blob();
  const tempUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = tempUrl;
  anchor.download = fallbackName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(tempUrl);
}

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function showStripeCardError(message) {
  if (!stripeCardError) return;
  if (!message) {
    stripeCardError.textContent = "";
    stripeCardError.classList.add("hidden");
    return;
  }
  stripeCardError.textContent = message;
  stripeCardError.classList.remove("hidden");
}

function saveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function loadSession() {
  return loadJson(SESSION_KEY, null);
}

function loadUsersDb() {
  return loadJson(USERS_DB_KEY, []);
}

function saveUsersDb(items) {
  saveJson(USERS_DB_KEY, items);
}

function setUserAvatar(userId, email, avatarDataUrl) {
  const users = loadUsersDb();
  const user = users.find((item) => item.id === userId || item.email === email);
  if (!user) return;
  user.avatarDataUrl = avatarDataUrl;
  user.updatedAt = new Date().toISOString();
  saveUsersDb(users);
}

function saveSession(session) {
  const { authToken, ...safeSession } = session || {};
  saveJson(SESSION_KEY, safeSession);
}

function getCurrentUserRecord(session) {
  const users = loadUsersDb();
  return users.find((item) => item.id === session.userId || item.email === session.email) || null;
}

function renderNavbar(session) {
  const tasksLink = session.role === "contributor" ? `<a class="btn btn-ghost" href="/views/tasks.html">Tasks</a>` : "";
  navbarRight.innerHTML = `
    ${tasksLink}
    <a class="btn btn-ghost" href="/views/dashboard.html">Dashboard</a>
    <button class="btn btn-ghost" id="logout-btn">Logout</button>
    <span class="chip"><img class="money-icon-img" src="/assets/icons/icon-wallet.svg" alt="" /> Balance: $${Number(session.balance).toFixed(2)}</span>
    <a class="btn btn-ghost user-profile-btn" href="/views/dashboard.html" title="Open your profile">
      <img class="user-icon-img" src="/assets/icons/icon-user.svg" alt="" />
      Profile
    </a>
  `;
  document.getElementById("logout-btn").addEventListener("click", async () => {
    try {
      const csrfToken = readCookie("appcontributor_csrf");
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
      });
    } catch {
      // ignore logout transport errors
    }
    localStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
    window.location.href = "/index.html";
  });
}

function loadBalances() {
  return loadJson(BALANCES_DB_KEY, {});
}

function getBalanceForUser(userId) {
  const balances = loadBalances();
  return Number(balances[String(userId)] || 0);
}

function setBalanceForUser(userId, amount) {
  const balances = loadBalances();
  balances[String(userId)] = Number(amount.toFixed(2));
  saveJson(BALANCES_DB_KEY, balances);
}

function loadPayoutMethods() {
  return loadJson(PAYOUT_METHODS_DB_KEY, []);
}

function savePayoutMethods(items) {
  saveJson(PAYOUT_METHODS_DB_KEY, items);
}

function loadPayoutRequests() {
  return loadJson(PAYOUT_REQUESTS_DB_KEY, []);
}

function savePayoutRequests(items) {
  saveJson(PAYOUT_REQUESTS_DB_KEY, items);
}

function loadReceipts() {
  return loadJson(RECEIPTS_DB_KEY, []);
}

function saveReceipts(items) {
  saveJson(RECEIPTS_DB_KEY, items);
}

function setBrandLinkTarget(_session) {
  // Navbar brand is display-only (logo + title), not a link.
}

function readCookie(name) {
  const target = `${name}=`;
  const cookie = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(target));
  return cookie ? decodeURIComponent(cookie.slice(target.length)) : "";
}

async function authedJson(path, session, method = "GET", payload = null) {
  const token = sessionStorage.getItem(AUTH_TOKEN_KEY) || "";
  const csrfToken = readCookie("appcontributor_csrf");
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
    ...(payload ? { body: JSON.stringify(payload) } : {}),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.detail || "Request failed");
  }
  return body;
}

async function trackEvent(session, event, metadata = {}) {
  const csrfToken = readCookie("appcontributor_csrf");
  try {
    await fetch(`${API_BASE_URL}/analytics/event`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
      body: JSON.stringify({
        event,
        source: "dashboard",
        userId: session?.userId ?? null,
        role: session?.role ?? null,
        metadata,
      }),
    });
  } catch {
    // Non-blocking analytics
  }
}

function statusClass(status) {
  return status === "rejected"
    ? "status-review"
    : status === "approved" || status === "partial_approved"
      ? "status-done"
      : "status-open";
}

function statusLabel(status) {
  if (status === "partial_approved") return "Partially Approved (50%)";
  return status.charAt(0).toUpperCase() + status.slice(1).replace("_", " ");
}

function formatTaskId(taskId) {
  const raw = String(taskId || "").trim();
  if (!raw) return "";
  if (raw.startsWith("PB-")) return `TASK-${raw.slice(3)}`;
  if (raw.startsWith("SR-")) return `TASK-${raw.slice(3)}`;
  return raw;
}

function payoutStatusClass(status) {
  return status === "paid" ? "status-done" : status === "rejected" ? "status-review" : "status-open";
}

function renderUserProfile(session) {
  if (!userProfileCard) return;
  const profile = getCurrentUserRecord(session);
  const initials = (session.fullName || "U")
    .split(" ")
    .map((chunk) => chunk[0] || "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const avatarImage = profile?.avatarDataUrl
    ? `<img class="profile-avatar-image" src="${escapeHtml(profile.avatarDataUrl)}" alt="${escapeHtml(session.fullName)} avatar" />`
    : `<span>${initials}</span>`;
  const skills = profile?.skills?.length ? profile.skills.join(", ") : "No skills added yet";
  userProfileCard.innerHTML = `
    <div class="profile-head">
      <div class="profile-avatar">${avatarImage}</div>
      <div>
        <h3>${session.fullName}</h3>
        <p>${session.email} â€¢ ${session.role}</p>
      </div>
    </div>
    <div class="profile-grid">
      <div><strong>Country</strong><p>${profile?.country || "Not set"}</p></div>
      <div><strong>Experience</strong><p>${profile?.yearsOfExperience ?? 0} years</p></div>
      <div><strong>Qualification</strong><p>${profile?.qualification || "Not set"}</p></div>
      <div><strong>GitHub</strong><p>${profile?.githubUrl || "Not set"}</p></div>
      <div><strong>Skills</strong><p>${skills}</p></div>
      <div><strong>Sorting check</strong><p>${profile?.sortingChallengePassed ? "Passed" : "Pending"}</p></div>
    </div>
    <p class="section-note" style="margin:8px 0 0;">${profile?.bio || "Add a short bio in onboarding."}</p>
    <div class="profile-avatar-actions">
      <label class="btn btn-ghost profile-avatar-upload" for="profile-avatar-input">Change profile picture</label>
      <input id="profile-avatar-input" type="file" accept="image/*" class="hidden" />
    </div>
  `;

  const profileAvatarInput = document.getElementById("profile-avatar-input");
  profileAvatarInput?.addEventListener("change", () => {
    const file = profileAvatarInput.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      alert("Please upload an image file.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      if (!result) return;
      setUserAvatar(session.userId, session.email, result);
      renderUserProfile(session);
    };
    reader.readAsDataURL(file);
  });
}

function syncApprovedEarnings(session) {
  const tasks = loadJson(TASKS_DB_KEY, []);
  const taskById = new Map(tasks.map((task) => [task.id, task]));
  const submissions = loadJson(SUBMISSIONS_DB_KEY, []);
  let added = 0;
  let changed = false;

  submissions.forEach((sub) => {
    if (sub.contributorId !== session.userId) return;
    if (!["approved", "partial_approved"].includes(sub.status)) return;
    if (sub.rewardCreditedAt) return;
    const taskReward = Number(taskById.get(sub.taskId)?.reward ?? 1);
    const payoutRate = sub.status === "partial_approved" ? Number(sub.payoutRate || 0.5) : 1;
    added += (Number.isFinite(taskReward) ? taskReward : 1) * payoutRate;
    sub.rewardCreditedAt = new Date().toISOString();
    changed = true;
  });

  if (changed) {
    saveJson(SUBMISSIONS_DB_KEY, submissions);
  }

  const current = Math.max(0, getBalanceForUser(session.userId));
  const next = current + added;
  setBalanceForUser(session.userId, next);
  session.balance = next;
  saveSession(session);
}

function renderDashboard(session) {
  const tasks = loadJson(TASKS_DB_KEY, []);
  const taskById = new Map(tasks.map((t) => [t.id, t]));
  const submissions = loadJson(SUBMISSIONS_DB_KEY, []).filter(
    (item) => item.contributorId === session.userId
  );

  dashboardList.innerHTML =
    submissions.length === 0
      ? "<p>No completed tasks yet.</p>"
      : submissions
          .map((sub) => {
            const task = taskById.get(sub.taskId);
            const originalReward = Number(task?.reward ?? sub.taskReward ?? 0);
            const disputeAction =
              sub.status === "rejected" && !sub.dispute
                ? `<button class="btn btn-ghost open-dispute-btn" data-submission-id="${sub.id}">Open contest</button>`
                : sub.dispute
                  ? `<span class="chip">Contest: ${sub.dispute}</span>`
                  : "";
            const reviewFeedback = sub.status === "rejected"
              ? `<div class="review-feedback critical">
                   <p class="review-line"><strong>Reason:</strong> ${sub.rejectionReason || "Not specified"}</p>
                   <p class="review-line"><strong>AI confidence:</strong> ${typeof sub.aiDetectionConfidence === "number" ? `${sub.aiDetectionConfidence}%` : "N/A"}</p>
                   <p class="review-line"><strong>Reviewer note:</strong> ${sub.reviewNote || "No extra note"}</p>
                 </div>`
              : sub.status === "partial_approved"
                ? `<div class="review-feedback positive">
                     <p class="review-line"><strong>Partial win:</strong> ${(Number(sub.payoutRate || 0.5) * 100).toFixed(0)}% payout approved</p>
                     <p class="review-line"><strong>AI confidence:</strong> ${typeof sub.aiDetectionConfidence === "number" ? `${sub.aiDetectionConfidence}%` : "N/A"}</p>
                     <p class="review-line"><strong>Reviewer note:</strong> ${sub.reviewNote || "Solid direction, continue improving the patch."}</p>
                   </div>`
                : "";
            const disputeFeedback = sub.dispute
              ? `<div class="review-feedback ${sub.dispute === "rejected" ? "critical" : "positive"}">
                   <p class="review-line"><strong>Contest:</strong> ${statusLabel(sub.dispute)}</p>
                   <p class="review-line"><strong>Your claim:</strong> ${sub.disputeReason || "No details provided"}</p>
                   ${sub.disputeAdminNote ? `<p class="review-line"><strong>Admin response:</strong> ${sub.disputeAdminNote}</p>` : ""}
                 </div>`
              : "";
            return `
      <div class="admin-item">
        <div>
          <strong>${task ? task.title : formatTaskId(sub.taskId)}</strong><br />
          <span>${formatTaskId(sub.taskId)} â€¢ Reward at submission: $${originalReward.toFixed(2)} â€¢ ${new Date(sub.submittedAt).toLocaleString()}</span>
          ${reviewFeedback}
          ${disputeFeedback}
        </div>
        <div>
          <span class="status-pill ${statusClass(sub.status)}">${statusLabel(sub.status)}</span>
          ${disputeAction}
        </div>
      </div>`;
          })
          .join("");

  document.querySelectorAll(".open-dispute-btn").forEach((button) => {
    button.addEventListener("click", () => openDispute(button.dataset.submissionId));
  });

  renderShortlistedTasks(session);
}

async function renderShortlistedTasks(session) {
  if (!shortlistList) return;
  let shortlistIds = [];
  try {
    const raw = localStorage.getItem(TASK_SHORTLIST_KEY) || sessionStorage.getItem(TASK_SHORTLIST_KEY) || "[]";
    const parsed = JSON.parse(raw);
    shortlistIds = Array.isArray(parsed) ? parsed : [];
  } catch {
    shortlistIds = [];
  }

  if (!shortlistIds.length) {
    shortlistList.innerHTML = `<div class="admin-item"><span>No shortlisted tasks yet. Use "Shortlist" in Task Marketplace.</span></div>`;
    return;
  }

  let tasks = [];
  try {
    const response = await fetch(`${API_BASE_URL}/tasks`);
    if (response.ok) {
      tasks = await response.json();
    }
  } catch {
    tasks = [];
  }
  if (!tasks.length) {
    tasks = loadJson(TASKS_DB_KEY, []);
  }
  const taskById = new Map(tasks.map((task) => [String(task.id), task]));
  const shortlisted = shortlistIds
    .map((id) => taskById.get(String(id)))
    .filter(Boolean);

  shortlistList.innerHTML =
    shortlisted.length === 0
      ? `<div class="admin-item"><span>Shortlisted tasks were not found in the current catalog.</span></div>`
      : shortlisted
          .map(
            (task) => `
      <div class="admin-item">
        <div>
          <strong>${escapeHtml(task.title || String(task.id))}</strong><br />
          <span>${escapeHtml(task.startup_name || "Startup App")} â€¢ Language: ${escapeHtml(task.language || "Set by startup")} â€¢ Reward: $${Number(task.reward || 0).toFixed(2)}</span>
        </div>
        <a class="btn btn-ghost" href="/views/tasks.html">Open in Tasks</a>
      </div>`
          )
          .join("");
}

function methodLabel(method) {
  if (method.methodType === "paypal") {
    return "PayPal";
  }
  return `${String(method.cardBrand || "Card").toUpperCase()}`;
}

function methodLogo(methodType) {
  return methodType === "paypal" ? "/assets/brand/logo-paypal.svg" : "/assets/brand/logo-visa.svg";
}

function methodDetails(method) {
  if (method.methodType === "paypal") return escapeHtml(method.billingEmail || "");
  const expSuffix = method.expMonth && method.expYear ? ` â€¢ ${String(method.expMonth).padStart(2, "0")}/${String(method.expYear).slice(-2)}` : "";
  return `â€¢â€¢â€¢â€¢ ${escapeHtml(method.cardLast4 || "")} (${escapeHtml(method.cardholderName || "")})${expSuffix}`;
}

async function renderWalletAndPayouts(session) {
  let methods = [];
  let myRequests = [];
  let myReceipts = [];
  try {
    methods = await authedJson("/payment-methods/me", session);
    myRequests = (await authedJson(`/payout-requests?user_id=${session.userId}`, session)).sort(
      (a, b) => new Date(b.createdAt) - new Date(a.createdAt)
    );
    myReceipts = (await authedJson(`/receipts?user_id=${session.userId}`, session)).sort(
      (a, b) => new Date(b.issuedAt) - new Date(a.issuedAt)
    );
  } catch (error) {
    methods = [];
    myRequests = [];
    myReceipts = [];
  }
  contributorPaymentMethods = methods;
  const currentBalance = getBalanceForUser(session.userId);
  session.balance = currentBalance;
  saveSession(session);
  renderNavbar(session);

  walletSummary.innerHTML = `
    <h3 style="margin: 0 0 8px;">
      Available balance: $${currentBalance.toFixed(2)}
    </h3>
    <p style="margin: 0;">Approved submissions increase your balance. Request payouts to your saved Visa/PayPal methods.</p>
  `;

  paymentMethodList.innerHTML =
    methods.length === 0
      ? `<div class="admin-item"><span>No payout methods yet.</span></div>`
      : methods
          .map(
            (method) => `
      <div class="admin-item">
        <div>
          <strong><img class="payment-logo" src="${methodLogo(method.methodType)}" alt="${methodLabel(method)} logo" /> ${methodLabel(method)} â€¢ ${methodDetails(method)}</strong><br />
          <span>Added ${new Date(method.createdAt).toLocaleString()}</span>
        </div>
        <button class="btn btn-ghost remove-method-btn" data-method-id="${method.id}">Remove</button>
      </div>`
          )
          .join("");

  payoutMethodSelect.innerHTML =
    methods.length === 0
      ? `<option value="">Add a method first</option>`
      : methods
          .map((method) => `<option value="${method.id}">${methodLabel(method)} â€¢ ${methodDetails(method)}</option>`)
          .join("");

  payoutRequestList.innerHTML =
    myRequests.length === 0
      ? `<div class="admin-item"><span>No payout requests yet.</span></div>`
      : myRequests
          .map(
            (item) => `
      <div class="admin-item">
        <div>
          <strong>$${Number(item.amount).toFixed(2)} â€¢ <img class="payment-logo" src="${item.provider === "paypal" ? "/assets/brand/logo-paypal.svg" : "/assets/brand/logo-visa.svg"}" alt="" /> ${item.provider}</strong><br />
          <span>${new Date(item.createdAt).toLocaleString()}</span>
        </div>
        <span class="status-pill ${payoutStatusClass(item.status)}">${statusLabel(item.status)}</span>
      </div>`
          )
          .join("");

  if (receiptList) {
    receiptList.innerHTML =
      myReceipts.length === 0
        ? `<div class="admin-item"><span>No receipts yet. Receipts appear after admin confirms payout.</span></div>`
        : myReceipts
            .map(
              (receipt) => `
      <div class="admin-item">
        <div>
          <strong>Receipt ${receipt.id} â€¢ $${Number(receipt.amount).toFixed(2)} â€¢ <img class="payment-logo" src="${receipt.provider === "paypal" ? "/assets/brand/logo-paypal.svg" : "/assets/brand/logo-visa.svg"}" alt="" /> ${receipt.provider}</strong><br />
          <span>Provider ref: ${receipt.providerReference} â€¢ Issued ${new Date(receipt.issuedAt).toLocaleString()}</span>
        </div>
        <span class="chip">Payout ${receipt.payoutRequestId}</span>
      </div>`
            )
            .join("");
  }

  document.querySelectorAll(".remove-method-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const methodId = Number(button.dataset.methodId || 0);
      const pendingUsingMethod = myRequests.some(
        (req) => String(req.destinationRef || "").includes(String(methodId)) && req.status === "pending"
      );
      if (pendingUsingMethod) {
        alert("You cannot remove a method while a payout is pending on it.");
        return;
      }
      try {
        await authedJson(`/payment-methods/${methodId}`, session, "DELETE");
        await renderWalletAndPayouts(session);
      } catch (error) {
        alert(error?.message || "Could not remove method.");
      }
    });
  });
}

function toggleMethodInputs() {
  const isPayPal = paymentMethodType.value === "paypal";
  paypalEmailWrap.classList.toggle("hidden", !isPayPal);
  cardNumberWrap.classList.toggle("hidden", isPayPal);
  cardNameWrap.classList.toggle("hidden", isPayPal);
  cardEmailWrap.classList.toggle("hidden", isPayPal);
  if (isPayPal) showStripeCardError("");
}

async function ensureStripeMounted(session) {
  if (stripeClient && stripeCardElement) return;
  if (!window.Stripe || !stripeCardElementHost) {
    throw new Error("Stripe is unavailable. Refresh and try again.");
  }
  const config = await authedJson("/payments/stripe-config", session);
  if (!config?.publishableKey) {
    throw new Error("Stripe publishable key is missing.");
  }
  stripeClient = window.Stripe(config.publishableKey);
  stripeElements = stripeClient.elements();
  stripeCardElement = stripeElements.create("card", {
    hidePostalCode: true,
    style: {
      base: {
        fontSize: "15px",
        color: "#18345a",
        fontFamily: "Manrope, Inter, Segoe UI, sans-serif",
        "::placeholder": { color: "#8aa0bf" },
      },
    },
  });
  stripeCardElement.mount("#stripe-card-element");
  showStripeCardError("");
  stripeMountAttempted = true;
}

function bindContributorFinanceHandlers(session) {
  paymentMethodType.addEventListener("change", () => {
    toggleMethodInputs();
    if (paymentMethodType.value === "card" && (!stripeClient || !stripeCardElement)) {
      ensureStripeMounted(session).catch((error) => {
        stripeMountAttempted = true;
        showStripeCardError(error?.message || "Card entry is unavailable right now.");
      });
    }
  });
  toggleMethodInputs();
  ensureStripeMounted(session).catch((error) => {
    stripeMountAttempted = true;
    showStripeCardError(error?.message || "Card entry is unavailable right now.");
  });

  paymentMethodForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const type = paymentMethodType.value;
    try {
      if (type === "paypal") {
        await authedJson("/payment-methods", session, "POST", {
          methodType: "paypal",
          paypalEmail: paypalEmailInput.value.trim().toLowerCase(),
        });
      } else {
        await ensureStripeMounted(session);
        if (!stripeClient || !stripeCardElement) {
          throw new Error(
            stripeMountAttempted
              ? "Stripe card form is unavailable. Check card setup configuration."
              : "Stripe card form is loading. Please retry in a moment."
          );
        }
        const setupIntent = await authedJson("/payments/stripe/setup-intent", session, "POST");
        const confirmation = await stripeClient.confirmCardSetup(setupIntent.clientSecret, {
          payment_method: {
            card: stripeCardElement,
            billing_details: {
              name: cardNameInput.value.trim(),
              email: cardEmailInput.value.trim().toLowerCase(),
            },
          },
        });
        if (confirmation.error) {
          throw new Error(confirmation.error.message || "Card verification failed.");
        }
        const stripePaymentMethodId = confirmation.setupIntent?.payment_method;
        if (!stripePaymentMethodId) {
          throw new Error("Stripe did not return a payment method id.");
        }
        await authedJson("/payment-methods", session, "POST", {
          methodType: "card",
          cardholderName: cardNameInput.value.trim(),
          billingEmail: cardEmailInput.value.trim().toLowerCase(),
          stripePaymentMethodId: String(stripePaymentMethodId),
        });
      }
      paymentMethodForm.reset();
      stripeCardElement?.clear();
      toggleMethodInputs();
      await renderWalletAndPayouts(session);
    } catch (error) {
      alert(error?.message || "Could not add payment method.");
    }
  });

  payoutRequestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const amount = Number.parseFloat(payoutAmountInput.value);
    const methodId = Number(payoutMethodSelect.value);
    const selectedMethod = contributorPaymentMethods.find((item) => Number(item.id) === methodId);
    if (!selectedMethod) {
      alert("Select a valid payout method.");
      return;
    }
    if (!Number.isFinite(amount) || amount < 1) {
      alert("Minimum payout amount is $1.00");
      return;
    }

    const currentBalance = getBalanceForUser(session.userId);
    if (amount > currentBalance) {
      alert("Insufficient balance for this payout.");
      return;
    }

    try {
      await authedJson("/payout-requests", session, "POST", {
        userId: session.userId,
        amount: Number(amount.toFixed(2)),
        provider: selectedMethod.provider === "paypal" ? "paypal" : "stripe",
        destinationRef: `${selectedMethod.providerToken}#${selectedMethod.id}`,
      });
      setBalanceForUser(session.userId, currentBalance - amount);
      payoutRequestForm.reset();
      await renderWalletAndPayouts(session);
    } catch (error) {
      alert(error?.message || "Could not create payout request.");
    }
  });
}

async function renderAdminTaskManager(session) {
  try {
    const tasks = await authedJson("/tasks", session);
    adminTaskList.innerHTML = tasks
      .map(
        (task) => `
      <div class="admin-item">
        <div>
          <strong>${escapeHtml(task.title)}</strong><br />
          <span>${formatTaskId(task.id)} â€¢ ${escapeHtml(task.type)} â€¢ Startup: ${escapeHtml(task.startup_name || "Startup App")}</span>
          <span class="review-note">${escapeHtml(task.summary || "")}</span>
          <span id="admin-task-feedback-${task.id}" class="review-note admin-inline-feedback hidden"></span>
        </div>
        <div class="review-controls">
          <input class="admin-task-title-input" data-task-id="${task.id}" value="${escapeHtml(task.title)}" placeholder="Title" />
          <input class="admin-task-language-input" data-task-id="${task.id}" value="${escapeHtml(task.type || "")}" placeholder="Language" />
          <input class="admin-task-status-input" data-task-id="${task.id}" value="${escapeHtml(task.status || "open")}" placeholder="Status" />
          <input class="admin-task-startup-input" data-task-id="${task.id}" value="${escapeHtml(task.startup_name || "")}" placeholder="Startup name" />
          <input class="admin-task-summary-input" data-task-id="${task.id}" value="${escapeHtml(task.summary || "")}" placeholder="Summary" />
          <input type="number" class="admin-task-reward-input" min="1" step="0.5" value="${Number(task.reward).toFixed(2)}" data-task-id="${task.id}" />
          <button class="btn btn-primary admin-task-save-btn" data-task-id="${task.id}">Save task</button>
          <button class="btn btn-ghost admin-task-delete-btn" data-task-id="${task.id}">Delete task</button>
        </div>
      </div>`
      )
      .join("");
  } catch (error) {
    adminTaskList.innerHTML = `<div class="admin-item"><span>${escapeHtml(error?.message || "Could not load task catalog.")}</span></div>`;
    return;
  }

  document.querySelectorAll(".admin-task-save-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const taskId = button.dataset.taskId;
      const titleInput = document.querySelector(`.admin-task-title-input[data-task-id="${taskId}"]`);
      const languageInput = document.querySelector(`.admin-task-language-input[data-task-id="${taskId}"]`);
      const statusInput = document.querySelector(`.admin-task-status-input[data-task-id="${taskId}"]`);
      const startupInput = document.querySelector(`.admin-task-startup-input[data-task-id="${taskId}"]`);
      const summaryInput = document.querySelector(`.admin-task-summary-input[data-task-id="${taskId}"]`);
      const rewardInput = document.querySelector(`.admin-task-reward-input[data-task-id="${taskId}"]`);
      const session = loadSession();
      if (!session) return;
      try {
        await authedJson(`/admin/tasks/${encodeURIComponent(taskId)}`, session, "PATCH", {
          title: titleInput?.value?.trim(),
          language: languageInput?.value?.trim(),
          status: statusInput?.value?.trim() || "open",
          startupName: startupInput?.value?.trim() || "",
          summary: summaryInput?.value?.trim() || "",
          reward: Number.parseFloat(rewardInput?.value || "0"),
        });
        const feedbackNode = document.getElementById(`admin-task-feedback-${taskId}`);
        if (feedbackNode) {
          feedbackNode.textContent = "Saved successfully.";
          feedbackNode.classList.remove("hidden");
        }
        await trackEvent(session, "admin_task_updated", { taskId });
        await renderAdminTaskManager(session);
      } catch (error) {
        alert(error?.message || "Could not save task.");
      }
    });
  });

  document.querySelectorAll(".admin-task-delete-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const taskId = button.dataset.taskId;
      if (!window.confirm(`Delete task ${formatTaskId(taskId)}?`)) return;
      const session = loadSession();
      if (!session) return;
      try {
        const result = await authedJson(`/admin/tasks/${encodeURIComponent(taskId)}`, session, "DELETE");
        showActionFeedback(adminTaskCreateFeedback, result?.message || "Task action completed.");
        await trackEvent(session, "admin_task_delete_requested", { taskId });
        await renderAdminTaskManager(session);
      } catch (error) {
        showActionFeedback(adminTaskCreateFeedback, error?.message || "Could not delete task.", true);
      }
    });
  });
}

async function renderAdminSubmissionReviews() {
  if (!adminSubmissionList) return;
  const session = loadSession();
  if (!session) return;
  let submissions = [];
  let tasks = [];
  try {
    submissions = (await authedJson("/submissions", session)).sort(
      (a, b) => new Date(b.submittedAt || 0) - new Date(a.submittedAt || 0)
    );
    tasks = await authedJson("/tasks", session);
  } catch (error) {
    adminSubmissionList.innerHTML = `<div class="admin-item"><span>${escapeHtml(error?.message || "Could not load submissions.")}</span></div>`;
    return;
  }
  const taskById = new Map(tasks.map((task) => [task.id, task]));

  adminSubmissionList.innerHTML =
    submissions.length === 0
      ? `<div class="admin-item"><span>No submissions to review yet.</span></div>`
      : submissions
          .map((sub) => {
            const task = taskById.get(sub.taskId);
            const reasonOptions = REJECTION_REASONS.map((reason) => `<option value="${reason}">${reason}</option>`).join("");
            const reviewControls =
              sub.status === "under_review"
                ? `<div class="review-controls">
                     <select class="review-reason-input" data-submission-id="${sub.id}">
                       <option value="">Select rejection reason</option>
                       ${reasonOptions}
                     </select>
                     <label class="section-note">AI detection confidence (%)</label>
                     <input class="ai-confidence-input" data-submission-id="${sub.id}" type="number" min="0" max="100" step="1" placeholder="0-100" />
                     <input class="review-note-input" data-submission-id="${sub.id}" placeholder="Optional reviewer note" />
                     <button class="btn btn-primary review-approve-btn" data-submission-id="${sub.id}">Approve 100%</button>
                     <button class="btn btn-primary review-partial-btn" data-submission-id="${sub.id}">Approve 50%</button>
                     <button class="btn btn-ghost review-reject-btn" data-submission-id="${sub.id}">Reject</button>
                   </div>`
                : "";

            return `
      <div class="admin-item">
        <div>
          <strong>${task?.title || formatTaskId(sub.taskId)}</strong><br />
          <span>Contributor ${sub.contributorName || sub.contributorId} â€¢ ${new Date(sub.submittedAt || Date.now()).toLocaleString()}</span>
          <details class="review-details">
            <summary>Implementation process</summary>
            <pre class="review-code-block">${escapeHtml(sub.thinking || "No implementation process submitted.")}</pre>
          </details>
          <details class="review-details">
            <summary>Submitted code</summary>
            <pre class="review-code-block">${escapeHtml(sub.code || "No code submitted.")}</pre>
          </details>
          ${renderSubmissionAttachments(sub.attachments || [], sub.id)}
          ${typeof sub.aiDetectionConfidence === "number" ? `<span class="review-note"><strong>AI confidence:</strong> ${sub.aiDetectionConfidence}%</span>` : ""}
          ${sub.rejectionReason ? `<span class="review-note"><strong>Reason:</strong> ${sub.rejectionReason}</span>` : ""}
          ${sub.reviewNote ? `<span class="review-note"><strong>Note:</strong> ${sub.reviewNote}</span>` : ""}
          ${sub.startupFeedbackRating ? `<span class="review-note"><strong>Startup rating:</strong> ${sub.startupFeedbackRating}/5</span>` : ""}
          ${sub.startupFeedbackNote ? `<span class="review-note"><strong>Startup feedback:</strong> ${sub.startupFeedbackNote}</span>` : ""}
        </div>
        <div>
          <span class="status-pill ${statusClass(sub.status)}">${statusLabel(sub.status)}</span>
          ${reviewControls}
        </div>
      </div>`;
          })
          .join("");

  document.querySelectorAll(".review-approve-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const submissionId = button.dataset.submissionId;
      const noteInput = document.querySelector(`.review-note-input[data-submission-id="${submissionId}"]`);
      const aiInput = document.querySelector(`.ai-confidence-input[data-submission-id="${submissionId}"]`);
      try {
        await authedJson(`/submissions/${submissionId}/review`, session, "PATCH", {
          status: "approved",
          aiDetectionConfidence: Number(aiInput?.value || 0),
          reviewNote: noteInput?.value?.trim() || "Meets task intent and code quality expectations.",
        });
        await renderAdminSubmissionReviews();
      } catch (error) {
        alert(error?.message || "Could not approve submission.");
      }
    });
  });

  document.querySelectorAll(".review-partial-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const submissionId = button.dataset.submissionId;
      const noteInput = document.querySelector(`.review-note-input[data-submission-id="${submissionId}"]`);
      const aiInput = document.querySelector(`.ai-confidence-input[data-submission-id="${submissionId}"]`);
      try {
        await authedJson(`/submissions/${submissionId}/review`, session, "PATCH", {
          status: "partial_approved",
          aiDetectionConfidence: Number(aiInput?.value || 0),
          reviewNote: noteInput?.value?.trim() || "Correct direction, but implementation is incomplete. 50% payout granted.",
        });
        await renderAdminSubmissionReviews();
      } catch (error) {
        alert(error?.message || "Could not partially approve submission.");
      }
    });
  });

  document.querySelectorAll(".review-reject-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const submissionId = button.dataset.submissionId;
      const reasonInput = document.querySelector(`.review-reason-input[data-submission-id="${submissionId}"]`);
      const noteInput = document.querySelector(`.review-note-input[data-submission-id="${submissionId}"]`);
      const aiInput = document.querySelector(`.ai-confidence-input[data-submission-id="${submissionId}"]`);
      const reason = reasonInput?.value?.trim();
      if (!reason) {
        alert("Please select a rejection reason.");
        return;
      }
      try {
        await authedJson(`/submissions/${submissionId}/review`, session, "PATCH", {
          status: "rejected",
          rejectionReason: reason,
          aiDetectionConfidence: Number(aiInput?.value || 0),
          reviewNote: noteInput?.value?.trim() || "Submission is rejected for this task based on review policy.",
        });
        await renderAdminSubmissionReviews();
      } catch (error) {
        alert(error?.message || "Could not reject submission.");
      }
    });
  });

  document.querySelectorAll(".submission-download-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const attachmentId = Number(button.dataset.attachmentId || 0);
      if (!attachmentId) return;
      try {
        await downloadSubmissionAttachment(session, attachmentId, "submission-attachment");
      } catch (error) {
        alert(error?.message || "Could not download attachment.");
      }
    });
  });
}

async function renderAdminPayoutManager(session) {
  let requests = [];
  try {
    requests = (await authedJson("/payout-requests", session)).sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  } catch (error) {
    adminPayoutList.innerHTML = `<div class="admin-item"><span>${escapeHtml(error?.message || "Could not load payout requests.")}</span></div>`;
    return;
  }
  adminPayoutList.innerHTML =
    requests.length === 0
      ? `<div class="admin-item"><span>No payout requests submitted yet.</span></div>`
      : requests
          .map(
            (req) => `
      <div class="admin-item">
        <div>
          <strong>User ${req.userId} â€¢ $${Number(req.amount).toFixed(2)}</strong><br />
          <span>${req.provider} â€¢ ${new Date(req.createdAt).toLocaleString()}</span>
        </div>
        <div class="reward-editor">
          <span class="status-pill ${payoutStatusClass(req.status)}">${statusLabel(req.status)}</span>
          ${
            req.status === "pending"
              ? `<button class="btn btn-primary payout-approve-btn" data-payout-id="${req.id}">Mark paid</button>
                 <button class="btn btn-ghost payout-reject-btn" data-payout-id="${req.id}">Reject</button>`
              : ""
          }
        </div>
      </div>`
          )
          .join("");

  document.querySelectorAll(".payout-approve-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const payoutId = button.dataset.payoutId;
      try {
        await authedJson(`/payout-requests/${payoutId}`, session, "PATCH", {
          status: "paid",
        });
        await renderAdminPayoutManager(session);
      } catch (error) {
        alert(error?.message || "Could not mark payout as paid.");
      }
    });
  });

  document.querySelectorAll(".payout-reject-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const payoutId = button.dataset.payoutId;
      try {
        await authedJson(`/payout-requests/${payoutId}`, session, "PATCH", {
          status: "rejected",
        });
        await renderAdminPayoutManager(session);
      } catch (error) {
        alert(error?.message || "Could not reject payout.");
      }
    });
  });
}

function renderAdminDisputes() {
  if (!adminDisputeList) return;
  const submissions = loadJson(SUBMISSIONS_DB_KEY, []).sort(
    (a, b) => new Date(b.submittedAt || 0) - new Date(a.submittedAt || 0)
  );
  const disputed = submissions.filter((sub) => sub.dispute === "opened");

  adminDisputeList.innerHTML =
    disputed.length === 0
      ? `<div class="admin-item"><span>No open contests.</span></div>`
      : disputed
          .map((sub) => {
            return `
      <div class="admin-item">
        <div>
          <strong>Submission ${sub.id} â€¢ Task ${formatTaskId(sub.taskId)}</strong><br />
          <span>Contributor ${sub.contributorName || sub.contributorId}</span>
          <span class="review-note"><strong>Contest claim:</strong> ${sub.disputeReason || "No claim text"}</span>
          ${sub.reviewNote ? `<span class="review-note"><strong>Original review note:</strong> ${sub.reviewNote}</span>` : ""}
        </div>
        <div class="review-controls">
          <input class="dispute-admin-note-input" data-submission-id="${sub.id}" placeholder="Admin contest response note" />
          <button class="btn btn-primary dispute-uphold-btn" data-submission-id="${sub.id}">Uphold contributor</button>
          <button class="btn btn-ghost dispute-reject-btn" data-submission-id="${sub.id}">Keep original review</button>
        </div>
      </div>`;
          })
          .join("");

  document.querySelectorAll(".dispute-uphold-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const submissionId = button.dataset.submissionId;
      const submissionsDb = loadJson(SUBMISSIONS_DB_KEY, []);
      const target = submissionsDb.find((item) => String(item.id) === String(submissionId));
      if (!target || target.dispute !== "opened") return;
      const noteInput = document.querySelector(`.dispute-admin-note-input[data-submission-id="${submissionId}"]`);
      target.dispute = "resolved";
      target.disputeResolvedAt = new Date().toISOString();
      target.disputeAdminNote = noteInput?.value?.trim() || "Contest accepted. Contributor's appeal was valid.";
      saveJson(SUBMISSIONS_DB_KEY, submissionsDb);
      renderAdminDisputes();
      renderAdminSubmissionReviews();
    });
  });

  document.querySelectorAll(".dispute-reject-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const submissionId = button.dataset.submissionId;
      const submissionsDb = loadJson(SUBMISSIONS_DB_KEY, []);
      const target = submissionsDb.find((item) => String(item.id) === String(submissionId));
      if (!target || target.dispute !== "opened") return;
      const noteInput = document.querySelector(`.dispute-admin-note-input[data-submission-id="${submissionId}"]`);
      target.dispute = "rejected";
      target.disputeResolvedAt = new Date().toISOString();
      target.disputeAdminNote = noteInput?.value?.trim() || "Contest reviewed. Original review decision stands.";
      saveJson(SUBMISSIONS_DB_KEY, submissionsDb);
      renderAdminDisputes();
      renderAdminSubmissionReviews();
    });
  });
}

async function renderStartupWorkspace(session) {
  if (!startupStatusCard || !startupTaskRequestList || !startupTaskRequestForm) return;
  try {
    const startup = await authedJson("/startups/me", session);
    const statusClassName = payoutStatusClass(startup.status);
    startupStatusCard.innerHTML = `
      <h3 style="margin:0 0 8px;">${escapeHtml(startup.companyName)}</h3>
      <p style="margin:0 0 10px;">Industry: ${escapeHtml(startup.industry)} â€¢ Stage: ${escapeHtml(startup.productStage)} â€¢ Team size: ${startup.teamSize}</p>
      <p style="margin:0 0 10px;">Website: ${escapeHtml(startup.websiteUrl)}</p>
      <p style="margin:0 0 10px;">Tech stack: ${escapeHtml(startup.techStack || "Not set")}</p>
      <p style="margin:0 0 10px;">Task requests created: ${Number(startup.numberOfTasks || 0)} â€¢ Task offers posted: ${Number(startup.tasksPosted || 0)}</p>
      <span class="status-pill ${statusClassName}">${statusLabel(startup.status)}</span>
      ${startup.reviewNote ? `<p class="review-note"><strong>Ops note:</strong> ${escapeHtml(startup.reviewNote)}</p>` : ""}
    `;

    const requestButton = startupTaskRequestForm.querySelector("button[type='submit']");
    const canSubmit = startup.status === "approved";
    requestButton.disabled = !canSubmit;
    requestButton.textContent = canSubmit
      ? "Submit task request"
      : "Startup must be approved before submitting requests";

    const requests = await authedJson("/startup-task-requests", session);
    startupTaskRequestList.innerHTML =
      requests.length === 0
        ? `<div class="admin-item"><span>No task requests submitted yet.</span></div>`
        : requests
            .map(
              (req) => `
      <div class="admin-item">
        <div>
          <strong>${escapeHtml(req.title)} â€¢ ${escapeHtml(req.language)} â€¢ $${Number(req.reward).toFixed(2)}</strong><br />
          <span>${new Date(req.createdAt).toLocaleString()}</span>
          ${req.adminNote ? `<span class="review-note"><strong>Admin note:</strong> ${escapeHtml(req.adminNote)}</span>` : ""}
        </div>
        <span class="status-pill ${payoutStatusClass(req.status)}">${statusLabel(req.status)}</span>
      </div>`
            )
            .join("");

    if (startupSubmissionFeedbackList) {
      const submissions = await authedJson("/submissions", session);
      const reviewed = submissions.filter((item) => ["approved", "partial_approved", "rejected"].includes(item.status));
      startupSubmissionFeedbackList.innerHTML =
        reviewed.length === 0
          ? `<div class="admin-item"><span>No reviewed submissions available for rating yet.</span></div>`
          : reviewed
              .map(
                (sub) => `
      <div class="admin-item">
        <div>
          <strong>Task ${formatTaskId(sub.taskId)} â€¢ Contributor ${escapeHtml(sub.contributorName || String(sub.contributorId))}</strong><br />
          <span>Status: ${statusLabel(sub.status)} â€¢ ${new Date(sub.submittedAt || Date.now()).toLocaleString()}</span>
          ${sub.reviewNote ? `<span class="review-note"><strong>Admin note:</strong> ${escapeHtml(sub.reviewNote)}</span>` : ""}
          ${renderSubmissionAttachments(sub.attachments || [], sub.id)}
          ${
            sub.startupFeedbackRating
              ? `<span class="review-note"><strong>Your rating:</strong> ${sub.startupFeedbackRating}/5${sub.startupFeedbackNote ? ` â€” ${escapeHtml(sub.startupFeedbackNote)}` : ""}</span>`
              : ""
          }
        </div>
        <div class="review-controls">
          <select class="startup-feedback-rating-input" data-submission-id="${sub.id}">
            <option value="">Rate usefulness (1-5)</option>
            <option value="1">1 - Not useful</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
            <option value="5">5 - Very useful</option>
          </select>
          <input class="startup-feedback-note-input" data-submission-id="${sub.id}" placeholder="Optional feedback note" />
          <button class="btn btn-primary startup-feedback-submit-btn" data-submission-id="${sub.id}">Save rating</button>
        </div>
      </div>`
              )
              .join("");

      document.querySelectorAll(".startup-feedback-submit-btn").forEach((button) => {
        button.addEventListener("click", async () => {
          const submissionId = button.dataset.submissionId;
          const ratingInput = document.querySelector(`.startup-feedback-rating-input[data-submission-id="${submissionId}"]`);
          const noteInput = document.querySelector(`.startup-feedback-note-input[data-submission-id="${submissionId}"]`);
          const rating = Number(ratingInput?.value || 0);
          if (!rating || rating < 1 || rating > 5) {
            alert("Please select a rating from 1 to 5.");
            return;
          }
          try {
            await authedJson(`/startup/submissions/${submissionId}/feedback`, session, "POST", {
              rating,
              note: noteInput?.value?.trim() || "",
            });
            await renderStartupWorkspace(session);
          } catch (error) {
            alert(error?.message || "Could not save startup feedback.");
          }
        });
      });

      document.querySelectorAll(".submission-download-btn").forEach((button) => {
        button.addEventListener("click", async () => {
          const attachmentId = Number(button.dataset.attachmentId || 0);
          if (!attachmentId) return;
          try {
            await downloadSubmissionAttachment(session, attachmentId, "submission-attachment");
          } catch (error) {
            alert(error?.message || "Could not download attachment.");
          }
        });
      });
    }

    if (startupTaskDeletionRequestList) {
      const deletionRequests = await authedJson("/startup-task-deletion-requests", session);
      const pendingDeletion = deletionRequests.filter((item) => item.status === "pending");
      startupTaskDeletionRequestList.innerHTML =
        pendingDeletion.length === 0
          ? `<div class="admin-item"><span>No pending task deletion approvals.</span></div>`
          : pendingDeletion
              .map(
                (item) => `
      <div class="admin-item">
        <div>
          <strong>Task ${formatTaskId(item.taskId)} â€¢ ${escapeHtml(item.startupName)}</strong><br />
          <span>Requested by admin ${item.adminUserId} â€¢ ${new Date(item.createdAt).toLocaleString()}</span>
          ${item.note ? `<span class="review-note">${escapeHtml(item.note)}</span>` : ""}
        </div>
        <div class="review-controls">
          <input class="startup-deletion-note-input" data-deletion-id="${item.id}" placeholder="Optional response note" />
          <button class="btn btn-primary startup-deletion-approve-btn" data-deletion-id="${item.id}">Approve deletion</button>
          <button class="btn btn-ghost startup-deletion-reject-btn" data-deletion-id="${item.id}">Reject deletion</button>
        </div>
      </div>`
              )
              .join("");

      document.querySelectorAll(".startup-deletion-approve-btn").forEach((button) => {
        button.addEventListener("click", async () => {
          const deletionId = button.dataset.deletionId;
          const noteInput = document.querySelector(`.startup-deletion-note-input[data-deletion-id="${deletionId}"]`);
          try {
            await authedJson(`/startup-task-deletion-requests/${deletionId}/review`, session, "PATCH", {
              status: "approved",
              note: noteInput?.value?.trim() || "",
            });
            await renderStartupWorkspace(session);
          } catch (error) {
            alert(error?.message || "Could not approve deletion request.");
          }
        });
      });

      document.querySelectorAll(".startup-deletion-reject-btn").forEach((button) => {
        button.addEventListener("click", async () => {
          const deletionId = button.dataset.deletionId;
          const noteInput = document.querySelector(`.startup-deletion-note-input[data-deletion-id="${deletionId}"]`);
          try {
            await authedJson(`/startup-task-deletion-requests/${deletionId}/review`, session, "PATCH", {
              status: "rejected",
              note: noteInput?.value?.trim() || "",
            });
            await renderStartupWorkspace(session);
          } catch (error) {
            alert(error?.message || "Could not reject deletion request.");
          }
        });
      });
    }
  } catch (error) {
    startupStatusCard.innerHTML = `<p>Startup registration not found. Complete startup onboarding first.</p>`;
    startupTaskRequestList.innerHTML = `<div class="admin-item"><span>${escapeHtml(error?.message || "Could not load startup workspace.")}</span></div>`;
    if (startupTaskDeletionRequestList) {
      startupTaskDeletionRequestList.innerHTML = `<div class="admin-item"><span>Could not load deletion approvals.</span></div>`;
    }
  }
}

function bindStartupHandlers(session) {
  if (!startupTaskRequestForm) return;
  const updateStartupPublishHint = () => {
    if (!startupTaskPublishHint) return;
    const language = startupTaskLanguage.value.trim().toLowerCase();
    const reward = Number.parseFloat(startupTaskReward.value || "0");
    const demand = ["typescript", "javascript", "python", "sql"].includes(language) ? "high demand" : "normal demand";
    const eta = reward >= 4 ? "est. first response in ~6-12h" : reward >= 2 ? "est. first response in ~12-24h" : "est. first response in ~24-48h";
    startupTaskPublishHint.textContent = language
      ? `Language demand: ${demand}. ${eta}.`
      : "Hint: fill language + reward to see response-time estimate.";
  };
  startupTaskLanguage?.addEventListener("input", updateStartupPublishHint);
  startupTaskReward?.addEventListener("input", updateStartupPublishHint);
  updateStartupPublishHint();
  startupTaskRequestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await authedJson("/startup-task-requests", session, "POST", {
        title: startupTaskTitle.value.trim(),
        language: startupTaskLanguage.value.trim(),
        reward: Number.parseFloat(startupTaskReward.value),
        details: startupTaskDetails.value.trim(),
        acceptanceRules: startupTaskRules.value.trim(),
      });
      await trackEvent(session, "startup_task_request_created");
      startupTaskRequestForm.reset();
      await renderStartupWorkspace(session);
    } catch (error) {
      alert(error?.message || "Could not submit startup task request.");
    }
  });
}

async function renderAdminStartupRegistrations(session) {
  if (!adminStartupList) return;
  try {
    const startups = await authedJson("/startups/pending", session);
    adminStartupList.innerHTML =
      startups.length === 0
        ? `<div class="admin-item"><span>No pending startup registrations.</span></div>`
        : startups
            .map(
              (startup) => `
      <div class="admin-item">
        <div>
          <strong>${escapeHtml(startup.companyName)}</strong><br />
          <span>${escapeHtml(startup.industry)} â€¢ Team ${startup.teamSize} â€¢ ${escapeHtml(startup.websiteUrl)}</span>
          <span class="review-note"><strong>Intentions:</strong> ${escapeHtml(startup.intentions)}</span>
        </div>
        <div class="review-controls">
          <input class="startup-review-note-input" data-startup-id="${startup.id}" placeholder="Ops review note" />
          <button class="btn btn-primary startup-approve-btn" data-startup-id="${startup.id}">Approve</button>
          <button class="btn btn-ghost startup-reject-btn" data-startup-id="${startup.id}">Reject</button>
        </div>
      </div>`
            )
            .join("");

    document.querySelectorAll(".startup-approve-btn").forEach((button) => {
      button.addEventListener("click", async () => {
        const startupId = button.dataset.startupId;
        const noteInput = document.querySelector(`.startup-review-note-input[data-startup-id="${startupId}"]`);
        await authedJson(`/startups/${startupId}/review`, session, "PATCH", {
          status: "approved",
          reviewNote: noteInput?.value?.trim() || "Startup approved. You can now submit task requests.",
        });
        await renderAdminStartupRegistrations(session);
      });
    });

    document.querySelectorAll(".startup-reject-btn").forEach((button) => {
      button.addEventListener("click", async () => {
        const startupId = button.dataset.startupId;
        const noteInput = document.querySelector(`.startup-review-note-input[data-startup-id="${startupId}"]`);
        await authedJson(`/startups/${startupId}/review`, session, "PATCH", {
          status: "rejected",
          reviewNote: noteInput?.value?.trim() || "Startup rejected. Provide clearer intentions and squad details.",
        });
        await renderAdminStartupRegistrations(session);
      });
    });
  } catch (error) {
    adminStartupList.innerHTML = `<div class="admin-item"><span>${escapeHtml(error?.message || "Could not load startup registrations.")}</span></div>`;
  }
}

async function renderAdminStartupTaskRequests(session) {
  if (!adminStartupTaskRequestList) return;
  try {
    const requests = await authedJson("/startup-task-requests", session);
    const pending = requests.filter((item) => item.status === "pending");
    adminStartupTaskRequestList.innerHTML =
      pending.length === 0
        ? `<div class="admin-item"><span>No pending startup task requests.</span></div>`
        : pending
            .map(
              (req) => `
      <div class="admin-item">
        <div>
          <strong>${escapeHtml(req.title)} â€¢ ${escapeHtml(req.language)} â€¢ $${Number(req.reward).toFixed(2)}</strong><br />
          <span>Startup user ${req.startupUserId} â€¢ ${new Date(req.createdAt).toLocaleString()}</span>
          <span class="review-note"><strong>Details:</strong> ${escapeHtml(req.details)}</span>
          <span class="review-note"><strong>Acceptance:</strong> ${escapeHtml(req.acceptanceRules)}</span>
        </div>
        <div class="review-controls">
          <label class="section-note"><input type="checkbox" class="publish-request-checkbox" data-request-id="${req.id}" /> Publish to catalog</label>
          <input class="startup-request-note-input" data-request-id="${req.id}" placeholder="Admin response note" />
          <button class="btn btn-primary startup-request-approve-btn" data-request-id="${req.id}">Approve</button>
          <button class="btn btn-ghost startup-request-reject-btn" data-request-id="${req.id}">Reject</button>
        </div>
      </div>`
            )
            .join("");

    document.querySelectorAll(".startup-request-approve-btn").forEach((button) => {
      button.addEventListener("click", async () => {
        const requestId = button.dataset.requestId;
        const noteInput = document.querySelector(`.startup-request-note-input[data-request-id="${requestId}"]`);
        const publishInput = document.querySelector(`.publish-request-checkbox[data-request-id="${requestId}"]`);
        await authedJson(`/startup-task-requests/${requestId}/review`, session, "PATCH", {
          status: "approved",
          adminNote: noteInput?.value?.trim() || "Approved by platform ops.",
          publishToTasks: Boolean(publishInput?.checked),
        });
        await renderAdminStartupTaskRequests(session);
      });
    });

    document.querySelectorAll(".startup-request-reject-btn").forEach((button) => {
      button.addEventListener("click", async () => {
        const requestId = button.dataset.requestId;
        const noteInput = document.querySelector(`.startup-request-note-input[data-request-id="${requestId}"]`);
        await authedJson(`/startup-task-requests/${requestId}/review`, session, "PATCH", {
          status: "rejected",
          adminNote: noteInput?.value?.trim() || "Rejected by platform ops.",
          publishToTasks: false,
        });
        await renderAdminStartupTaskRequests(session);
      });
    });
  } catch (error) {
    adminStartupTaskRequestList.innerHTML = `<div class="admin-item"><span>${escapeHtml(error?.message || "Could not load startup requests.")}</span></div>`;
  }
}

function bindAdminTaskCreate(session) {
  if (!adminTaskCreateForm) return;
  adminTaskCreateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await authedJson("/admin/tasks", session, "POST", {
        id: adminTaskIdInput?.value?.trim() || undefined,
        title: adminTaskTitleInput?.value?.trim(),
        language: adminTaskLanguageInput?.value?.trim(),
        reward: Number.parseFloat(adminTaskRewardInput?.value || "0"),
        status: adminTaskStatusInput?.value?.trim() || "open",
        startupName: adminTaskStartupInput?.value?.trim() || "",
        summary: adminTaskSummaryInput?.value?.trim(),
        description: adminTaskDescriptionInput?.value?.trim(),
        endpoints: adminTaskEndpointsInput?.value?.trim() || "N/A",
        layout: adminTaskLayoutInput?.value?.trim() || "N/A",
        runInstructions: adminTaskRunInput?.value?.trim() || "N/A",
      });
      adminTaskCreateForm.reset();
      if (adminTaskStatusInput) adminTaskStatusInput.value = "open";
      if (adminTaskEndpointsInput) adminTaskEndpointsInput.value = "N/A";
      if (adminTaskLayoutInput) adminTaskLayoutInput.value = "N/A";
      if (adminTaskRunInput) adminTaskRunInput.value = "N/A";
      showActionFeedback(adminTaskCreateFeedback, "Task saved and added to catalog.");
      await trackEvent(session, "admin_task_created");
      await renderAdminTaskManager(session);
    } catch (error) {
      showActionFeedback(adminTaskCreateFeedback, error?.message || "Could not create task.", true);
    }
  });
}

async function renderAdminUsers(session) {
  if (!adminUserList) return;
  try {
    const users = await authedJson("/admin/users", session);
    adminUserList.innerHTML = users
      .sort((a, b) => a.id - b.id)
      .map(
        (user) => {
          const isCollapsed = adminUserCollapsed.has(String(user.id));
          if (isCollapsed) {
            return `
      <div class="admin-item">
        <div>
          <strong>${escapeHtml(user.fullName)}</strong><br />
          <span>User ${user.id} â€¢ ${escapeHtml(user.email)}</span>
          <span class="review-note">Role: ${escapeHtml(user.role)} â€¢ Profile: ${user.profileCompleted ? "complete" : "incomplete"} â€¢ Active: ${user.isActive ? "yes" : "no"}</span>
          <div class="admin-user-overview" data-user-id="${user.id}"><span class="section-note">Loading activity...</span></div>
        </div>
        <div class="review-controls">
          <button class="btn btn-ghost admin-user-edit-btn" data-user-id="${user.id}">Edit</button>
          <button class="btn btn-ghost admin-user-delete-btn" data-user-id="${user.id}" data-user-name="${escapeHtml(user.fullName)}">Remove user</button>
        </div>
      </div>`;
          }
          return `
      <div class="admin-item">
        <div>
          <strong>${escapeHtml(user.fullName)}</strong><br />
          <span>User ${user.id} â€¢ ${escapeHtml(user.email)}</span>
          <span class="review-note">Created: ${new Date(user.createdAt).toLocaleString()}</span>
          <div class="admin-user-overview" data-user-id="${user.id}"><span class="section-note">Loading activity...</span></div>
        </div>
        <div class="review-controls">
          <label>Role
            <select class="admin-user-role-input" data-user-id="${user.id}">
              <option value="contributor" ${user.role === "contributor" ? "selected" : ""}>contributor</option>
              <option value="startup" ${user.role === "startup" ? "selected" : ""}>startup</option>
              <option value="admin" ${user.role === "admin" ? "selected" : ""}>admin</option>
            </select>
          </label>
          <label class="section-note"><input type="checkbox" class="admin-user-profile-input" data-user-id="${user.id}" ${user.profileCompleted ? "checked" : ""} /> Profile completed</label>
          <label class="section-note"><input type="checkbox" class="admin-user-active-input" data-user-id="${user.id}" ${user.isActive ? "checked" : ""} /> Account active</label>
          <button class="btn btn-primary admin-user-save-btn" data-user-id="${user.id}">Save access</button>
          <button class="btn btn-ghost admin-user-delete-btn" data-user-id="${user.id}" data-user-name="${escapeHtml(user.fullName)}">Remove user</button>
        </div>
      </div>`;
        }
      )
      .join("");

    await Promise.all(
      users.map(async (user) => {
        const target = document.querySelector(`.admin-user-overview[data-user-id="${user.id}"]`);
        if (!target) return;
        try {
          const overview = await authedJson(`/admin/users/${user.id}/overview`, session);
          target.innerHTML = `<span class="review-note"><strong>Activity:</strong> submissions ${overview.submissionsCount} (pending ${overview.pendingSubmissions}, approved ${overview.approvedSubmissions}, partial ${overview.partialApprovedSubmissions}, rejected ${overview.rejectedSubmissions}) â€¢ payouts ${overview.payoutRequestsCount} (paid ${overview.paidPayoutRequests}, pending ${overview.pendingPayoutRequests})${overview.lastLoginAt ? ` â€¢ last login ${new Date(overview.lastLoginAt).toLocaleString()}` : ""}</span>
            ${
              overview.startupCompanyName
                ? `<span class="review-note"><strong>Startup:</strong> ${escapeHtml(overview.startupCompanyName)} â€¢ ${escapeHtml(
                    overview.startupStatus || "unknown"
                  )} â€¢ tasks posted ${overview.startupTasksPosted}</span>`
                : ""
            }`;
        } catch {
          target.innerHTML = `<span class="section-note">Activity unavailable.</span>`;
        }
      })
    );
  } catch (error) {
    adminUserList.innerHTML = `<div class="admin-item"><span>${escapeHtml(error?.message || "Could not load users.")}</span></div>`;
    return;
  }

  document.querySelectorAll(".admin-user-edit-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const userId = button.dataset.userId;
      adminUserCollapsed.delete(String(userId));
      await renderAdminUsers(session);
    });
  });

  document.querySelectorAll(".admin-user-save-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const userId = button.dataset.userId;
      const roleInput = document.querySelector(`.admin-user-role-input[data-user-id="${userId}"]`);
      const profileInput = document.querySelector(`.admin-user-profile-input[data-user-id="${userId}"]`);
      const activeInput = document.querySelector(`.admin-user-active-input[data-user-id="${userId}"]`);
      try {
        await authedJson(`/admin/users/${userId}`, session, "PATCH", {
          role: roleInput?.value || "contributor",
          profileCompleted: Boolean(profileInput?.checked),
          isActive: Boolean(activeInput?.checked),
        });
        adminUserCollapsed.add(String(userId));
        showActionFeedback(adminUserSaveFeedback, `Access saved for user ${userId}.`);
        await trackEvent(session, "admin_user_access_updated", { targetUserId: Number(userId) });
        await renderAdminUsers(session);
      } catch (error) {
        showActionFeedback(adminUserSaveFeedback, error?.message || "Could not update user.", true);
      }
    });
  });

  document.querySelectorAll(".admin-user-delete-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const userId = button.dataset.userId;
      const userName = button.dataset.userName || "this user";
      const confirmed = window.confirm(`Remove ${userName} from the platform? This action cannot be undone.`);
      if (!confirmed) return;
      try {
        await authedJson(`/admin/users/${userId}`, session, "DELETE");
        adminUserCollapsed.delete(String(userId));
        showActionFeedback(adminUserSaveFeedback, `User ${userName} removed.`);
        await trackEvent(session, "admin_user_removed", { targetUserId: Number(userId) });
        await renderAdminUsers(session);
      } catch (error) {
        showActionFeedback(adminUserSaveFeedback, error?.message || "Could not remove user.", true);
      }
    });
  });
}

async function renderAdminAnalyticsOverview(session) {
  if (!adminAnalyticsOverview) return;
  try {
    const metrics = await authedJson("/admin/analytics/overview", session);
    adminAnalyticsOverview.innerHTML = `
      <article class="card"><h3>Events</h3><p>${metrics.eventsLast24h} tracked events</p></article>
      <article class="card"><h3>Signups</h3><p>${metrics.signupsLast24h} completed</p></article>
      <article class="card"><h3>Logins</h3><p>${metrics.loginsLast24h} successful</p></article>
      <article class="card"><h3>Submissions</h3><p>${metrics.submissionsLast24h} task submissions</p></article>
      <article class="card"><h3>Payout requests</h3><p>${metrics.payoutRequestsLast24h} requests</p></article>
      <article class="card"><h3>Startup task requests</h3><p>${metrics.startupTaskRequestsLast24h} created</p></article>
    `;
  } catch (error) {
    adminAnalyticsOverview.innerHTML = `<article class="card"><p>${escapeHtml(error?.message || "Could not load analytics overview.")}</p></article>`;
  }
}

function openDispute(submissionId) {
  const note = window.prompt("Why are you opening this contest?");
  if (!note || note.trim().length < 5) return;
  const submissions = loadJson(SUBMISSIONS_DB_KEY, []);
  const target = submissions.find((item) => item.id === submissionId);
  if (!target) return;
  target.dispute = "opened";
  target.disputeReason = note.trim();
  saveJson(SUBMISSIONS_DB_KEY, submissions);
  const session = loadSession();
  if (session) renderDashboard(session);
}

const session = loadSession();
if (!session) {
  window.location.href = "/index.html";
} else if (!session.profileCompleted) {
  window.location.href = session.role === "startup" ? "/views/startup-onboarding.html" : "/views/onboarding.html";
} else {
  renderNavbar(session);
  sessionStorage.setItem(LAST_PAGE_KEY, "/views/dashboard.html");
  setBrandLinkTarget(session);
  if (session.role === "admin") {
    document.body.classList.add("admin-view");
    contributorSection.classList.add("hidden");
    adminSection.classList.remove("hidden");
    renderAdminAnalyticsOverview(session);
    bindAdminTaskCreate(session);
    renderAdminTaskManager(session);
    void renderAdminSubmissionReviews();
    renderAdminPayoutManager(session);
    renderAdminDisputes();
    renderAdminStartupRegistrations(session);
    renderAdminStartupTaskRequests(session);
    renderAdminUsers(session);
  } else if (session.role === "startup") {
    document.body.classList.remove("admin-view");
    adminSection.classList.add("hidden");
    contributorSection.classList.add("hidden");
    startupSection.classList.remove("hidden");
    bindStartupHandlers(session);
    renderStartupWorkspace(session);
  } else {
    document.body.classList.remove("admin-view");
    adminSection.classList.add("hidden");
    startupSection.classList.add("hidden");
    contributorSection.classList.remove("hidden");
    syncApprovedEarnings(session);
    renderUserProfile(session);
    renderDashboard(session);
    bindContributorFinanceHandlers(session);
    renderWalletAndPayouts(session);
  }
}

