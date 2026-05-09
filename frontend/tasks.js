const SESSION_KEY = "app_contributor_session";
const AUTH_TOKEN_KEY = "app_contributor_auth_token";
const API_BASE_URL = (() => {
  const configured = String(window.__APP_API_BASE_URL__ || "").trim();
  const base = configured || "https://appcontributor-backend.onrender.com/api";
  const normalized = base.replace(/\/+$/, "");
  return normalized.endsWith("/api") ? normalized : `${normalized}/api`;
})();
const LAST_PAGE_KEY = "app_contributor_last_page";
const SUBMISSIONS_DB_KEY = "app_contributor_submissions_db";
const TASK_SHORTLIST_KEY = "app_contributor_task_shortlist";

const navbarRight = document.getElementById("navbar-right");
const taskList = document.getElementById("task-list");
const languageFilter = document.getElementById("language-filter");
const taskModal = document.getElementById("task-modal");
const closeTaskModalBtn = document.getElementById("close-task-modal");
const taskSubmitForm = document.getElementById("task-submit-form");
const taskModalTitle = document.getElementById("task-modal-title");
const taskModalReward = document.getElementById("task-modal-reward");
const taskModalStatus = document.getElementById("task-modal-status");
const taskModalId = document.getElementById("task-modal-id");
const taskModalDescription = document.getElementById("task-modal-description");
const taskModalEndpoints = document.getElementById("task-modal-endpoints");
const taskModalLayout = document.getElementById("task-modal-layout");
const taskModalRun = document.getElementById("task-modal-run");
const taskModalLanguage = document.getElementById("task-modal-language");
const thinkingInput = document.getElementById("submission-thinking");
const codeInput = document.getElementById("submission-code");
const codeLineNumbers = document.getElementById("code-line-numbers");
const submissionFilesInput = document.getElementById("submission-files");
const submissionFilesList = document.getElementById("submission-files-list");
const confirmLanguageFit = document.getElementById("confirm-language-fit");
const confirmLanguageFitLabel = document.getElementById("confirm-language-fit-label");
const submissionLanguageUsed = document.getElementById("submission-language-used");

let selectedLanguage = "all";
let activeTask = null;
let cachedTasks = [];
let shortlistedTasks = new Set();
let pendingAttachments = [];
const MAX_ATTACHMENTS = 5;
const MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024;
const ALLOWED_ATTACHMENT_EXTENSIONS = new Set([".py", ".pdf", ".txt", ".md", ".zip", ".png", ".jpg", ".jpeg"]);

function readCookie(name) {
  const target = `${name}=`;
  const cookie = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(target));
  return cookie ? decodeURIComponent(cookie.slice(target.length)) : "";
}

function loadShortlist() {
  try {
    const raw = localStorage.getItem(TASK_SHORTLIST_KEY) || sessionStorage.getItem(TASK_SHORTLIST_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    shortlistedTasks = new Set(Array.isArray(parsed) ? parsed : []);
  } catch {
    shortlistedTasks = new Set();
  }
}

function saveShortlist() {
  const payload = JSON.stringify(Array.from(shortlistedTasks));
  localStorage.setItem(TASK_SHORTLIST_KEY, payload);
  sessionStorage.setItem(TASK_SHORTLIST_KEY, payload);
}

function fitScore(task) {
  const reward = Number(task.reward || 0);
  if (reward >= 4) return "Advanced";
  if (reward >= 2) return "Intermediate";
  return "Beginner-friendly";
}

function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function statusClass(status) {
  return status === "under_review" ? "status-review" : status === "done" ? "status-done" : "status-open";
}

function statusLabel(status) {
  return status === "under_review" ? "Under Review" : status === "done" ? "Completed" : "Open";
}

function formatTaskId(taskId) {
  const raw = String(taskId || "").trim();
  if (!raw) return "";
  if (raw.startsWith("PB-")) return `TASK-${raw.slice(3)}`;
  if (raw.startsWith("SR-")) return `TASK-${raw.slice(3)}`;
  return raw;
}

function languageConstraintEnabled(taskLanguage) {
  const normalized = String(taskLanguage || "").trim().toLowerCase();
  return normalized !== "" && normalized !== "all" && normalized !== "general";
}

function deriveTaskLanguage(task) {
  const primary = String(task?.language || "").trim();
  if (languageConstraintEnabled(primary)) return primary;
  const fallback = String(task?.type || "").trim();
  if (languageConstraintEnabled(fallback)) return fallback;
  return "";
}

function displayTaskType(task, derivedLanguage) {
  const typeText = String(task?.type || "").trim();
  if (!typeText) return "";
  if (derivedLanguage && typeText.toLowerCase() === derivedLanguage.toLowerCase()) return "";
  return typeText;
}

async function fetchTasks(language = "all") {
  const params = language && language !== "all" ? `?language=${encodeURIComponent(language)}` : "";
  const response = await fetch(`${API_BASE_URL}/tasks${params}`);
  if (!response.ok) throw new Error("Failed to load tasks");
  return response.json();
}

async function fetchTask(taskId) {
  const response = await fetch(`${API_BASE_URL}/tasks/${encodeURIComponent(taskId)}`);
  if (!response.ok) throw new Error("Failed to load task details");
  return response.json();
}

async function createSubmission(payload) {
  const token = sessionStorage.getItem(AUTH_TOKEN_KEY) || "";
  const csrfToken = readCookie("appcontributor_csrf");
  const response = await fetch(`${API_BASE_URL}/submissions`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || "Submission failed");
  }
  return response.json();
}

async function uploadSubmissionAttachments(submissionId, files) {
  if (!files.length) return [];
  const token = sessionStorage.getItem(AUTH_TOKEN_KEY) || "";
  const csrfToken = readCookie("appcontributor_csrf");
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  const response = await fetch(`${API_BASE_URL}/submissions/${encodeURIComponent(submissionId)}/attachments`, {
    method: "POST",
    credentials: "include",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
    body: form,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || "Attachment upload failed");
  }
  return response.json();
}

function renderNavbar() {
  const session = loadSession();
  if (!session) {
    window.location.href = "./index.html";
    return;
  }
  if (session.role !== "contributor") {
    window.location.href = "./dashboard.html";
    return;
  }
  if (!session.profileCompleted) {
    window.location.href = "./onboarding.html";
    return;
  }

  navbarRight.innerHTML = `
    <a class="btn btn-ghost" href="./tasks.html">Tasks</a>
    <a class="btn btn-ghost" href="./dashboard.html">Dashboard</a>
    <button class="btn btn-ghost" id="logout-btn">Logout</button>
    <span class="chip"><img class="money-icon-img" src="./icon-wallet.svg" alt="" /> Balance: $${Number(session.balance).toFixed(2)}</span>
    <a class="btn btn-ghost user-profile-btn" href="./dashboard.html" title="Open your profile">
      <img class="user-icon-img" src="./icon-user.svg" alt="" />
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
      // ignore
    }
    localStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
    window.location.href = "./index.html";
  });
}

function setBrandLinkTarget() {
  // Navbar brand is display-only (logo + title), not a link.
}

function renderTaskCards(tasks) {
  if (tasks.length === 0) {
    taskList.innerHTML = `<article class="card"><p>No tasks found for ${selectedLanguage} yet.</p></article>`;
    return;
  }

  taskList.innerHTML = tasks
    .map((task) => {
      const derivedLanguage = deriveTaskLanguage(task);
      const typeText = displayTaskType(task, derivedLanguage);
      const sublineLeft = [task.startup_name || "Startup App", typeText].filter(Boolean).join(" • ");
      return `
      <article class="task-card" data-task-id="${task.id}" role="button" tabindex="0" aria-label="Open ${task.title}">
        <div class="task-signal"></div>
        <div class="task-top">
          <p class="task-title">${task.title}</p>
          <strong class="task-reward">$${Number(task.reward).toFixed(2)}</strong>
        </div>
        <div class="task-subline">
          <span><img class="task-inline-icon" src="./icon-review.svg" alt="" />${sublineLeft}</span>
          <span>${formatTaskId(task.id)}</span>
        </div>
        <p class="task-summary">${task.summary}</p>
        <div class="task-meta">
          <span class="task-kpi task-kpi-highlight"><img class="task-inline-icon" src="./icon-wallet.svg" alt="" /><strong>$${Number(task.reward).toFixed(2)}</strong></span>
          <span class="task-kpi"><img class="task-inline-icon" src="./icon-user.svg" alt="" />Slots: <strong>${task.slots}</strong></span>
          ${
            derivedLanguage
              ? `<span class="task-kpi task-kpi-lang"><img class="task-inline-icon" src="./icon-payout.svg" alt="" />Language: <strong>${derivedLanguage}</strong></span>`
              : ""
          }
          <span class="status-pill ${statusClass(task.status)}">${statusLabel(task.status)}</span>
        </div>
        <div class="task-card-actions">
          <button class="btn btn-ghost shortlist-task-btn" data-task-id="${task.id}">${
            shortlistedTasks.has(task.id) ? "Shortlisted" : "Shortlist"
          }</button>
          <button class="btn btn-primary open-task-btn" data-task-id="${task.id}">Open task</button>
        </div>
      </article>`;
    })
    .join("");

  document.querySelectorAll(".task-card").forEach((card) => {
    const taskId = card.dataset.taskId;
    card.addEventListener("click", () => openTaskModal(taskId));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openTaskModal(taskId);
      }
    });
  });

  document.querySelectorAll(".open-task-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      openTaskModal(button.dataset.taskId);
    });
  });
  document.querySelectorAll(".shortlist-task-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const taskId = button.dataset.taskId;
      if (shortlistedTasks.has(taskId)) {
        shortlistedTasks.delete(taskId);
      } else {
        shortlistedTasks.add(taskId);
      }
      saveShortlist();
      renderTaskCards(tasks);
    });
  });
}

async function renderTasks() {
  taskList.innerHTML = `<article class="card"><p>Loading tasks...</p></article>`;
  try {
    cachedTasks = await fetchTasks(selectedLanguage);
    renderTaskCards(cachedTasks);
  } catch {
    taskList.innerHTML = `<article class="card"><p>API unavailable. Start backend server to load tasks.</p></article>`;
  }
}

function updateCodeLineNumbers() {
  const lines = (codeInput.value.match(/\n/g)?.length || 0) + 1;
  codeLineNumbers.textContent = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
}

function extensionOf(fileName) {
  const index = fileName.lastIndexOf(".");
  return index >= 0 ? fileName.slice(index).toLowerCase() : "";
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function renderAttachmentSelection() {
  if (!submissionFilesList) return;
  if (!pendingAttachments.length) {
    submissionFilesList.innerHTML = `<p class="section-note">No files selected.</p>`;
    return;
  }
  submissionFilesList.innerHTML = pendingAttachments
    .map(
      (file, index) => `
      <div class="submission-file-item">
        <span>${file.name} • ${formatBytes(file.size)}</span>
        <button type="button" class="btn btn-ghost remove-submission-file-btn" data-file-index="${index}">Remove</button>
      </div>`
    )
    .join("");
  document.querySelectorAll(".remove-submission-file-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.fileIndex || "-1");
      if (!Number.isNaN(index) && index >= 0) {
        pendingAttachments.splice(index, 1);
        renderAttachmentSelection();
      }
    });
  });
}

function validateAttachmentSelection(newFiles) {
  if (pendingAttachments.length + newFiles.length > MAX_ATTACHMENTS) {
    throw new Error(`You can upload up to ${MAX_ATTACHMENTS} attachments.`);
  }
  for (const file of newFiles) {
    if (file.size > MAX_ATTACHMENT_BYTES) {
      throw new Error(`${file.name} is larger than 5MB.`);
    }
    const ext = extensionOf(file.name);
    if (!ALLOWED_ATTACHMENT_EXTENSIONS.has(ext)) {
      throw new Error(`${file.name} has an unsupported file type.`);
    }
  }
}

async function openTaskModal(taskId) {
  try {
    const task = await fetchTask(taskId);
    activeTask = task;
    taskModalTitle.textContent = task.title;
    taskModalReward.textContent = `$${Number(task.reward).toFixed(2)}`;
    taskModalId.textContent = formatTaskId(task.id);
    taskModalDescription.textContent = task.description;
    taskModalEndpoints.textContent = task.context.endpoints;
    taskModalLayout.textContent = task.context.layout;
    taskModalRun.textContent = task.context.run;
    const requiredLanguage = deriveTaskLanguage(task);
    taskModalLanguage.textContent = requiredLanguage || "Set by startup";
    if (confirmLanguageFitLabel) confirmLanguageFitLabel.textContent = (requiredLanguage || "this task language").toLowerCase();
    taskModalStatus.className = `status-pill ${statusClass(task.status)}`;
    taskModalStatus.textContent = statusLabel(task.status);
    thinkingInput.value = "";
    codeInput.value = "";
    if (confirmLanguageFit) {
      confirmLanguageFit.checked = false;
      const confirmWrap = confirmLanguageFit.closest(".language-confirm");
      const mustMatchLanguage = !!requiredLanguage;
      confirmLanguageFit.required = mustMatchLanguage;
      if (confirmWrap) confirmWrap.classList.toggle("hidden", !mustMatchLanguage);
    }
    if (submissionLanguageUsed) {
      const options = Array.from(submissionLanguageUsed.options).map((option) => option.value);
      const target = task.language && options.includes(task.language) ? task.language : "";
      submissionLanguageUsed.value = target;
    }
    pendingAttachments = [];
    if (submissionFilesInput) submissionFilesInput.value = "";
    renderAttachmentSelection();
    updateCodeLineNumbers();
    taskModal.classList.remove("hidden");
  } catch {
    alert("Could not load task details from API.");
  }
}

function closeTaskModal() {
  taskModal.classList.add("hidden");
  activeTask = null;
}

taskSubmitForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const session = loadSession();
  if (!session || !activeTask) return;

  const thinking = thinkingInput.value.trim();
  const code = codeInput.value.trim();
  const selectedLanguage = submissionLanguageUsed?.value?.trim() || "";
  const requiredLanguage = deriveTaskLanguage(activeTask);
  if (thinking.length < 20 || code.length < 12) {
    alert("Please provide both your thinking process and code.");
    return;
  }
  if (!selectedLanguage) {
    alert("Please select the programming language used in your code.");
    return;
  }
  if (requiredLanguage && selectedLanguage.toLowerCase() !== requiredLanguage.toLowerCase()) {
    alert(`This task requires ${requiredLanguage}. Please submit code in ${requiredLanguage}.`);
    return;
  }
  if (confirmLanguageFit && confirmLanguageFit.required && !confirmLanguageFit.checked) {
    alert(`Please confirm your submission matches the required programming language (${activeTask.language || "required language"}).`);
    return;
  }

  try {
    const response = await createSubmission({
      taskId: activeTask.id,
      contributorId: session.userId,
      contributorName: session.fullName,
      thinking,
      code,
    });
    const submissionId = Number(response?.submissionId || 0);
    if (pendingAttachments.length && submissionId > 0) {
      await uploadSubmissionAttachments(submissionId, pendingAttachments);
    }
    const submissions = JSON.parse(localStorage.getItem(SUBMISSIONS_DB_KEY) || "[]");
    submissions.push({
      id: submissionId || response?.submissionId || `SUB-${Date.now()}`,
      taskId: activeTask.id,
      contributorId: session.userId,
      contributorName: session.fullName,
      taskReward: Number(activeTask.reward || 0),
      status: "under_review",
      reviewNote: "",
      rejectionReason: "",
      payoutRate: 0,
      submittedLanguage: selectedLanguage,
      attachments: pendingAttachments.map((file) => ({ fileName: file.name, sizeBytes: file.size })),
      submittedAt: new Date().toISOString(),
    });
    localStorage.setItem(SUBMISSIONS_DB_KEY, JSON.stringify(submissions));
    alert("Submission sent for review.");
    closeTaskModal();
    await renderTasks();
  } catch {
    alert("Submission failed. Check your account role/session and make sure backend API is running.");
  }
});

submissionFilesInput?.addEventListener("change", () => {
  const files = Array.from(submissionFilesInput.files || []);
  if (!files.length) return;
  try {
    validateAttachmentSelection(files);
    pendingAttachments.push(...files);
    renderAttachmentSelection();
  } catch (error) {
    alert(error?.message || "Invalid file selection.");
  } finally {
    submissionFilesInput.value = "";
  }
});

closeTaskModalBtn.addEventListener("click", closeTaskModal);
taskModal.addEventListener("click", (event) => {
  if (event.target === taskModal) closeTaskModal();
});

codeInput.addEventListener("input", updateCodeLineNumbers);
codeInput.addEventListener("scroll", () => {
  codeLineNumbers.scrollTop = codeInput.scrollTop;
});
codeInput.addEventListener("keydown", (event) => {
  if (event.key === "Tab") {
    event.preventDefault();
    const start = codeInput.selectionStart;
    const end = codeInput.selectionEnd;
    codeInput.value = `${codeInput.value.slice(0, start)}  ${codeInput.value.slice(end)}`;
    codeInput.selectionStart = codeInput.selectionEnd = start + 2;
    updateCodeLineNumbers();
  }
});

languageFilter.addEventListener("change", async (event) => {
  selectedLanguage = event.target.value;
  await renderTasks();
});

renderNavbar();
sessionStorage.setItem(LAST_PAGE_KEY, "./tasks.html");
setBrandLinkTarget();
loadShortlist();
renderTasks();
updateCodeLineNumbers();
renderAttachmentSelection();
