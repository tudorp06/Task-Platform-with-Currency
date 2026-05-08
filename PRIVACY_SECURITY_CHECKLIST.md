# Privacy & Security Checklist (Beta Gate)

Use this before inviting external testers.

## Environment

- Set `CORS_ALLOW_ORIGINS` to exact frontend origins (comma-separated).
- Set `SESSION_TTL_HOURS` (recommended `24` to `72` in beta).
- Keep `ALLOW_ADMIN_SIGNUP=0` in production-like environments.
- If you ever enable admin signup, set `ADMIN_SIGNUP_CODE` and rotate it.
- Set Stripe keys only in environment (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`).

## Auth & Access Control

- Verify auth uses HttpOnly cookie session (`appcontributor_session`) and not localStorage bearer token.
- Verify admin signup is blocked from public UI/API.
- Verify disabled users cannot log in or use existing tokens.
- Verify expired sessions return `401`.
- Verify contributors cannot read other users' payout requests/receipts.
- Verify only admins can:
  - import tasks from URL
  - patch payout statuses
  - review startups / startup task requests
  - create/update/delete tasks via admin endpoints

## Rate Limiting

- Verify repeated login attempts trigger `429`.
- Verify repeated signup attempts trigger `429`.
- Verify payout creation flood triggers `429`.
- Verify payment method creation/setup-intent flood triggers `429`.

## Payments & Privacy

- Verify card details are collected via Stripe Elements.
- Verify backend stores only tokenized payment method metadata (brand/last4/expiry).
- Verify no full card number or CVV is persisted.
- Verify payout destination references use provider token IDs only.

## Auditability

- Verify admin actions create entries in `admin_audit_logs` for:
  - user access updates
  - task create/update/delete
  - startup reviews and task request reviews
  - payout status updates
  - task imports

## Manual Smoke Checks

1. Create contributor account -> complete onboarding -> add card method -> request payout.
2. Create startup account -> submit startup registration -> approve via admin -> submit task request -> approve+publish.
3. Login as contributor and confirm:
   - cannot access admin endpoints
   - cannot list other users' receipts/payouts.
4. Disable a user from admin panel and verify access immediately fails.
