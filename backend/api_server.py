from __future__ import annotations

import json
import hashlib
import hmac
import mimetypes
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request as UrlRequest, urlopen
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
import bcrypt
try:
    import stripe
except Exception:
    stripe = None
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
except Exception:
    sentry_sdk = None

load_dotenv()


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(50))
    reward: Mapped[float] = mapped_column(Float, default=1.0)
    slots: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="open")
    summary: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    endpoints: Mapped[str] = mapped_column(Text)
    layout: Mapped[str] = mapped_column(Text)
    run_instructions: Mapped[str] = mapped_column(Text)
    startup_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class SubmissionRecord(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(20))
    contributor_id: Mapped[int] = mapped_column(Integer)
    contributor_name: Mapped[str] = mapped_column(String(255))
    thinking: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="under_review")
    dispute: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_detection_confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payout_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    startup_feedback_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    startup_feedback_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    startup_feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    startup_feedback_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SubmissionAttachmentRecord(Base):
    __tablename__ = "submission_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(Integer)
    file_name: Mapped[str] = mapped_column(String(255))
    storage_name: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PayoutRequestRecord(Base):
    __tablename__ = "payout_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer)
    amount: Mapped[float] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(30))  # stripe | paypal
    destination_ref: Mapped[str] = mapped_column(String(255))
    provider_payout_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WebhookEventRecord(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(30))
    event_id: Mapped[str] = mapped_column(String(120))
    payload: Mapped[str] = mapped_column(Text)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserAuthRecord(Base):
    __tablename__ = "auth_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="contributor")
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SessionTokenRecord(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer)
    token: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))


class PaymentReceiptRecord(Base):
    __tablename__ = "payment_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payout_request_id: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(30))
    provider_reference: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Float)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PaymentMethodRecord(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer)
    method_type: Mapped[str] = mapped_column(String(30))  # paypal | card
    provider: Mapped[str] = mapped_column(String(30))  # paypal | stripe
    provider_token: Mapped[str] = mapped_column(String(120))
    card_brand: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    card_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    cardholder_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    exp_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exp_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AdminAuditLogRecord(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_user_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(120))
    target_type: Mapped[str] = mapped_column(String(80))
    target_ref: Mapped[str] = mapped_column(String(120))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalyticsEventRecord(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_name: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(40), default="web")
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StartupRecord(Base):
    __tablename__ = "startups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True)
    company_name: Mapped[str] = mapped_column(String(255))
    website_url: Mapped[str] = mapped_column(String(255))
    industry: Mapped[str] = mapped_column(String(120))
    product_stage: Mapped[str] = mapped_column(String(80), default="idea")
    tech_stack: Mapped[str] = mapped_column(Text, default="")
    team_size: Mapped[int] = mapped_column(Integer, default=1)
    squad_summary: Mapped[str] = mapped_column(Text)
    intentions: Mapped[str] = mapped_column(Text)
    tasks_posted: Mapped[int] = mapped_column(Integer, default=0)
    number_of_tasks: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending | approved | rejected
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StartupTaskRequestRecord(Base):
    __tablename__ = "startup_task_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    startup_id: Mapped[int] = mapped_column(Integer)
    startup_user_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(80))
    reward: Mapped[float] = mapped_column(Float)
    details: Mapped[str] = mapped_column(Text)
    acceptance_rules: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending | approved | rejected
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_to_tasks: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StartupTaskDeletionRequestRecord(Base):
    __tablename__ = "startup_task_deletion_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(20))
    startup_id: Mapped[int] = mapped_column(Integer)
    startup_user_id: Mapped[int] = mapped_column(Integer)
    startup_name: Mapped[str] = mapped_column(String(255))
    admin_user_id: Mapped[int] = mapped_column(Integer)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending | approved | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskOut(BaseModel):
    id: str
    title: str
    type: str
    reward: float
    slots: str
    status: str
    startup_name: str
    summary: str
    description: str
    context: dict[str, str]


class SubmissionIn(BaseModel):
    taskId: str
    contributorId: int
    contributorName: str
    thinking: str = Field(min_length=20)
    code: str = Field(min_length=12)


class SubmissionOut(BaseModel):
    id: int
    taskId: str
    contributorId: int
    contributorName: str
    thinking: str
    code: str
    status: str
    dispute: Optional[str]
    reviewNote: Optional[str]
    rejectionReason: Optional[str]
    aiDetectionConfidence: Optional[int]
    payoutRate: Optional[float]
    reviewedAt: Optional[datetime]
    startupFeedbackRating: Optional[int]
    startupFeedbackNote: Optional[str]
    startupFeedbackAt: Optional[datetime]
    attachments: list["SubmissionAttachmentOut"] = Field(default_factory=list)
    submittedAt: datetime


class SubmissionAttachmentOut(BaseModel):
    id: int
    fileName: str
    contentType: str
    sizeBytes: int
    createdAt: datetime


class SubmissionReviewIn(BaseModel):
    status: str = Field(pattern="^(approved|partial_approved|rejected)$")
    reviewNote: Optional[str] = None
    rejectionReason: Optional[str] = None
    aiDetectionConfidence: Optional[int] = Field(default=None, ge=0, le=100)


class StartupSubmissionFeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    note: Optional[str] = None


class PayoutRequestIn(BaseModel):
    userId: int
    amount: float = Field(gt=0)
    provider: str = Field(pattern="^(stripe|paypal)$")
    destinationRef: str = Field(min_length=4)


class PayoutRequestOut(BaseModel):
    id: int
    userId: int
    amount: float
    provider: str
    destinationRef: str
    providerPayoutId: Optional[str] = None
    status: str
    createdAt: datetime


class PayoutStatusUpdateIn(BaseModel):
    status: str = Field(pattern="^(paid|rejected|pending)$")
    providerPayoutId: Optional[str] = None


class WebhookIn(BaseModel):
    eventId: str
    payoutRequestId: Optional[int] = None
    providerPayoutId: Optional[str] = None
    status: Optional[str] = None
    payload: dict


class TaskImportIn(BaseModel):
    sourceUrl: str = Field(min_length=10)


class TaskImportOut(BaseModel):
    imported: int
    updated: int
    sourceUrl: str


class SignupIn(BaseModel):
    fullName: str = Field(min_length=2)
    email: str = Field(min_length=5)
    password: str = Field(min_length=8)
    role: str = Field(pattern="^(contributor|startup|admin)$")
    adminCode: Optional[str] = None


class LoginIn(BaseModel):
    email: str
    password: str


class AuthOut(BaseModel):
    token: str
    userId: int
    fullName: str
    email: str
    role: str
    profileCompleted: bool


class ProfileCompletionIn(BaseModel):
    profileCompleted: bool = True


class ReceiptOut(BaseModel):
    id: int
    payoutRequestId: int
    userId: int
    provider: str
    providerReference: str
    amount: float
    issuedAt: datetime


class PaymentMethodIn(BaseModel):
    methodType: str = Field(pattern="^(paypal|card)$")
    paypalEmail: Optional[str] = None
    stripePaymentMethodId: Optional[str] = None
    billingEmail: Optional[str] = None
    cardholderName: Optional[str] = None


class PaymentMethodOut(BaseModel):
    id: int
    userId: int
    methodType: str
    provider: str
    providerToken: str
    cardBrand: Optional[str]
    cardLast4: Optional[str]
    cardholderName: Optional[str]
    expMonth: Optional[int]
    expYear: Optional[int]
    billingEmail: Optional[str]
    createdAt: datetime


class StripeConfigOut(BaseModel):
    publishableKey: str


class StripeSetupIntentOut(BaseModel):
    clientSecret: str
    setupIntentId: str


class AnalyticsEventIn(BaseModel):
    event: str = Field(min_length=2, max_length=120)
    source: str = Field(default="web", min_length=2, max_length=40)
    userId: Optional[int] = None
    role: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class OverviewMetricsOut(BaseModel):
    todayAverageEarnings: float
    averageReviewHours: float
    tasksApprovedToday: int


class StartupRegistrationIn(BaseModel):
    companyName: str = Field(min_length=2)
    websiteUrl: str = Field(min_length=8)
    industry: str = Field(min_length=2)
    productStage: str = Field(min_length=2)
    techStack: str = Field(min_length=2)
    teamSize: int = Field(ge=1, le=5000)
    squadSummary: str = Field(min_length=10)
    intentions: str = Field(min_length=20)


class StartupOut(BaseModel):
    id: int
    userId: int
    companyName: str
    websiteUrl: str
    industry: str
    productStage: str
    techStack: str
    teamSize: int
    squadSummary: str
    intentions: str
    tasksPosted: int
    numberOfTasks: int
    status: str
    reviewNote: Optional[str]
    createdAt: datetime
    updatedAt: datetime


class StartupReviewIn(BaseModel):
    status: str = Field(pattern="^(approved|rejected|pending)$")
    reviewNote: Optional[str] = None


class StartupTaskRequestIn(BaseModel):
    title: str = Field(min_length=4)
    language: str = Field(min_length=2)
    reward: float = Field(gt=0)
    details: str = Field(min_length=20)
    acceptanceRules: str = Field(min_length=12)


class StartupTaskRequestOut(BaseModel):
    id: int
    startupId: int
    startupUserId: int
    title: str
    language: str
    reward: float
    details: str
    acceptanceRules: str
    status: str
    adminNote: Optional[str]
    publishedToTasks: bool
    createdAt: datetime
    updatedAt: datetime


class StartupTaskRequestReviewIn(BaseModel):
    status: str = Field(pattern="^(approved|rejected|pending)$")
    adminNote: Optional[str] = None
    publishToTasks: bool = False


class StartupTaskDeletionRequestOut(BaseModel):
    id: int
    taskId: str
    startupId: int
    startupUserId: int
    startupName: str
    adminUserId: int
    note: Optional[str]
    status: str
    createdAt: datetime
    updatedAt: datetime


class StartupTaskDeletionReviewIn(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    note: Optional[str] = None


class AdminTaskCreateIn(BaseModel):
    id: Optional[str] = None
    title: str = Field(min_length=4)
    language: str = Field(min_length=2)
    reward: float = Field(gt=0)
    status: str = Field(min_length=2)
    startupName: Optional[str] = None
    summary: str = Field(min_length=8)
    description: str = Field(min_length=20)
    endpoints: str = Field(min_length=2)
    layout: str = Field(min_length=2)
    runInstructions: str = Field(min_length=2)


class AdminTaskUpdateIn(BaseModel):
    title: Optional[str] = None
    language: Optional[str] = None
    reward: Optional[float] = Field(default=None, gt=0)
    status: Optional[str] = None
    startupName: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    endpoints: Optional[str] = None
    layout: Optional[str] = None
    runInstructions: Optional[str] = None


class AdminUserOut(BaseModel):
    id: int
    email: str
    fullName: str
    role: str
    profileCompleted: bool
    isActive: bool
    createdAt: datetime


class AdminUserUpdateIn(BaseModel):
    role: Optional[str] = Field(default=None, pattern="^(contributor|startup|admin)$")
    profileCompleted: Optional[bool] = None
    isActive: Optional[bool] = None


class AdminAnalyticsOverviewOut(BaseModel):
    eventsLast24h: int
    signupsLast24h: int
    loginsLast24h: int
    submissionsLast24h: int
    payoutRequestsLast24h: int
    startupTaskRequestsLast24h: int


class AdminUserOverviewOut(BaseModel):
    userId: int
    email: str
    fullName: str
    role: str
    isActive: bool
    profileCompleted: bool
    lastLoginAt: Optional[datetime]
    submissionsCount: int
    pendingSubmissions: int
    approvedSubmissions: int
    partialApprovedSubmissions: int
    rejectedSubmissions: int
    payoutRequestsCount: int
    paidPayoutRequests: int
    pendingPayoutRequests: int
    startupCompanyName: Optional[str]
    startupStatus: Optional[str]
    startupTasksPosted: int


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_DB_URL = f"sqlite:///{(BASE_DIR / 'appcontributor.db').as_posix()}"
DB_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_DB_URL).strip() or DEFAULT_SQLITE_DB_URL
engine = create_engine(DB_URL, future=True)
UPLOADS_BASE_DIR = (BASE_DIR / "uploads" / "submissions").resolve()
MAX_SUBMISSION_ATTACHMENT_BYTES = int(os.getenv("MAX_SUBMISSION_ATTACHMENT_BYTES", str(5 * 1024 * 1024)))
MAX_SUBMISSION_ATTACHMENTS_PER_SUBMISSION = int(os.getenv("MAX_SUBMISSION_ATTACHMENTS_PER_SUBMISSION", "5"))
ALLOWED_SUBMISSION_ATTACHMENT_EXTENSIONS = {
    ".py",
    ".pdf",
    ".txt",
    ".md",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
}
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500,http://[::1]:5500",
    ).split(",")
    if origin.strip()
]
SESSION_TTL_HOURS = max(1, int(os.getenv("SESSION_TTL_HOURS", "168")))
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "appcontributor_session")
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "0") == "1"
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax")
AUTH_CSRF_COOKIE_NAME = os.getenv("AUTH_CSRF_COOKIE_NAME", "appcontributor_csrf")
ADMIN_BOOTSTRAP_EMAIL = os.getenv("ADMIN_BOOTSTRAP_EMAIL", "admin@appcontributor.local").strip().lower()
ADMIN_BOOTSTRAP_PASSWORD = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "").strip()
ADMIN_BOOTSTRAP_NAME = os.getenv("ADMIN_BOOTSTRAP_NAME", "Platform Admin").strip()
ALLOW_ADMIN_BOOTSTRAP = os.getenv("ALLOW_ADMIN_BOOTSTRAP", "0") == "1"

RATE_LIMIT_BUCKET: dict[str, list[float]] = {}
RATE_LIMIT_RULES = {
    "auth_login": (8, 60.0),
    "auth_signup": (6, 60.0),
    "payout_create": (10, 60.0),
    "payment_method_create": (15, 60.0),
}
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://app.posthog.com").rstrip("/")
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "").strip()
SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
PAYPAL_WEBHOOK_TOKEN = os.getenv("PAYPAL_WEBHOOK_TOKEN", "").strip()
ANALYTICS_METADATA_ALLOWED_KEYS = {
    "accessPath",
    "action",
    "taskId",
    "taskStatus",
    "taskLanguage",
    "taskReward",
    "view",
    "result",
}
ANALYTICS_METADATA_MAX_CHARS = 512
MAX_BCRYPT_PASSWORD_BYTES = 72
FINAL_SUBMISSION_STATUSES = {"approved", "partial_approved", "rejected"}

app = FastAPI(title="AppContributor API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Auth-Token", "X-CSRF-Token"],
)

if sentry_sdk is not None and SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        environment=os.getenv("APP_ENV", "development"),
    )


@app.middleware("http")
async def propagate_auth_cookie(request: Request, call_next):
    if "authorization" not in request.headers and "x-auth-token" not in request.headers:
        cookie_token = request.cookies.get(AUTH_COOKIE_NAME, "").strip()
        if cookie_token:
            request.scope["headers"] = list(request.scope.get("headers", [])) + [
                (b"x-auth-token", cookie_token.encode("utf-8"))
            ]
    return await call_next(request)


@app.middleware("http")
async def csrf_protect_mutations(request: Request, call_next):
    if request.method in {"POST", "PATCH", "DELETE"} and request.url.path.startswith("/api/"):
        csrf_exempt = {
            "/api/auth/login",
            "/api/auth/signup",
            "/api/auth/logout",
            "/api/webhooks/stripe",
            "/api/webhooks/paypal",
        }
        if request.url.path not in csrf_exempt:
            origin = request.headers.get("origin", "").strip()
            if origin and origin not in CORS_ALLOW_ORIGINS:
                return Response(status_code=403, content="Invalid origin")
            # If explicit auth header token is present, the request is not CSRF-able in the same way as cookie auth.
            auth_header = request.headers.get("authorization", "").strip()
            x_auth_header = request.headers.get("x-auth-token", "").strip()
            if auth_header.lower().startswith("bearer ") or x_auth_header:
                return await call_next(request)
            cookie_session = request.cookies.get(AUTH_COOKIE_NAME, "").strip()
            if cookie_session:
                csrf_cookie = request.cookies.get(AUTH_CSRF_COOKIE_NAME, "").strip()
                csrf_header = request.headers.get("x-csrf-token", "").strip()
                if not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
                    return Response(status_code=403, content="CSRF token mismatch")
    return await call_next(request)


def slots_for_reward(reward: float) -> str:
    # Enforce platform rule: easier/low-pay tasks get 5 total slots, harder/higher-pay tasks get 2 total slots.
    return "5/5" if reward <= 2.0 else "2/2"


SEED_TASKS = [
    {
        "id": "PB-101",
        "title": "Fix GET /activities timeout",
        "language": "Python",
        "reward": 2.0,
        "slots": slots_for_reward(2.0),
        "status": "open",
        "summary": "Debug timeout under concurrent requests.",
        "description": (
            "RunBetter is a beta health and sports app that helps users track weekly running goals and pace trends. "
            "The team implemented a backend flow that fetches recent activities and computes summary metrics for the dashboard. "
            "They started seeing timeout errors on the activities endpoint when multiple users query at once. "
            "Your task is to analyze whether the issue comes from query logic, aggregation math, or implementation mistakes and propose a sensible first solution. "
            "A partial but well-reasoned fix path is acceptable."
        ),
        "endpoints": "GET /api/activities\nPOST /api/activities",
        "layout": "backend/api/activity_routes.py\nbackend/service/activity_service.py",
        "run_instructions": "python app.py",
    },
    {
        "id": "PB-104",
        "title": "Write DFS on binary info graph",
        "language": "Python",
        "reward": 1.0,
        "slots": slots_for_reward(1.0),
        "status": "open",
        "summary": "Implement DFS traversal for feature graph.",
        "description": (
            "InsightTree is a product analytics app that maps binary decision branches in onboarding flows. "
            "Developers already modeled the graph nodes and links, but traversal logic remains inconsistent across modules. "
            "In deeper branches the current approach skips nodes or revisits them unexpectedly. "
            "Your task is to implement a clean DFS utility with deterministic visit order and code that can be reused by the graph analysis service. "
            "If you can only complete part of the traversal path, submit the best coherent implementation you can."
        ),
        "endpoints": "N/A (algorithm module)",
        "layout": "backend/algorithms/graph_traversal.py",
        "run_instructions": "pytest tests/test_graph.py -q",
    },
    {
        "id": "PB-105",
        "title": "Write BFS on binary info graph",
        "language": "Java",
        "reward": 1.0,
        "slots": slots_for_reward(1.0),
        "status": "open",
        "summary": "Implement BFS traversal and level output.",
        "description": (
            "ClassPath is an education startup that recommends learning paths based on prerequisite graphs. "
            "The team implemented graph structures in Java and can store course dependency nodes. "
            "They are blocked because they cannot reliably generate level-by-level traversal for recommendation ordering. "
            "Your task is to implement BFS with queue logic and return both visit order and grouped levels. "
            "Innovative alternatives that still make technical sense are welcome."
        ),
        "endpoints": "N/A (service utility)",
        "layout": "backend/src/main/java/algorithms/GraphUtils.java",
        "run_instructions": "./gradlew test",
    },
    {
        "id": "PB-106",
        "title": "Improve sorting algorithm",
        "language": "C++",
        "reward": 1.0,
        "slots": slots_for_reward(1.0),
        "status": "open",
        "summary": "Replace bubble sort with a faster sort.",
        "description": (
            "DealRadar is a startup platform that ranks opportunities by urgency and expected ROI. "
            "The current ranking engine still uses a prototype bubble sort that worked only on tiny datasets. "
            "As data volume increased, ranking updates became visibly slow and users see stale ordering. "
            "Your task is to replace the sorting strategy with a faster algorithm (quick sort or merge sort) and provide implementation notes. "
            "A practical improvement over the current version is enough for initial approval."
        ),
        "endpoints": "N/A",
        "layout": "core/ranking/sort_engine.cpp",
        "run_instructions": "cmake --build . && ctest -R ranking",
    },
    {
        "id": "PB-110",
        "title": "Ruby background job retry handler",
        "language": "Ruby",
        "reward": 1.0,
        "slots": slots_for_reward(1.0),
        "status": "open",
        "summary": "Add retry and backoff for failed jobs.",
        "description": (
            "NotifyLoop is a reminder app that sends scheduled notifications through Ruby background workers. "
            "The team already implemented a Sidekiq worker pipeline for dispatching outbound reminder jobs. "
            "When transient API/network failures happen, jobs fail immediately and are lost without controlled retries. "
            "Your task is to add a retry/backoff strategy with clearer error logging so the system can recover safely. "
            "A partial retry design that is technically correct can still be approved."
        ),
        "endpoints": "POST /api/reminders",
        "layout": "backend/jobs/reminder_worker.rb",
        "run_instructions": "bundle exec sidekiq",
    },
    {
        "id": "PB-111",
        "title": "Fix staging-only 422 validation on workflow form submit",
        "language": "TypeScript",
        "reward": 3.0,
        "slots": slots_for_reward(3.0),
        "status": "open",
        "summary": "Staging users submit prompts but backend rejects payload shape.",
        "description": (
            "PromptForge is a small AI workflow app where non-technical users build content pipelines from templates. "
            "A new schema rollout broke the staging form submit flow, returning 422 for malformed payloads. "
            "Your task is restricted to staging behavior and schema alignment; do not touch production billing or auth code. "
            "Implement the smallest safe fix path so startup QA can validate before any production promotion. "
            "A clear partial solution (for example fixing core required fields first) is acceptable."
        ),
        "endpoints": "POST /staging/api/workflows/run\nGET /staging/api/workflows/schema",
        "layout": "frontend/src/features/run-workflow/SubmitPanel.tsx\nbackend/api/workflows_staging.py",
        "run_instructions": "npm run dev && uvicorn backend.main:app --reload",
    },
    {
        "id": "PB-112",
        "title": "Stabilize staging OpenAI retry queue (non-production)",
        "language": "Python",
        "reward": 4.0,
        "slots": slots_for_reward(4.0),
        "status": "open",
        "summary": "Staging retry queue duplicates jobs after 429 bursts.",
        "description": (
            "ReplyPilot is an AI support assistant that drafts first responses for help-desk agents. "
            "In staging, retry workers duplicate jobs during 429 bursts. "
            "Your task is limited to staging worker logic and must not alter live traffic or production queue config. "
            "Make retry handling safer with idempotency or deduping logic and keep behavior observable in logs. "
            "If you can only patch the most likely duplicate path first, that is still valuable."
        ),
        "endpoints": "POST /staging/api/replies/generate\nPOST /staging/api/retries/process",
        "layout": "backend/workers/retry_worker_staging.py\nbackend/services/reply_service.py",
        "run_instructions": "python -m backend.workers.retry_worker",
    },
    {
        "id": "PB-113",
        "title": "Prevent duplicate credits in sandbox billing webhooks",
        "language": "Go",
        "reward": 5.0,
        "slots": slots_for_reward(5.0),
        "status": "open",
        "summary": "Sandbox billing webhook can credit wallet more than once.",
        "description": (
            "BuildLane sells usage credits for a developer tool and tests billing in Stripe sandbox mode. "
            "Support reports sandbox users got credits twice when Stripe retried the same event during network instability. "
            "Your task is to add idempotency checks around sandbox webhook processing only; production payout release remains out of scope. "
            "Keep normal successful top-ups unchanged. "
            "A focused fix for duplicate-event handling is enough for initial approval."
        ),
        "endpoints": "POST /billing/sandbox/webhook/stripe\nGET /billing/sandbox/wallet/:userId",
        "layout": "services/billing/webhook_handler_sandbox.go\nservices/billing/wallet_store.go",
        "run_instructions": "go test ./... && go run ./cmd/billing-api",
    },
    {
        "id": "PB-114",
        "title": "Fix staging board stale cache after task update",
        "language": "JavaScript",
        "reward": 2.5,
        "slots": slots_for_reward(2.5),
        "status": "open",
        "summary": "Staging UI still shows old task state after save.",
        "description": (
            "SprintMint is a planning app where product teams update small engineering tasks and priorities in real time. "
            "The staging frontend uses React Query and optimistic updates, but cards revert to old values until hard refresh. "
            "Your task is to trace the stale-cache path and apply a safe invalidation or merge strategy in staging. "
            "Do not modify production deploy settings or live data migrations. "
            "A partial fix targeting the most common update flow is still useful."
        ),
        "endpoints": "PATCH /staging/api/tasks/:id\nGET /staging/api/tasks",
        "layout": "frontend/src/features/tasks/hooks/useTaskMutations.js\nfrontend/src/features/tasks/TaskBoard.jsx",
        "run_instructions": "npm run dev",
    },
    {
        "id": "PB-115",
        "title": "Repair staging SQL migration for nullable profile fields",
        "language": "Database",
        "reward": 3.5,
        "slots": slots_for_reward(3.5),
        "status": "open",
        "summary": "Migration fails on staging rows with null bios.",
        "description": (
            "CreatorNest is an AI portfolio platform where users publish project pages generated from prompts and manual edits. "
            "A staging migration that splits profile metadata into a new table fails because legacy rows have null values. "
            "Your task is to design a safe migration sequence in staging (or rollback + forward plan) that handles null data without profile loss. "
            "Production migration execution is explicitly out of scope. "
            "Even if you only provide a safe phased migration with SQL snippets, that can be approved."
        ),
        "endpoints": "N/A (staging migration task)",
        "layout": "backend/db/migrations/staging/2026_05_profile_refactor.sql",
        "run_instructions": "alembic upgrade head",
    },
    {
        "id": "PB-116",
        "title": "Fix staging CORS preflight blocked on contributor submit",
        "language": "JavaScript",
        "reward": 2.0,
        "slots": slots_for_reward(2.0),
        "status": "open",
        "summary": "Staging OPTIONS request fails before submission reaches API.",
        "description": (
            "TaskBloom is a lightweight contributor portal used by startup founders to collect fast technical fixes. "
            "The staging frontend is hosted on a different domain than the staging API and submissions fail in-browser. "
            "Users see a network error even though the endpoint is healthy with curl. "
            "Your task is to fix staging CORS/preflight handling without weakening security. "
            "A practical first fix that unblocks the main submit path is acceptable."
        ),
        "endpoints": "OPTIONS /staging/api/submissions\nPOST /staging/api/submissions",
        "layout": "backend/main_staging.py\nfrontend/src/api/client.js",
        "run_instructions": "npm run dev && uvicorn backend.main:app --reload",
    },
    {
        "id": "PB-117",
        "title": "Handle missing OPENAI_API_KEY in staging without crash",
        "language": "Python",
        "reward": 1.5,
        "slots": slots_for_reward(1.5),
        "status": "open",
        "summary": "Staging app boots with traceback when env variable is absent.",
        "description": (
            "IdeaMate helps founders brainstorm product plans with AI-generated outlines and user stories. "
            "The staging app crashes during startup when OPENAI_API_KEY is missing. "
            "Your task is to add defensive config handling and friendly error messaging in staging mode only. "
            "Do not change production secret managers or release pipelines. "
            "Even a partial patch that improves startup messaging and avoids hard crashes can be approved."
        ),
        "endpoints": "GET /staging/api/health\nPOST /staging/api/ideas/generate",
        "layout": "backend/config/settings.py\nbackend/services/llm_client_staging.py",
        "run_instructions": "python -m backend.app",
    },
    {
        "id": "PB-118",
        "title": "Fix staging 401 on profile fetch due to auth header format",
        "language": "TypeScript",
        "reward": 2.0,
        "slots": slots_for_reward(2.0),
        "status": "open",
        "summary": "Staging token exists but API rejects malformed Authorization header.",
        "description": (
            "CrewBoard is an internal ops app where contributors track accepted tasks and weekly payouts. "
            "After a recent frontend refactor, staging profile requests return 401 for logged-in users. "
            "QA found tokens in local storage, yet backend logs suggest malformed Authorization headers in some flows. "
            "Your task is to normalize header handling in staging and confirm profile requests remain authenticated after refresh. "
            "A focused fix for the most common login path is still useful."
        ),
        "endpoints": "POST /staging/api/auth/login\nGET /staging/api/me",
        "layout": "frontend/src/auth/session.ts\nfrontend/src/api/http.ts",
        "run_instructions": "npm run dev",
    },
    {
        "id": "PB-119",
        "title": "Correct internal cron timezone for daily payout summary",
        "language": "Go",
        "reward": 2.5,
        "slots": slots_for_reward(2.5),
        "status": "open",
        "summary": "Internal daily report runs at wrong local hour for admins.",
        "description": (
            "PayOrbit sends founders a daily payout summary from an internal reporting worker. "
            "The team scheduled a cron job expecting 18:00 local business time, but it runs hours off due to timezone mismatch. "
            "Your task is to correct worker scheduling behavior and document the timezone strategy in internal docs. "
            "No production infra changes should be performed in this task. "
            "A straightforward and testable fix to align execution time is enough."
        ),
        "endpoints": "N/A (scheduled worker)",
        "layout": "services/reports/scheduler.go\nservices/reports/daily_summary.go",
        "run_instructions": "go run ./cmd/reports-worker",
    },
    {
        "id": "PB-120",
        "title": "Guard sandbox webhook JSON parsing for malformed payload",
        "language": "Node.js",
        "reward": 2.0,
        "slots": slots_for_reward(2.0),
        "status": "open",
        "summary": "Sandbox webhook endpoint throws when body is invalid JSON.",
        "description": (
            "SignalDock aggregates event callbacks from third-party tools and forwards them to startup dashboards. "
            "A partner integration occasionally sends malformed JSON to the sandbox webhook path, crashing the handler. "
            "This creates noisy logs and sometimes delays valid events arriving right after bad ones. "
            "Your task is to add safer parsing/error responses for sandbox webhooks and keep valid events processing normally. "
            "A minimal but robust guard around parse failures is acceptable for approval."
        ),
        "endpoints": "POST /sandbox/webhooks/events",
        "layout": "api/routes/webhooks_sandbox.js\napi/middleware/rawBodyParser.js",
        "run_instructions": "npm run start:api",
    },
    {
        "id": "PB-121",
        "title": "Create staging seed-data reset script for QA",
        "language": "Python",
        "reward": 1.5,
        "slots": slots_for_reward(1.5),
        "status": "open",
        "summary": "Build a safe script to reset and re-seed staging data for QA cycles.",
        "description": (
            "NovaBoard is a startup building an internal operations backend. "
            "QA needs a one-command way to reset staging data before regression runs. "
            "Your task is to add a safe staging-only seed/reset script and basic logging for what records are recreated. "
            "The script must never point to production databases. "
            "A practical script with guard checks is enough for approval."
        ),
        "endpoints": "N/A (internal script)",
        "layout": "backend/scripts/reset_staging_data.py\nbackend/scripts/seed_staging_data.py",
        "run_instructions": "python backend/scripts/reset_staging_data.py --env staging",
    },
    {
        "id": "PB-122",
        "title": "Add internal admin CSV export for staging support tickets",
        "language": "JavaScript",
        "reward": 2.0,
        "slots": slots_for_reward(2.0),
        "status": "open",
        "summary": "Create CSV export endpoint used by internal support tooling only.",
        "description": (
            "PulseDesk is building an internal support dashboard and ops needs quick CSV exports from staging ticket data. "
            "Your task is to add a simple internal endpoint and frontend button for CSV export with date-range filters. "
            "This is internal tooling only and should not expose customer PII fields beyond what support already sees. "
            "A clean staging/internal implementation is enough for approval."
        ),
        "endpoints": "GET /internal/staging/tickets/export.csv",
        "layout": "frontend/src/features/support/ExportButton.jsx\nbackend/api/internal_exports.py",
        "run_instructions": "npm run dev",
    },
    {
        "id": "PB-123",
        "title": "Add feature-flag guard for staging experimental UI block",
        "language": "Python",
        "reward": 2.5,
        "slots": slots_for_reward(2.5),
        "status": "open",
        "summary": "Prevent accidental exposure of staging experiments to non-test users.",
        "description": (
            "ShipNest is testing an experimental UI block in staging. "
            "The team wants strict feature-flag checks so only whitelisted QA users can access it. "
            "Your task is to add robust guard logic and fallback rendering, with no impact to production release toggles. "
            "A focused implementation with clear flag checks is enough."
        ),
        "endpoints": "GET /staging/api/feature-flags\nGET /staging/dashboard",
        "layout": "backend/services/feature_flags.py\nfrontend/src/features/experiments/ExperimentalBlock.tsx",
        "run_instructions": "npm run dev && uvicorn backend.main:app --reload",
    },
    {
        "id": "PB-124",
        "title": "Fix internal webhook replay tool duplicate-send behavior",
        "language": "Shell",
        "reward": 1.0,
        "slots": slots_for_reward(1.0),
        "status": "open",
        "summary": "Internal replay script sends duplicates during batch retries.",
        "description": (
            "CraftPilot has an internal webhook replay helper used by support engineers in staging. "
            "Under retry mode, the script occasionally resends the same event IDs more than once. "
            "Your task is to add dedupe protection and clear terminal output so support can trust replay batches. "
            "No live production event replays should be touched in this task."
        ),
        "endpoints": "N/A (internal CLI tool)",
        "layout": "tools/replay_webhooks.sh\ntools/lib/event_batch_utils.sh",
        "run_instructions": "bash tools/replay_webhooks.sh --env staging --dry-run",
    },
    {
        "id": "PB-125",
        "title": "Create staging smoke-test checklist for login + task submit",
        "language": "SQL",
        "reward": 2.0,
        "slots": slots_for_reward(2.0),
        "status": "open",
        "summary": "Provide repeatable smoke script/checklist for core staging paths.",
        "description": (
            "LedgerLoop needs a lightweight but repeatable staging smoke test routine before each release candidate. "
            "The checklist should cover login, task browsing, submission creation, and admin review sanity checks. "
            "Your task is to produce a practical script or markdown checklist that QA can run in 10-15 minutes. "
            "This is staging/internal quality assurance only."
        ),
        "endpoints": "POST /staging/api/auth/login\nPOST /staging/api/submissions",
        "layout": "docs/qa/staging_smoke_checklist.md\nbackend/scripts/workflow_smoke.py",
        "run_instructions": "python backend/scripts/workflow_smoke.py --api-base http://127.0.0.1:8000/api",
    },
]

STARTUP_BY_TASK_ID = {
    "PB-101": "RunBetter",
    "PB-104": "InsightTree",
    "PB-105": "ClassPath",
    "PB-106": "DealRadar",
    "PB-110": "NotifyLoop",
    "PB-111": "PromptForge",
    "PB-112": "ReplyPilot",
    "PB-113": "BuildLane",
    "PB-114": "SprintMint",
    "PB-115": "CreatorNest",
    "PB-116": "TaskBloom",
    "PB-117": "IdeaMate",
    "PB-118": "CrewBoard",
    "PB-119": "PayOrbit",
    "PB-120": "SignalDock",
    "PB-121": "NovaBoard",
    "PB-122": "PulseDesk",
    "PB-123": "ShipNest",
    "PB-124": "CraftPilot",
    "PB-125": "LedgerLoop",
}

def task_to_out(task: TaskRecord) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        type=task.language,
        reward=task.reward,
        slots=task.slots,
        status=task.status,
        startup_name=task.startup_name or STARTUP_BY_TASK_ID.get(task.id, "Startup App"),
        summary=task.summary,
        description=task.description,
        context={
            "endpoints": task.endpoints,
            "layout": task.layout,
            "run": task.run_instructions,
        },
    )


def submission_to_out(row: SubmissionRecord) -> SubmissionOut:
    return SubmissionOut(
        id=row.id,
        taskId=row.task_id,
        contributorId=row.contributor_id,
        contributorName=row.contributor_name,
        thinking=row.thinking,
        code=row.code,
        status=row.status,
        dispute=row.dispute,
        reviewNote=row.review_note,
        rejectionReason=row.rejection_reason,
        aiDetectionConfidence=row.ai_detection_confidence,
        payoutRate=row.payout_rate,
        reviewedAt=row.reviewed_at,
        startupFeedbackRating=row.startup_feedback_rating,
        startupFeedbackNote=row.startup_feedback_note,
        startupFeedbackAt=row.startup_feedback_at,
        attachments=[],
        submittedAt=row.submitted_at,
    )


def submission_attachment_to_out(row: SubmissionAttachmentRecord) -> SubmissionAttachmentOut:
    return SubmissionAttachmentOut(
        id=row.id,
        fileName=row.file_name,
        contentType=row.content_type,
        sizeBytes=row.size_bytes,
        createdAt=row.created_at,
    )


def with_submission_attachments(
    session: Session, submissions: list[SubmissionRecord]
) -> list[SubmissionOut]:
    if not submissions:
        return []
    out_items = [submission_to_out(row) for row in submissions]
    by_submission_id: dict[int, list[SubmissionAttachmentOut]] = {
        row.id: [] for row in submissions
    }
    attachment_rows = session.execute(
        select(SubmissionAttachmentRecord).where(
            SubmissionAttachmentRecord.submission_id.in_(list(by_submission_id.keys()))
        )
    ).scalars().all()
    for attachment in attachment_rows:
        by_submission_id.setdefault(attachment.submission_id, []).append(
            submission_attachment_to_out(attachment)
        )
    for out in out_items:
        out.attachments = by_submission_id.get(out.id, [])
    return out_items


def sanitize_attachment_name(name: str) -> str:
    sanitized = Path(name or "").name.strip()
    if not sanitized:
        raise HTTPException(status_code=400, detail="Attachment filename is required")
    if len(sanitized) > 180:
        raise HTTPException(status_code=400, detail="Attachment filename is too long")
    ext = Path(sanitized).suffix.lower()
    if ext not in ALLOWED_SUBMISSION_ATTACHMENT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported attachment type '{ext or 'none'}'. Allowed: {', '.join(sorted(ALLOWED_SUBMISSION_ATTACHMENT_EXTENSIONS))}",
        )
    return sanitized


def storage_name_for_upload(original_name: str) -> str:
    ext = Path(original_name).suffix.lower()
    return f"{secrets.token_hex(16)}{ext}"


def receipt_to_out(receipt: PaymentReceiptRecord) -> ReceiptOut:
    return ReceiptOut(
        id=receipt.id,
        payoutRequestId=receipt.payout_request_id,
        userId=receipt.user_id,
        provider=receipt.provider,
        providerReference=receipt.provider_reference,
        amount=receipt.amount,
        issuedAt=receipt.issued_at,
    )


def payment_method_to_out(method: PaymentMethodRecord) -> PaymentMethodOut:
    return PaymentMethodOut(
        id=method.id,
        userId=method.user_id,
        methodType=method.method_type,
        provider=method.provider,
        providerToken=method.provider_token,
        cardBrand=method.card_brand,
        cardLast4=method.card_last4,
        cardholderName=method.cardholder_name,
        expMonth=method.exp_month,
        expYear=method.exp_year,
        billingEmail=method.billing_email,
        createdAt=method.created_at,
    )


def startup_to_out(startup: StartupRecord) -> StartupOut:
    return StartupOut(
        id=startup.id,
        userId=startup.user_id,
        companyName=startup.company_name,
        websiteUrl=startup.website_url,
        industry=startup.industry,
        productStage=startup.product_stage,
        techStack=startup.tech_stack,
        teamSize=startup.team_size,
        squadSummary=startup.squad_summary,
        intentions=startup.intentions,
        tasksPosted=startup.tasks_posted,
        numberOfTasks=startup.number_of_tasks,
        status=startup.status,
        reviewNote=startup.review_note,
        createdAt=startup.created_at,
        updatedAt=startup.updated_at,
    )


def startup_request_to_out(row: StartupTaskRequestRecord) -> StartupTaskRequestOut:
    return StartupTaskRequestOut(
        id=row.id,
        startupId=row.startup_id,
        startupUserId=row.startup_user_id,
        title=row.title,
        language=row.language,
        reward=row.reward,
        details=row.details,
        acceptanceRules=row.acceptance_rules,
        status=row.status,
        adminNote=row.admin_note,
        publishedToTasks=row.published_to_tasks,
        createdAt=row.created_at,
        updatedAt=row.updated_at,
    )


def startup_deletion_request_to_out(row: StartupTaskDeletionRequestRecord) -> StartupTaskDeletionRequestOut:
    return StartupTaskDeletionRequestOut(
        id=row.id,
        taskId=row.task_id,
        startupId=row.startup_id,
        startupUserId=row.startup_user_id,
        startupName=row.startup_name,
        adminUserId=row.admin_user_id,
        note=row.note,
        status=row.status,
        createdAt=row.created_at,
        updatedAt=row.updated_at,
    )


def admin_user_to_out(user: UserAuthRecord) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        fullName=user.full_name,
        role=user.role,
        profileCompleted=user.profile_completed,
        isActive=bool(user.is_active),
        createdAt=user.created_at,
    )


def build_admin_user_overview(session: Session, user: UserAuthRecord) -> AdminUserOverviewOut:
    submissions = session.execute(
        select(SubmissionRecord).where(SubmissionRecord.contributor_id == user.id)
    ).scalars().all()
    payout_requests = session.execute(
        select(PayoutRequestRecord).where(PayoutRequestRecord.user_id == user.id)
    ).scalars().all()
    auth_sessions = session.execute(
        select(SessionTokenRecord).where(SessionTokenRecord.user_id == user.id)
    ).scalars().all()
    startup = session.execute(
        select(StartupRecord).where(StartupRecord.user_id == user.id)
    ).scalar_one_or_none()

    submissions_count = len(submissions)
    pending_submissions = len([row for row in submissions if row.status == "under_review"])
    approved_submissions = len([row for row in submissions if row.status == "approved"])
    partial_approved_submissions = len([row for row in submissions if row.status == "partial_approved"])
    rejected_submissions = len([row for row in submissions if row.status == "rejected"])
    payouts_count = len(payout_requests)
    paid_payout_requests = len([row for row in payout_requests if row.status == "paid"])
    pending_payout_requests = len([row for row in payout_requests if row.status == "pending"])
    last_login_at = max((row.created_at for row in auth_sessions), default=None)

    return AdminUserOverviewOut(
        userId=user.id,
        email=user.email,
        fullName=user.full_name,
        role=user.role,
        isActive=bool(user.is_active),
        profileCompleted=user.profile_completed,
        lastLoginAt=last_login_at,
        submissionsCount=submissions_count,
        pendingSubmissions=pending_submissions,
        approvedSubmissions=approved_submissions,
        partialApprovedSubmissions=partial_approved_submissions,
        rejectedSubmissions=rejected_submissions,
        payoutRequestsCount=payouts_count,
        paidPayoutRequests=paid_payout_requests,
        pendingPayoutRequests=pending_payout_requests,
        startupCompanyName=startup.company_name if startup else None,
        startupStatus=startup.status if startup else None,
        startupTasksPosted=int(startup.tasks_posted or 0) if startup else 0,
    )


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError("Password is too long for the current hashing policy")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return f"bcrypt${hashed}"


def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        return False, False
    # Legacy format: "salt$sha256(salt:password)"
    if stored_hash.count("$") == 1 and not stored_hash.startswith("$2"):
        try:
            salt, digest = stored_hash.split("$", 1)
            candidate = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
            ok = hmac.compare_digest(candidate, digest)
            return ok, ok
        except ValueError:
            return False, False

    # New format: "bcrypt$<bcrypt_hash>", and support existing raw "$2x$..." hashes.
    if stored_hash.startswith("bcrypt$"):
        bcrypt_hash = stored_hash.split("$", 1)[1]
    else:
        bcrypt_hash = stored_hash
    if not bcrypt_hash.startswith("$2"):
        return False, False
    try:
        ok = bcrypt.checkpw(password.encode("utf-8"), bcrypt_hash.encode("utf-8"))
    except Exception:
        return False, False
    return ok, False


def luhn_valid(card_number: str) -> bool:
    digits = [int(ch) for ch in card_number if ch.isdigit()]
    if len(digits) < 12:
        return False
    checksum = 0
    parity = len(digits) % 2
    for idx, digit in enumerate(digits):
        value = digit
        if idx % 2 == parity:
            value = digit * 2
            if value > 9:
                value -= 9
        checksum += value
    return checksum % 10 == 0


def stripe_secret_key() -> str:
    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def stripe_publishable_key() -> str:
    return os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()


def ensure_stripe_customer(session: Session, user: UserAuthRecord) -> str:
    secret_key = stripe_secret_key()
    if not secret_key:
        raise HTTPException(status_code=503, detail="Stripe secret key is not configured")
    if stripe is None:
        raise HTTPException(status_code=503, detail="Stripe SDK is not installed")
    stripe.api_key = secret_key
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name,
        metadata={"platform_user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    session.commit()
    session.refresh(user)
    return user.stripe_customer_id


def apply_rate_limit(scope: str, request: Request) -> None:
    max_calls, window_seconds = RATE_LIMIT_RULES[scope]
    ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.client.host
        or "unknown"
    )
    now = time.time()
    bucket_key = f"{scope}:{ip}"
    entries = [ts for ts in RATE_LIMIT_BUCKET.get(bucket_key, []) if now - ts <= window_seconds]
    if len(entries) >= max_calls:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")
    entries.append(now)
    RATE_LIMIT_BUCKET[bucket_key] = entries


def issue_session_token(db: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    db.add(SessionTokenRecord(user_id=user_id, token=token, expires_at=expires_at))
    db.commit()
    return token


def log_admin_action(admin_user_id: int, action: str, target_type: str, target_ref: str, note: Optional[str] = None) -> None:
    with Session(engine) as session:
        session.add(
            AdminAuditLogRecord(
                admin_user_id=admin_user_id,
                action=action,
                target_type=target_type,
                target_ref=target_ref,
                note=note,
            )
        )
        session.commit()


def set_auth_cookie(response: Response, token: str) -> None:
    csrf_token = secrets.token_urlsafe(24)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )
    response.set_cookie(
        key=AUTH_CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        max_age=SESSION_TTL_HOURS * 3600,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        path="/",
    )
    response.delete_cookie(
        key=AUTH_CSRF_COOKIE_NAME,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        path="/",
    )


def forward_event_to_posthog(event_name: str, distinct_id: str, properties: dict) -> None:
    if not POSTHOG_API_KEY:
        return
    payload = json.dumps(
        {
            "api_key": POSTHOG_API_KEY,
            "event": event_name,
            "distinct_id": distinct_id,
            "properties": properties,
        }
    ).encode("utf-8")
    req = UrlRequest(
        f"{POSTHOG_HOST}/capture/",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=4):
            pass
    except Exception:
        # Never fail app behavior due to analytics network issues.
        return


def resolve_user_from_token(authorization: Optional[str], x_auth_token: Optional[str]) -> UserAuthRecord:
    tokens: list[str] = []
    if authorization and authorization.lower().startswith("bearer "):
        tokens.append(authorization[7:].strip())
    if x_auth_token:
        tokens.append(x_auth_token.strip())
    tokens = [token for token in tokens if token]

    if not tokens:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    with Session(engine) as session:
        for token in tokens:
            auth_session = session.execute(select(SessionTokenRecord).where(SessionTokenRecord.token == token)).scalar_one_or_none()
            if auth_session is None:
                continue
            if auth_session.expires_at < datetime.utcnow():
                continue
            user = session.get(UserAuthRecord, auth_session.user_id)
            if user is None:
                continue
            if not bool(user.is_active):
                raise HTTPException(status_code=403, detail="Account is disabled")
            return user
    raise HTTPException(status_code=401, detail="Invalid authentication token")


def normalize_remote_task(raw: dict) -> dict:
    reward = float(raw.get("reward", 1.0))
    task_id = str(raw["id"]).strip()
    title = str(raw.get("title", "Imported task")).strip()
    language = str(raw.get("language", "General")).strip()
    summary = str(raw.get("summary", "Imported from remote API feed.")).strip()
    description = str(raw.get("description", summary)).strip()
    endpoints = str(raw.get("endpoints", "N/A")).strip()
    layout = str(raw.get("layout", "N/A")).strip()
    run_instructions = str(raw.get("run_instructions", "N/A")).strip()
    startup_name = str(raw.get("startup_name", "")).strip()
    status = str(raw.get("status", "open")).strip() or "open"
    slots = str(raw.get("slots", slots_for_reward(reward))).strip() or slots_for_reward(reward)
    return {
        "id": task_id,
        "title": title,
        "language": language,
        "reward": reward,
        "slots": slots,
        "status": status,
        "summary": summary,
        "description": description,
        "endpoints": endpoints,
        "layout": layout,
        "run_instructions": run_instructions,
        "startup_name": startup_name or None,
    }


def task_id_for_startup_request(request_id: int) -> str:
    return f"SR-{request_id:04d}"


def on_startup() -> None:
    validate_runtime_config()
    UPLOADS_BASE_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    # Legacy SQLite patch-up logic. Postgres/other DBs should rely on SQLAlchemy models + Alembic migrations.
    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            task_cols = {
                row[1] for row in conn.exec_driver_sql("PRAGMA table_info(tasks)").fetchall()
            }
            if "startup_name" not in task_cols:
                conn.exec_driver_sql("ALTER TABLE tasks ADD COLUMN startup_name VARCHAR(255)")
                conn.commit()

        with engine.connect() as conn:
            auth_cols = {
                row[1] for row in conn.exec_driver_sql("PRAGMA table_info(auth_users)").fetchall()
            }
            if "profile_completed" not in auth_cols:
                conn.exec_driver_sql("ALTER TABLE auth_users ADD COLUMN profile_completed BOOLEAN DEFAULT 0")
            if "is_active" not in auth_cols:
                conn.exec_driver_sql("ALTER TABLE auth_users ADD COLUMN is_active BOOLEAN DEFAULT 1")
            if "stripe_customer_id" not in auth_cols:
                conn.exec_driver_sql("ALTER TABLE auth_users ADD COLUMN stripe_customer_id VARCHAR(80)")
                conn.commit()

        with engine.connect() as conn:
            session_cols = {
                row[1] for row in conn.exec_driver_sql("PRAGMA table_info(auth_sessions)").fetchall()
            }
            if "expires_at" not in session_cols:
                conn.exec_driver_sql("ALTER TABLE auth_sessions ADD COLUMN expires_at DATETIME")
                conn.exec_driver_sql(
                    f"UPDATE auth_sessions SET expires_at = datetime(created_at, '+{SESSION_TTL_HOURS} hours') WHERE expires_at IS NULL"
                )
                conn.commit()

        with engine.connect() as conn:
            submission_cols = {
                row[1] for row in conn.exec_driver_sql("PRAGMA table_info(submissions)").fetchall()
            }
            if "review_note" not in submission_cols:
                conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN review_note TEXT")
            if "rejection_reason" not in submission_cols:
                conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN rejection_reason TEXT")
            if "ai_detection_confidence" not in submission_cols:
                conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN ai_detection_confidence INTEGER")
            if "payout_rate" not in submission_cols:
                conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN payout_rate FLOAT")
            if "reviewed_at" not in submission_cols:
                conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN reviewed_at DATETIME")
            if "startup_feedback_rating" not in submission_cols:
                conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN startup_feedback_rating INTEGER")
            if "startup_feedback_note" not in submission_cols:
                conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN startup_feedback_note TEXT")
            if "startup_feedback_at" not in submission_cols:
                conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN startup_feedback_at DATETIME")
            if "startup_feedback_user_id" not in submission_cols:
                conn.exec_driver_sql("ALTER TABLE submissions ADD COLUMN startup_feedback_user_id INTEGER")
            conn.commit()

        with engine.connect() as conn:
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS submission_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id INTEGER NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    storage_name VARCHAR(255) NOT NULL UNIQUE,
                    content_type VARCHAR(120) NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

        with engine.connect() as conn:
            startup_cols = {
                row[1] for row in conn.exec_driver_sql("PRAGMA table_info(startups)").fetchall()
            }
            if "product_stage" not in startup_cols:
                conn.exec_driver_sql("ALTER TABLE startups ADD COLUMN product_stage VARCHAR(80) DEFAULT 'idea'")
            if "tech_stack" not in startup_cols:
                conn.exec_driver_sql("ALTER TABLE startups ADD COLUMN tech_stack TEXT DEFAULT ''")
            if "tasks_posted" not in startup_cols:
                conn.exec_driver_sql("ALTER TABLE startups ADD COLUMN tasks_posted INTEGER DEFAULT 0")
            if "number_of_tasks" not in startup_cols:
                conn.exec_driver_sql("ALTER TABLE startups ADD COLUMN number_of_tasks INTEGER DEFAULT 0")
            conn.commit()

    with Session(engine) as session:
        existing_rows = {row.id: row for row in session.execute(select(TaskRecord)).scalars().all()}
        for row in SEED_TASKS:
            if row["id"] not in existing_rows:
                session.add(TaskRecord(**row))
                continue

            # Keep seeded context/description fresh across restarts while preserving admin reward edits.
            record = existing_rows[row["id"]]
            record.title = row["title"]
            record.language = row["language"]
            # Keep slots consistent with current reward band every startup.
            record.slots = slots_for_reward(record.reward)
            record.status = row["status"]
            record.summary = row["summary"]
            record.description = row["description"]
            record.endpoints = row["endpoints"]
            record.layout = row["layout"]
            record.run_instructions = row["run_instructions"]
            record.startup_name = STARTUP_BY_TASK_ID.get(row["id"])
        if ALLOW_ADMIN_BOOTSTRAP and ADMIN_BOOTSTRAP_EMAIL and ADMIN_BOOTSTRAP_PASSWORD:
            admin = session.execute(
                select(UserAuthRecord).where(UserAuthRecord.email == ADMIN_BOOTSTRAP_EMAIL)
            ).scalar_one_or_none()
            if admin is None:
                if len(ADMIN_BOOTSTRAP_PASSWORD.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
                    raise RuntimeError("ADMIN_BOOTSTRAP_PASSWORD exceeds 72-byte bcrypt limit")
                admin = UserAuthRecord(
                    email=ADMIN_BOOTSTRAP_EMAIL,
                    full_name=ADMIN_BOOTSTRAP_NAME,
                    password_hash=hash_password(ADMIN_BOOTSTRAP_PASSWORD),
                    role="admin",
                    profile_completed=True,
                    is_active=True,
                )
                session.add(admin)
        session.commit()


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    on_startup()
    yield


app.router.lifespan_context = app_lifespan


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/metrics/overview", response_model=OverviewMetricsOut)
def get_overview_metrics() -> OverviewMetricsOut:
    now = datetime.utcnow()
    today = now.date()
    approved_statuses = {"done", "approved", "partial_approved"}

    with Session(engine) as session:
        contributors = session.execute(
            select(UserAuthRecord).where(UserAuthRecord.role == "contributor")
        ).scalars().all()
        contributor_ids = {user.id for user in contributors}

        paid_today = [
            row
            for row in session.execute(select(PayoutRequestRecord).where(PayoutRequestRecord.status == "paid")).scalars().all()
            if row.created_at.date() == today
        ]
        earnings_by_user: dict[int, float] = {user_id: 0.0 for user_id in contributor_ids}
        for row in paid_today:
            if row.user_id in earnings_by_user:
                earnings_by_user[row.user_id] += row.amount

        # Platform-wide average earnings per contributor for today (includes zero-earning contributors).
        today_average_earnings = (
            round(sum(earnings_by_user.values()) / len(earnings_by_user), 2) if earnings_by_user else 0.0
        )

        # Platform-wide average response/wait time based on all submissions in the last 24h.
        recent_submissions = [
            row
            for row in session.execute(select(SubmissionRecord)).scalars().all()
            if (now - row.submitted_at).total_seconds() <= 24 * 3600
        ]
        average_review_hours = (
            round(sum((now - row.submitted_at).total_seconds() / 3600 for row in recent_submissions) / len(recent_submissions), 1)
            if recent_submissions
            else 0.0
        )

        tasks_approved_today = len(
            [
                row
                for row in session.execute(select(SubmissionRecord)).scalars().all()
                if row.status in approved_statuses and row.submitted_at.date() == today
            ]
        )

    return OverviewMetricsOut(
        todayAverageEarnings=today_average_earnings,
        averageReviewHours=average_review_hours,
        tasksApprovedToday=tasks_approved_today,
    )


@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(language: Optional[str] = Query(default=None)) -> list[TaskOut]:
    with Session(engine) as session:
        stmt = select(TaskRecord)
        if language and language.lower() != "all":
            stmt = stmt.where(TaskRecord.language.ilike(language))
        rows = session.execute(stmt).scalars().all()
        return [task_to_out(row) for row in rows]


@app.get("/api/admin/users", response_model=list[AdminUserOut])
def list_admin_users(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> list[AdminUserOut]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can list platform users")
    with Session(engine) as session:
        rows = session.execute(select(UserAuthRecord)).scalars().all()
        return [admin_user_to_out(row) for row in rows]


@app.patch("/api/admin/users/{user_id}", response_model=AdminUserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdateIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> AdminUserOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update users")
    with Session(engine) as session:
        row = session.get(UserAuthRecord, user_id)
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")
        active_admin_count = session.execute(
            select(UserAuthRecord).where(UserAuthRecord.role == "admin", UserAuthRecord.is_active == True)  # noqa: E712
        ).scalars().all()
        is_last_active_admin = row.role == "admin" and bool(row.is_active) and len(active_admin_count) <= 1
        if payload.role is not None:
            if is_last_active_admin and payload.role != "admin":
                raise HTTPException(status_code=400, detail="Cannot demote the last active admin")
            row.role = payload.role
        if payload.profileCompleted is not None:
            row.profile_completed = payload.profileCompleted
        if payload.isActive is not None:
            if is_last_active_admin and payload.isActive is False:
                raise HTTPException(status_code=400, detail="Cannot disable the last active admin")
            row.is_active = payload.isActive
        session.commit()
        session.refresh(row)
        log_admin_action(auth_user.id, "update_user_access", "user", str(user_id), note=f"role={row.role}, active={row.is_active}")
        return admin_user_to_out(row)


@app.get("/api/admin/users/{user_id}/overview", response_model=AdminUserOverviewOut)
def admin_user_overview(
    user_id: int,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> AdminUserOverviewOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view user overview")
    with Session(engine) as session:
        user = session.get(UserAuthRecord, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return build_admin_user_overview(session, user)


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> dict[str, str]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can remove users")
    if auth_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot remove your own admin account")

    with Session(engine) as session:
        row = session.get(UserAuthRecord, user_id)
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")
        active_admin_count = session.execute(
            select(UserAuthRecord).where(UserAuthRecord.role == "admin", UserAuthRecord.is_active == True)  # noqa: E712
        ).scalars().all()
        if row.role == "admin" and bool(row.is_active) and len(active_admin_count) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last active admin")
        deleted_email = row.email
        for session_row in session.execute(select(SessionTokenRecord).where(SessionTokenRecord.user_id == user_id)).scalars().all():
            session.delete(session_row)
        session.delete(row)
        session.commit()
        log_admin_action(auth_user.id, "delete_user", "user", str(user_id), note=deleted_email)
        return {"message": "User removed"}


@app.post("/api/admin/tasks", response_model=TaskOut)
def admin_create_task(
    payload: AdminTaskCreateIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> TaskOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create tasks")

    provided_id = (payload.id or "").strip()
    task_id = provided_id or f"TASK-{secrets.token_hex(3).upper()}"
    with Session(engine) as session:
        existing = session.get(TaskRecord, task_id)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Task ID already exists")
        row = TaskRecord(
            id=task_id,
            title=payload.title.strip(),
            language=payload.language.strip(),
            reward=payload.reward,
            slots=slots_for_reward(payload.reward),
            status=payload.status.strip(),
            startup_name=(payload.startupName or "").strip() or None,
            summary=payload.summary.strip(),
            description=payload.description.strip(),
            endpoints=payload.endpoints.strip(),
            layout=payload.layout.strip(),
            run_instructions=payload.runInstructions.strip(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        log_admin_action(auth_user.id, "create_task", "task", row.id, note=row.title)
        return task_to_out(row)


@app.patch("/api/admin/tasks/{task_id}", response_model=TaskOut)
def admin_update_task(
    task_id: str,
    payload: AdminTaskUpdateIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> TaskOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update tasks")
    with Session(engine) as session:
        row = session.get(TaskRecord, task_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if payload.title is not None:
            row.title = payload.title.strip()
        if payload.language is not None:
            row.language = payload.language.strip()
        if payload.reward is not None:
            row.reward = payload.reward
            row.slots = slots_for_reward(payload.reward)
        if payload.status is not None:
            row.status = payload.status.strip()
        if payload.startupName is not None:
            row.startup_name = payload.startupName.strip() or None
        if payload.summary is not None:
            row.summary = payload.summary.strip()
        if payload.description is not None:
            row.description = payload.description.strip()
        if payload.endpoints is not None:
            row.endpoints = payload.endpoints.strip()
        if payload.layout is not None:
            row.layout = payload.layout.strip()
        if payload.runInstructions is not None:
            row.run_instructions = payload.runInstructions.strip()
        session.commit()
        session.refresh(row)
        log_admin_action(auth_user.id, "update_task", "task", row.id, note=row.title)
        return task_to_out(row)


@app.delete("/api/admin/tasks/{task_id}")
def admin_delete_task(
    task_id: str,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> dict[str, str]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete tasks")
    with Session(engine) as session:
        row = session.get(TaskRecord, task_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        startup = None
        if row.startup_name:
            startup = session.execute(
                select(StartupRecord).where(StartupRecord.company_name == row.startup_name)
            ).scalar_one_or_none()

        if startup is not None:
            existing_pending = session.execute(
                select(StartupTaskDeletionRequestRecord).where(
                    StartupTaskDeletionRequestRecord.task_id == row.id,
                    StartupTaskDeletionRequestRecord.status == "pending",
                )
            ).scalar_one_or_none()
            if existing_pending is not None:
                raise HTTPException(status_code=409, detail="Deletion request already pending startup approval")
            request_row = StartupTaskDeletionRequestRecord(
                task_id=row.id,
                startup_id=startup.id,
                startup_user_id=startup.user_id,
                startup_name=startup.company_name,
                admin_user_id=auth_user.id,
                note=f"Admin requested deletion for task '{row.title}'",
                status="pending",
            )
            session.add(request_row)
            session.commit()
            log_admin_action(auth_user.id, "request_task_deletion", "task", task_id, note=row.title)
            return {"message": "Deletion request sent to startup for approval"}

        deleted_title = row.title
        session.delete(row)
        session.commit()
        log_admin_action(auth_user.id, "delete_task", "task", task_id, note=deleted_title)
        return {"message": "Task deleted"}


@app.get("/api/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: str) -> TaskOut:
    with Session(engine) as session:
        row = session.get(TaskRecord, task_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task_to_out(row)


@app.post("/api/tasks/import-url", response_model=TaskImportOut)
def import_tasks_from_url(
    payload: TaskImportIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> TaskImportOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can import remote tasks")
    try:
        with urlopen(payload.sourceUrl, timeout=12) as response:
            body = response.read().decode("utf-8")
    except URLError as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch source URL: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unexpected import error: {exc}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON from source URL: {exc}") from exc

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Remote payload must be a JSON array of task objects")

    imported = 0
    updated = 0
    with Session(engine) as session:
        existing_rows = {row.id: row for row in session.execute(select(TaskRecord)).scalars().all()}
        for item in data:
            if not isinstance(item, dict) or "id" not in item:
                continue
            normalized = normalize_remote_task(item)
            existing = existing_rows.get(normalized["id"])
            if existing is None:
                session.add(TaskRecord(**normalized))
                imported += 1
            else:
                existing.title = normalized["title"]
                existing.language = normalized["language"]
                existing.summary = normalized["summary"]
                existing.description = normalized["description"]
                existing.endpoints = normalized["endpoints"]
                existing.layout = normalized["layout"]
                existing.run_instructions = normalized["run_instructions"]
                existing.status = normalized["status"]
                # Keep slots aligned with platform rule if reward changes.
                existing.reward = normalized["reward"]
                existing.slots = slots_for_reward(existing.reward)
                existing.startup_name = normalized["startup_name"]
                updated += 1
        session.commit()

    log_admin_action(auth_user.id, "import_tasks", "task_feed", payload.sourceUrl, note=f"imported={imported},updated={updated}")
    return TaskImportOut(imported=imported, updated=updated, sourceUrl=payload.sourceUrl)


@app.post("/api/submissions")
def create_submission(
    payload: SubmissionIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> dict[str, str]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "contributor":
        raise HTTPException(status_code=403, detail="Only contributors can submit task proposals")
    if not auth_user.profile_completed:
        raise HTTPException(status_code=403, detail="Complete your contributor profile before submitting tasks")
    if auth_user.id != payload.contributorId:
        raise HTTPException(status_code=403, detail="Contributor identity mismatch")

    with Session(engine) as session:
        task = session.get(TaskRecord, payload.taskId)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

        record = SubmissionRecord(
            task_id=payload.taskId,
            contributor_id=payload.contributorId,
            contributor_name=payload.contributorName,
            thinking=payload.thinking,
            code=payload.code,
            status="under_review",
        )
        session.add(record)
        task.status = "under_review"
        session.commit()
        session.refresh(record)

    return {"message": "Submission received", "submissionId": str(record.id)}


@app.get("/api/submissions", response_model=list[SubmissionOut])
def list_submissions(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> list[SubmissionOut]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    with Session(engine) as session:
        stmt = select(SubmissionRecord)
        if auth_user.role == "admin":
            rows = session.execute(stmt).scalars().all()
        elif auth_user.role == "contributor":
            rows = session.execute(stmt.where(SubmissionRecord.contributor_id == auth_user.id)).scalars().all()
        elif auth_user.role == "startup":
            startup = session.execute(select(StartupRecord).where(StartupRecord.user_id == auth_user.id)).scalar_one_or_none()
            if startup is None:
                return []
            task_ids = [
                task.id
                for task in session.execute(select(TaskRecord).where(TaskRecord.startup_name == startup.company_name)).scalars().all()
            ]
            if not task_ids:
                return []
            rows = session.execute(stmt.where(SubmissionRecord.task_id.in_(task_ids))).scalars().all()
        else:
            raise HTTPException(status_code=403, detail="Not allowed to list submissions")
        return with_submission_attachments(session, rows)


@app.patch("/api/submissions/{submission_id}/review", response_model=SubmissionOut)
def review_submission(
    submission_id: int,
    payload: SubmissionReviewIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> SubmissionOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can review submissions")
    with Session(engine) as session:
        row = session.get(SubmissionRecord, submission_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        if row.status in FINAL_SUBMISSION_STATUSES and row.status != payload.status:
            raise HTTPException(
                status_code=409,
                detail="Submission review is already finalized. Reopen flow is required before changing status.",
            )
        if row.status == "under_review" and payload.status not in FINAL_SUBMISSION_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid transition from under_review")
        row.status = payload.status
        row.review_note = (payload.reviewNote or "").strip() or None
        row.rejection_reason = (payload.rejectionReason or "").strip() or None
        row.ai_detection_confidence = payload.aiDetectionConfidence
        if payload.status == "approved":
            row.payout_rate = 1.0
        elif payload.status == "partial_approved":
            row.payout_rate = 0.5
        else:
            row.payout_rate = 0.0
        row.reviewed_at = datetime.utcnow()
        session.commit()
        session.refresh(row)
        out = submission_to_out(row)
        out.attachments = [
            submission_attachment_to_out(item)
            for item in session.execute(
                select(SubmissionAttachmentRecord).where(
                    SubmissionAttachmentRecord.submission_id == row.id
                )
            ).scalars().all()
        ]
        return out


@app.post("/api/startup/submissions/{submission_id}/feedback", response_model=SubmissionOut)
def startup_feedback_submission(
    submission_id: int,
    payload: StartupSubmissionFeedbackIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> SubmissionOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "startup":
        raise HTTPException(status_code=403, detail="Only startup accounts can submit feedback")
    with Session(engine) as session:
        startup = session.execute(select(StartupRecord).where(StartupRecord.user_id == auth_user.id)).scalar_one_or_none()
        if startup is None:
            raise HTTPException(status_code=403, detail="Startup profile not found")
        row = session.get(SubmissionRecord, submission_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        task = session.get(TaskRecord, row.task_id)
        if task is None or (task.startup_name or "") != startup.company_name:
            raise HTTPException(status_code=403, detail="Submission does not belong to your startup task")
        if row.status not in {"approved", "partial_approved", "rejected"}:
            raise HTTPException(status_code=400, detail="You can rate submissions only after admin review")
        row.startup_feedback_rating = payload.rating
        row.startup_feedback_note = (payload.note or "").strip() or None
        row.startup_feedback_at = datetime.utcnow()
        row.startup_feedback_user_id = auth_user.id
        session.commit()
        session.refresh(row)
        out = submission_to_out(row)
        out.attachments = [
            submission_attachment_to_out(item)
            for item in session.execute(
                select(SubmissionAttachmentRecord).where(
                    SubmissionAttachmentRecord.submission_id == row.id
                )
            ).scalars().all()
        ]
        return out


@app.post(
    "/api/submissions/{submission_id}/attachments",
    response_model=list[SubmissionAttachmentOut],
)
async def upload_submission_attachments(
    submission_id: int,
    files: list[UploadFile] = File(default=[]),
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> list[SubmissionAttachmentOut]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "contributor":
        raise HTTPException(status_code=403, detail="Only contributors can upload submission attachments")
    if not files:
        raise HTTPException(status_code=400, detail="No files were provided")
    with Session(engine) as session:
        submission = session.get(SubmissionRecord, submission_id)
        if submission is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        if submission.contributor_id != auth_user.id:
            raise HTTPException(status_code=403, detail="You can only upload files for your own submission")
        existing_count = session.execute(
            select(SubmissionAttachmentRecord).where(
                SubmissionAttachmentRecord.submission_id == submission_id
            )
        ).scalars().all()
        if len(existing_count) + len(files) > MAX_SUBMISSION_ATTACHMENTS_PER_SUBMISSION:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_SUBMISSION_ATTACHMENTS_PER_SUBMISSION} attachments are allowed per submission",
            )
        created: list[SubmissionAttachmentRecord] = []
        for upload in files:
            safe_name = sanitize_attachment_name(upload.filename or "")
            body = await upload.read(MAX_SUBMISSION_ATTACHMENT_BYTES + 1)
            if len(body) > MAX_SUBMISSION_ATTACHMENT_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"{safe_name} exceeds {MAX_SUBMISSION_ATTACHMENT_BYTES // (1024 * 1024)}MB limit",
                )
            storage_name = storage_name_for_upload(safe_name)
            content_type = (
                (upload.content_type or "").strip().lower()
                or mimetypes.guess_type(safe_name)[0]
                or "application/octet-stream"
            )
            target = (UPLOADS_BASE_DIR / storage_name).resolve()
            if target.parent != UPLOADS_BASE_DIR:
                raise HTTPException(status_code=400, detail="Invalid upload target path")
            target.write_bytes(body)
            row = SubmissionAttachmentRecord(
                submission_id=submission_id,
                file_name=safe_name,
                storage_name=storage_name,
                content_type=content_type,
                size_bytes=len(body),
            )
            session.add(row)
            created.append(row)
        session.commit()
        for row in created:
            session.refresh(row)
        return [submission_attachment_to_out(row) for row in created]


@app.get("/api/submissions/attachments/{attachment_id}/download")
def download_submission_attachment(
    attachment_id: int,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> FileResponse:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    with Session(engine) as session:
        attachment = session.get(SubmissionAttachmentRecord, attachment_id)
        if attachment is None:
            raise HTTPException(status_code=404, detail="Attachment not found")
        submission = session.get(SubmissionRecord, attachment.submission_id)
        if submission is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        allowed = auth_user.role == "admin" or submission.contributor_id == auth_user.id
        if auth_user.role == "startup":
            startup = session.execute(
                select(StartupRecord).where(StartupRecord.user_id == auth_user.id)
            ).scalar_one_or_none()
            if startup is not None:
                task = session.get(TaskRecord, submission.task_id)
                if task is not None and (task.startup_name or "") == startup.company_name:
                    allowed = True
        if not allowed:
            raise HTTPException(status_code=403, detail="Not allowed to download this attachment")
        path = (UPLOADS_BASE_DIR / attachment.storage_name).resolve()
        if path.parent != UPLOADS_BASE_DIR or not path.exists():
            raise HTTPException(status_code=404, detail="Attachment file is missing from storage")
        return FileResponse(path=path, filename=attachment.file_name, media_type=attachment.content_type)


@app.post("/api/auth/signup", response_model=AuthOut)
def signup(payload: SignupIn, request: Request, response: Response) -> AuthOut:
    apply_rate_limit("auth_signup", request)
    if len(payload.password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise HTTPException(status_code=400, detail="Password is too long (max 72 bytes)")
    if payload.role == "admin":
        admin_signup_enabled = os.getenv("ALLOW_ADMIN_SIGNUP", "0") == "1"
        expected_code = os.getenv("ADMIN_SIGNUP_CODE", "").strip()
        if (not admin_signup_enabled) or (not expected_code) or (payload.adminCode or "").strip() != expected_code:
            raise HTTPException(status_code=403, detail="Admin signup is disabled")
    normalized_email = payload.email.strip().lower()
    with Session(engine) as session:
        existing = session.execute(select(UserAuthRecord).where(UserAuthRecord.email == normalized_email)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Email already registered")

        user = UserAuthRecord(
            email=normalized_email,
            full_name=payload.fullName.strip(),
            password_hash=hash_password(payload.password),
            role=payload.role,
            profile_completed=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        token = issue_session_token(session, user.id)
        set_auth_cookie(response, token)

        return AuthOut(
            token=token,
            userId=user.id,
            fullName=user.full_name,
            email=user.email,
            role=user.role,
            profileCompleted=user.profile_completed,
        )


@app.post("/api/auth/login", response_model=AuthOut)
def login(payload: LoginIn, request: Request, response: Response) -> AuthOut:
    apply_rate_limit("auth_login", request)
    normalized_email = payload.email.strip().lower()
    with Session(engine) as session:
        user = session.execute(select(UserAuthRecord).where(UserAuthRecord.email == normalized_email)).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        verified, needs_rehash = verify_password(payload.password, user.password_hash)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not bool(user.is_active):
            raise HTTPException(status_code=403, detail="Account is disabled")
        if needs_rehash:
            user.password_hash = hash_password(payload.password)
            session.commit()

        token = issue_session_token(session, user.id)
        set_auth_cookie(response, token)

        return AuthOut(
            token=token,
            userId=user.id,
            fullName=user.full_name,
            email=user.email,
            role=user.role,
            profileCompleted=user.profile_completed,
        )


@app.get("/api/auth/me", response_model=AuthOut)
def auth_me(
    token: str = Query(default=""),
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    appcontributor_session: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> AuthOut:
    header_token = x_auth_token
    if not header_token and appcontributor_session:
        header_token = appcontributor_session
    if token:
        header_token = token
    user = resolve_user_from_token(authorization, header_token)
    return AuthOut(
        token="",
        userId=user.id,
        fullName=user.full_name,
        email=user.email,
        role=user.role,
        profileCompleted=user.profile_completed,
    )


@app.post("/api/auth/logout")
def auth_logout(
    response: Response,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    appcontributor_session: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> dict[str, str]:
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif x_auth_token:
        token = x_auth_token.strip()
    elif appcontributor_session:
        token = appcontributor_session.strip()
    if token:
        with Session(engine) as session:
            row = session.execute(select(SessionTokenRecord).where(SessionTokenRecord.token == token)).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()
    clear_auth_cookie(response)
    return {"message": "Logged out"}


@app.post("/api/analytics/event")
def ingest_analytics_event(payload: AnalyticsEventIn) -> dict[str, str]:
    event_name = payload.event.strip().lower()
    if not event_name:
        raise HTTPException(status_code=400, detail="Event name is required")
    metadata = sanitize_analytics_metadata(payload.metadata or {})
    with Session(engine) as session:
        row = AnalyticsEventRecord(
            event_name=event_name,
            source=payload.source.strip().lower() or "web",
            user_id=payload.userId,
            role=(payload.role or "").strip().lower() or None,
            metadata_json=json.dumps(metadata),
        )
        session.add(row)
        session.commit()
    distinct_id = str(payload.userId) if payload.userId is not None else f"anon-{secrets.token_hex(6)}"
    forward_event_to_posthog(
        event_name,
        distinct_id,
        {
            "source": payload.source,
            "role": payload.role,
            **metadata,
        },
    )
    return {"message": "Event recorded"}


@app.get("/api/admin/analytics/overview", response_model=AdminAnalyticsOverviewOut)
def admin_analytics_overview(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> AdminAnalyticsOverviewOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view analytics overview")
    cutoff = datetime.utcnow() - timedelta(hours=24)
    with Session(engine) as session:
        events = [
            row
            for row in session.execute(select(AnalyticsEventRecord)).scalars().all()
            if row.created_at >= cutoff
        ]
        submissions = [
            row
            for row in session.execute(select(SubmissionRecord)).scalars().all()
            if row.submitted_at >= cutoff
        ]
        payout_requests = [
            row
            for row in session.execute(select(PayoutRequestRecord)).scalars().all()
            if row.created_at >= cutoff
        ]
        startup_task_requests = [
            row
            for row in session.execute(select(StartupTaskRequestRecord)).scalars().all()
            if row.created_at >= cutoff
        ]
        signups = sum(1 for event in events if event.event_name == "signup_completed")
        logins = sum(1 for event in events if event.event_name == "login_success")
        return AdminAnalyticsOverviewOut(
            eventsLast24h=len(events),
            signupsLast24h=signups,
            loginsLast24h=logins,
            submissionsLast24h=len(submissions),
            payoutRequestsLast24h=len(payout_requests),
            startupTaskRequestsLast24h=len(startup_task_requests),
        )


@app.patch("/api/auth/profile-complete", response_model=AuthOut)
def set_profile_completion(
    payload: ProfileCompletionIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> AuthOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    with Session(engine) as session:
        user = session.get(UserAuthRecord, auth_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        user.profile_completed = payload.profileCompleted
        session.commit()
        token = ""
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        elif x_auth_token:
            token = x_auth_token.strip()
        return AuthOut(
            token=token,
            userId=user.id,
            fullName=user.full_name,
            email=user.email,
            role=user.role,
            profileCompleted=user.profile_completed,
        )


@app.post("/api/startups/register", response_model=StartupOut)
def register_startup(
    payload: StartupRegistrationIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> StartupOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "startup":
        raise HTTPException(status_code=403, detail="Only startup accounts can register startup profiles")

    now = datetime.utcnow()
    with Session(engine) as session:
        user = session.get(UserAuthRecord, auth_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        existing = session.execute(select(StartupRecord).where(StartupRecord.user_id == auth_user.id)).scalar_one_or_none()
        if existing is None:
            existing = StartupRecord(
                user_id=auth_user.id,
                company_name=payload.companyName.strip(),
                website_url=payload.websiteUrl.strip(),
                industry=payload.industry.strip(),
                product_stage=payload.productStage.strip(),
                tech_stack=payload.techStack.strip(),
                team_size=payload.teamSize,
                squad_summary=payload.squadSummary.strip(),
                intentions=payload.intentions.strip(),
                status="pending",
                tasks_posted=0,
                number_of_tasks=0,
                updated_at=now,
            )
            session.add(existing)
        else:
            existing.company_name = payload.companyName.strip()
            existing.website_url = payload.websiteUrl.strip()
            existing.industry = payload.industry.strip()
            existing.product_stage = payload.productStage.strip()
            existing.tech_stack = payload.techStack.strip()
            existing.team_size = payload.teamSize
            existing.squad_summary = payload.squadSummary.strip()
            existing.intentions = payload.intentions.strip()
            existing.status = "pending"
            existing.review_note = None
            existing.updated_at = now
        user.profile_completed = True
        session.commit()
        session.refresh(existing)
        return startup_to_out(existing)


@app.get("/api/startups/me", response_model=StartupOut)
def get_my_startup_profile(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> StartupOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "startup":
        raise HTTPException(status_code=403, detail="Only startup accounts can read startup profile")

    with Session(engine) as session:
        startup = session.execute(select(StartupRecord).where(StartupRecord.user_id == auth_user.id)).scalar_one_or_none()
        if startup is None:
            raise HTTPException(status_code=404, detail="Startup profile not found")
        return startup_to_out(startup)


@app.get("/api/startups/pending", response_model=list[StartupOut])
def list_pending_startups(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> list[StartupOut]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can review startup registrations")

    with Session(engine) as session:
        rows = session.execute(select(StartupRecord).where(StartupRecord.status == "pending")).scalars().all()
        return [startup_to_out(row) for row in rows]


@app.patch("/api/startups/{startup_id}/review", response_model=StartupOut)
def review_startup_registration(
    startup_id: int,
    payload: StartupReviewIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> StartupOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can review startup registrations")

    with Session(engine) as session:
        row = session.get(StartupRecord, startup_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Startup profile not found")
        row.status = payload.status
        row.review_note = payload.reviewNote
        row.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(row)
        log_admin_action(auth_user.id, "review_startup", "startup", str(startup_id), note=f"status={row.status}")
        return startup_to_out(row)


@app.post("/api/startup-task-requests", response_model=StartupTaskRequestOut)
def create_startup_task_request(
    payload: StartupTaskRequestIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> StartupTaskRequestOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "startup":
        raise HTTPException(status_code=403, detail="Only startup accounts can create task requests")

    with Session(engine) as session:
        startup = session.execute(select(StartupRecord).where(StartupRecord.user_id == auth_user.id)).scalar_one_or_none()
        if startup is None:
            raise HTTPException(status_code=403, detail="Complete startup registration first")
        if startup.status != "approved":
            raise HTTPException(status_code=403, detail="Startup account must be approved before posting task requests")
        details = payload.details.strip()
        acceptance_rules = payload.acceptanceRules.strip()
        validate_task_request_quality(details, acceptance_rules)

        row = StartupTaskRequestRecord(
            startup_id=startup.id,
            startup_user_id=auth_user.id,
            title=payload.title.strip(),
            language=payload.language.strip(),
            reward=payload.reward,
            details=details,
            acceptance_rules=acceptance_rules,
            status="pending",
            admin_note=None,
            published_to_tasks=False,
        )
        session.add(row)

        startup.number_of_tasks = int(startup.number_of_tasks or 0) + 1
        startup.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(row)
        return startup_request_to_out(row)


@app.get("/api/startup-task-requests", response_model=list[StartupTaskRequestOut])
def list_startup_task_requests(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> list[StartupTaskRequestOut]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)

    with Session(engine) as session:
        stmt = select(StartupTaskRequestRecord)
        if auth_user.role == "startup":
            stmt = stmt.where(StartupTaskRequestRecord.startup_user_id == auth_user.id)
        elif auth_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not allowed to list startup task requests")
        rows = session.execute(stmt).scalars().all()
        return [startup_request_to_out(row) for row in rows]


@app.patch("/api/startup-task-requests/{request_id}/review", response_model=StartupTaskRequestOut)
def review_startup_task_request(
    request_id: int,
    payload: StartupTaskRequestReviewIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> StartupTaskRequestOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can review startup task requests")

    with Session(engine) as session:
        row = session.get(StartupTaskRequestRecord, request_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Startup task request not found")
        was_published = bool(row.published_to_tasks)
        row.status = payload.status
        row.admin_note = payload.adminNote
        row.published_to_tasks = bool(payload.publishToTasks and payload.status == "approved")
        row.updated_at = datetime.utcnow()
        if row.published_to_tasks:
            startup = session.get(StartupRecord, row.startup_id)
            if startup is not None:
                generated_task_id = task_id_for_startup_request(row.id)
                existing_task = session.get(TaskRecord, generated_task_id)
                if existing_task is None:
                    summary = (row.details[:140] + "...") if len(row.details) > 140 else row.details
                    session.add(
                        TaskRecord(
                            id=generated_task_id,
                            title=row.title,
                            language=row.language,
                            reward=row.reward,
                            slots=slots_for_reward(row.reward),
                            status="open",
                            startup_name=startup.company_name,
                            summary=summary,
                            description=row.details,
                            endpoints="Provided by startup during handoff",
                            layout="Repository layout to be provided by startup",
                            run_instructions="Run instructions to be provided by startup",
                        )
                    )
                else:
                    existing_task.title = row.title
                    existing_task.language = row.language
                    existing_task.reward = row.reward
                    existing_task.slots = slots_for_reward(row.reward)
                    existing_task.status = "open"
                    existing_task.startup_name = startup.company_name
                    existing_task.summary = (row.details[:140] + "...") if len(row.details) > 140 else row.details
                    existing_task.description = row.details
                    existing_task.endpoints = "Provided by startup during handoff"
                    existing_task.layout = "Repository layout to be provided by startup"
                    existing_task.run_instructions = "Run instructions to be provided by startup"
                if not was_published:
                    startup.tasks_posted = int(startup.tasks_posted or 0) + 1
                startup.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(row)
        log_admin_action(auth_user.id, "review_startup_task_request", "startup_task_request", str(request_id), note=f"status={row.status},published={row.published_to_tasks}")
        return startup_request_to_out(row)


@app.get("/api/startup-task-deletion-requests", response_model=list[StartupTaskDeletionRequestOut])
def list_startup_task_deletion_requests(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> list[StartupTaskDeletionRequestOut]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    with Session(engine) as session:
        stmt = select(StartupTaskDeletionRequestRecord)
        if auth_user.role == "startup":
            stmt = stmt.where(StartupTaskDeletionRequestRecord.startup_user_id == auth_user.id)
        elif auth_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not allowed to list deletion requests")
        rows = session.execute(stmt).scalars().all()
        return [startup_deletion_request_to_out(row) for row in rows]


@app.patch("/api/startup-task-deletion-requests/{request_id}/review", response_model=StartupTaskDeletionRequestOut)
def review_startup_task_deletion_request(
    request_id: int,
    payload: StartupTaskDeletionReviewIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> StartupTaskDeletionRequestOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "startup":
        raise HTTPException(status_code=403, detail="Only startup owners can approve or reject deletion requests")
    with Session(engine) as session:
        row = session.get(StartupTaskDeletionRequestRecord, request_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Deletion request not found")
        if row.startup_user_id != auth_user.id:
            raise HTTPException(status_code=403, detail="You can only review your startup deletion requests")
        if row.status != "pending":
            raise HTTPException(status_code=400, detail="Deletion request already resolved")
        row.status = payload.status
        if payload.note:
            row.note = payload.note.strip()
        row.updated_at = datetime.utcnow()
        if row.status == "approved":
            task = session.get(TaskRecord, row.task_id)
            if task is not None:
                session.delete(task)
        session.commit()
        session.refresh(row)
        log_admin_action(
            row.admin_user_id,
            "startup_reviewed_task_deletion",
            "task_deletion_request",
            str(row.id),
            note=f"status={row.status}",
        )
        return startup_deletion_request_to_out(row)


def payout_to_out(payout: PayoutRequestRecord) -> PayoutRequestOut:
    return PayoutRequestOut(
        id=payout.id,
        userId=payout.user_id,
        amount=payout.amount,
        provider=payout.provider,
        destinationRef=payout.destination_ref,
        providerPayoutId=payout.provider_payout_id,
        status=payout.status,
        createdAt=payout.created_at,
    )


@app.post("/api/payout-requests", response_model=PayoutRequestOut)
def create_payout_request(
    payload: PayoutRequestIn,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> PayoutRequestOut:
    apply_rate_limit("payout_create", request)
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "contributor":
        raise HTTPException(status_code=403, detail="Only contributors can request payouts")
    if auth_user.id != payload.userId:
        raise HTTPException(status_code=403, detail="Payout identity mismatch")
    with Session(engine) as session:
        user = session.get(UserAuthRecord, payload.userId)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        if user.role != "contributor":
            raise HTTPException(status_code=403, detail="Only contributors can request payouts")
        if not user.profile_completed:
            raise HTTPException(status_code=403, detail="Complete your contributor profile before requesting payouts")

    with Session(engine) as session:
        record = PayoutRequestRecord(
            user_id=payload.userId,
            amount=payload.amount,
            provider=payload.provider,
            destination_ref=payload.destinationRef,
            status="pending",
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return payout_to_out(record)


@app.get("/api/payments/stripe-config", response_model=StripeConfigOut)
def get_stripe_config() -> StripeConfigOut:
    publishable = stripe_publishable_key()
    if not publishable:
        raise HTTPException(status_code=503, detail="Stripe publishable key is not configured")
    return StripeConfigOut(publishableKey=publishable)


@app.post("/api/payments/stripe/setup-intent", response_model=StripeSetupIntentOut)
def create_stripe_setup_intent(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> StripeSetupIntentOut:
    apply_rate_limit("payment_method_create", request)
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "contributor":
        raise HTTPException(status_code=403, detail="Only contributors can add Stripe card methods")
    secret_key = stripe_secret_key()
    if not secret_key:
        raise HTTPException(status_code=503, detail="Stripe secret key is not configured")
    if stripe is None:
        raise HTTPException(status_code=503, detail="Stripe SDK is not installed")
    stripe.api_key = secret_key
    try:
        intent = stripe.SetupIntent.create(
            payment_method_types=["card"],
            usage="off_session",
            metadata={"platform_user_id": str(auth_user.id)},
        )
        return StripeSetupIntentOut(clientSecret=intent.client_secret, setupIntentId=intent.id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Stripe setup intent failed: {exc}") from exc


@app.post("/api/payment-methods", response_model=PaymentMethodOut)
def create_payment_method(
    payload: PaymentMethodIn,
    request: Request,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> PaymentMethodOut:
    apply_rate_limit("payment_method_create", request)
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "contributor":
        raise HTTPException(status_code=403, detail="Only contributors can add payment methods")
    if not auth_user.profile_completed:
        raise HTTPException(status_code=403, detail="Complete your contributor profile before adding payment methods")

    with Session(engine) as session:
        user = session.get(UserAuthRecord, auth_user.id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        if payload.methodType == "paypal":
            email = (payload.paypalEmail or "").strip().lower()
            if "@" not in email:
                raise HTTPException(status_code=400, detail="Valid PayPal email is required")
            row = PaymentMethodRecord(
                user_id=auth_user.id,
                method_type="paypal",
                provider="paypal",
                provider_token=f"PP-{secrets.token_hex(8).upper()}",
                billing_email=email,
            )
        else:
            stripe_pm_id = (payload.stripePaymentMethodId or "").strip()
            if not stripe_pm_id:
                raise HTTPException(status_code=400, detail="stripePaymentMethodId is required for card methods")
            customer_id = ensure_stripe_customer(session, user)
            secret_key = stripe_secret_key()
            if not secret_key:
                raise HTTPException(status_code=503, detail="Stripe secret key is not configured")
            if stripe is None:
                raise HTTPException(status_code=503, detail="Stripe SDK is not installed")
            stripe.api_key = secret_key
            try:
                stripe.PaymentMethod.attach(stripe_pm_id, customer=customer_id)
            except Exception:
                # Already attached or attach error; continue with retrieval and ownership checks.
                pass
            try:
                stripe_pm = stripe.PaymentMethod.retrieve(stripe_pm_id)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Could not fetch Stripe payment method: {exc}") from exc
            if stripe_pm.get("customer") != customer_id:
                raise HTTPException(status_code=403, detail="Stripe payment method does not belong to this account")
            card_info = stripe_pm.get("card") or {}
            billing_details = stripe_pm.get("billing_details") or {}
            row = PaymentMethodRecord(
                user_id=auth_user.id,
                method_type="card",
                provider="stripe",
                provider_token=stripe_pm_id,
                card_brand=str(card_info.get("brand") or "card"),
                card_last4=str(card_info.get("last4") or ""),
                cardholder_name=str(billing_details.get("name") or payload.cardholderName or "").strip() or None,
                exp_month=card_info.get("exp_month"),
                exp_year=card_info.get("exp_year"),
                billing_email=str((billing_details.get("email") or payload.billingEmail or "")).strip().lower() or None,
            )
        session.add(row)
        session.commit()
        session.refresh(row)
        return payment_method_to_out(row)


@app.get("/api/payment-methods/me", response_model=list[PaymentMethodOut])
def list_my_payment_methods(
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> list[PaymentMethodOut]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    with Session(engine) as session:
        rows = session.execute(
            select(PaymentMethodRecord).where(PaymentMethodRecord.user_id == auth_user.id)
        ).scalars().all()
        return [payment_method_to_out(row) for row in rows]


@app.delete("/api/payment-methods/{method_id}")
def delete_payment_method(
    method_id: int,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> dict[str, str]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    with Session(engine) as session:
        row = session.get(PaymentMethodRecord, method_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Payment method not found")
        if row.user_id != auth_user.id and auth_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not allowed to remove this payment method")
        if row.provider == "stripe":
            secret_key = stripe_secret_key()
            if secret_key and stripe is not None and row.provider_token:
                stripe.api_key = secret_key
                try:
                    stripe.PaymentMethod.detach(row.provider_token)
                except Exception:
                    # Method may already be detached or unavailable; local cleanup still proceeds.
                    pass
        session.delete(row)
        session.commit()
        return {"message": "Payment method removed"}


@app.get("/api/payout-requests", response_model=list[PayoutRequestOut])
def list_payout_requests(
    user_id: Optional[int] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> list[PayoutRequestOut]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    with Session(engine) as session:
        stmt = select(PayoutRequestRecord)
        if auth_user.role == "admin":
            if user_id is not None:
                stmt = stmt.where(PayoutRequestRecord.user_id == user_id)
        elif auth_user.role == "contributor":
            stmt = stmt.where(PayoutRequestRecord.user_id == auth_user.id)
        else:
            raise HTTPException(status_code=403, detail="Not allowed to list payout requests")
        rows = session.execute(stmt).scalars().all()
        return [payout_to_out(row) for row in rows]


@app.patch("/api/payout-requests/{payout_id}", response_model=PayoutRequestOut)
def update_payout_request(
    payout_id: int,
    payload: PayoutStatusUpdateIn,
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> PayoutRequestOut:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    if auth_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update payout request status")
    with Session(engine) as session:
        row = session.get(PayoutRequestRecord, payout_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Payout request not found")
        row.status = payload.status
        if payload.providerPayoutId:
            row.provider_payout_id = payload.providerPayoutId

        if row.status == "paid":
            receipt = session.execute(
                select(PaymentReceiptRecord).where(PaymentReceiptRecord.payout_request_id == row.id)
            ).scalar_one_or_none()
            if receipt is None:
                provider_ref = row.provider_payout_id or f"{row.provider.upper()}-{secrets.token_hex(6)}"
                session.add(
                    PaymentReceiptRecord(
                        payout_request_id=row.id,
                        user_id=row.user_id,
                        provider=row.provider,
                        provider_reference=provider_ref,
                        amount=row.amount,
                    )
                )

        session.commit()
        session.refresh(row)
        log_admin_action(auth_user.id, "update_payout_status", "payout_request", str(row.id), note=f"status={row.status}")
        return payout_to_out(row)


@app.get("/api/receipts", response_model=list[ReceiptOut])
def list_receipts(
    user_id: Optional[int] = Query(default=None),
    authorization: Optional[str] = Header(default=None),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
) -> list[ReceiptOut]:
    auth_user = resolve_user_from_token(authorization, x_auth_token)
    with Session(engine) as session:
        stmt = select(PaymentReceiptRecord)
        if auth_user.role == "admin":
            if user_id is not None:
                stmt = stmt.where(PaymentReceiptRecord.user_id == user_id)
        elif auth_user.role == "contributor":
            stmt = stmt.where(PaymentReceiptRecord.user_id == auth_user.id)
        else:
            raise HTTPException(status_code=403, detail="Not allowed to list receipts")
        rows = session.execute(stmt).scalars().all()
        return [receipt_to_out(row) for row in rows]


def _compact_json(value: dict) -> str:
    serialized = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    return serialized[:4000]


def sanitize_analytics_metadata(metadata: dict) -> dict:
    safe: dict[str, str | int | float | bool] = {}
    for key, value in (metadata or {}).items():
        if key not in ANALYTICS_METADATA_ALLOWED_KEYS:
            continue
        if isinstance(value, (bool, int, float)):
            safe[key] = value
            continue
        value_str = str(value).strip()
        if not value_str:
            continue
        safe[key] = value_str[:ANALYTICS_METADATA_MAX_CHARS]
    return safe


def validate_task_request_quality(details: str, acceptance_rules: str) -> None:
    details_l = details.lower()
    acceptance_l = acceptance_rules.lower()
    detail_signals = ["repro", "step", "expected", "actual"]
    acceptance_signals = ["accept", "done", "verify", "test"]
    if sum(1 for token in detail_signals if token in details_l) < 2:
        raise HTTPException(
            status_code=400,
            detail="Add clearer repro steps and expected/actual behavior so contributors can trust the brief.",
        )
    if sum(1 for token in acceptance_signals if token in acceptance_l) < 1:
        raise HTTPException(
            status_code=400,
            detail="Acceptance rules must explain what done looks like (accept/verify/test).",
        )


def validate_runtime_config() -> None:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        if not AUTH_COOKIE_SECURE:
            raise RuntimeError("AUTH_COOKIE_SECURE must be 1 in production")
        if AUTH_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
            raise RuntimeError("AUTH_COOKIE_SAMESITE must be one of lax/strict/none")
        if not CORS_ALLOW_ORIGINS:
            raise RuntimeError("CORS_ALLOW_ORIGINS must include at least one trusted origin in production")
        if not STRIPE_WEBHOOK_SECRET:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET is required in production")


def handle_provider_webhook(provider: str, payload: WebhookIn) -> dict[str, str]:
    with Session(engine) as session:
        try:
            session.add(
                WebhookEventRecord(
                    provider=provider,
                    event_id=payload.eventId,
                    payload=_compact_json(payload.payload),
                )
            )
            session.flush()
        except IntegrityError:
            session.rollback()
            return {"message": "Event already processed"}

        if payload.payoutRequestId is not None:
            payout = session.get(PayoutRequestRecord, payload.payoutRequestId)
            if payout is not None:
                if payload.status in {"paid", "rejected", "pending"}:
                    payout.status = payload.status
                if payload.providerPayoutId:
                    payout.provider_payout_id = payload.providerPayoutId
                if payout.status == "paid":
                    receipt = session.execute(
                        select(PaymentReceiptRecord).where(PaymentReceiptRecord.payout_request_id == payout.id)
                    ).scalar_one_or_none()
                    if receipt is None:
                        provider_ref = payout.provider_payout_id or f"{payout.provider.upper()}-{secrets.token_hex(6)}"
                        session.add(
                            PaymentReceiptRecord(
                                payout_request_id=payout.id,
                                user_id=payout.user_id,
                                provider=payout.provider,
                                provider_reference=provider_ref,
                                amount=payout.amount,
                            )
                        )

        session.commit()
    return {"message": "Webhook processed"}


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict[str, str]:
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe webhook secret is not configured")
    if stripe is None:
        raise HTTPException(status_code=503, detail="Stripe SDK is not installed")
    signature = request.headers.get("stripe-signature", "")
    body = await request.body()
    try:
        event = stripe.Webhook.construct_event(body, signature, STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook signature: {exc}") from exc

    event_data = event.get("data", {}).get("object", {}) or {}
    payout_request_id_raw = (
        event_data.get("metadata", {}).get("payoutRequestId")
        or event_data.get("metadata", {}).get("payout_request_id")
    )
    payout_request_id = int(payout_request_id_raw) if str(payout_request_id_raw or "").isdigit() else None
    status = None
    if event.get("type") == "payout.paid":
        status = "paid"
    elif event.get("type") in {"payout.failed", "payout.canceled"}:
        status = "rejected"
    elif event.get("type", "").startswith("payout."):
        status = "pending"

    payload = WebhookIn(
        eventId=str(event.get("id") or ""),
        payoutRequestId=payout_request_id,
        providerPayoutId=str(event_data.get("id") or "") or None,
        status=status,
        payload={"type": event.get("type"), "object": event_data},
    )
    return handle_provider_webhook("stripe", payload)


@app.post("/api/webhooks/paypal")
def paypal_webhook(payload: WebhookIn, request: Request) -> dict[str, str]:
    if PAYPAL_WEBHOOK_TOKEN:
        token = request.headers.get("x-webhook-token", "")
        if not hmac.compare_digest(token, PAYPAL_WEBHOOK_TOKEN):
            raise HTTPException(status_code=401, detail="Invalid webhook token")
    return handle_provider_webhook("paypal", payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=False)
