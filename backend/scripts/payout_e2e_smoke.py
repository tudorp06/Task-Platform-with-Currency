from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def call_json(url: str, method: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url=url, method=method, data=body, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run payout flow smoke checks against AppContributor API."
    )
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/api")
    parser.add_argument("--contributor-token", required=True)
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--amount", type=float, default=1.0)
    parser.add_argument(
        "--method-id",
        type=int,
        required=True,
        help="Existing payment method id belonging to contributor",
    )
    args = parser.parse_args()

    payout = call_json(
        f"{args.api_base}/payout-requests",
        "POST",
        args.contributor_token,
        {
            "userId": 0,  # ignored server-side for contributor role
            "amount": args.amount,
            "provider": "stripe",
            "destinationRef": f"method:{args.method_id}",
        },
    )
    payout_id = int(payout.get("id") or 0)
    if not payout_id:
        raise RuntimeError("API did not return payout id")
    print(f"Created payout request #{payout_id}")

    updated = call_json(
        f"{args.api_base}/payout-requests/{payout_id}",
        "PATCH",
        args.admin_token,
        {
            "status": "paid",
            "providerPayoutId": f"SMOKE-{payout_id}",
        },
    )
    print(f"Marked payout #{updated.get('id')} as {updated.get('status')}")

    receipts = call_json(
        f"{args.api_base}/receipts",
        "GET",
        args.contributor_token,
    )
    if not isinstance(receipts, list):
        raise RuntimeError("Unexpected receipts payload")
    matched = [row for row in receipts if int(row.get("payoutRequestId") or 0) == payout_id]
    if not matched:
        raise RuntimeError("No receipt found for smoke payout")
    print(f"Receipt created for payout #{payout_id}: {matched[0].get('providerReference')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
