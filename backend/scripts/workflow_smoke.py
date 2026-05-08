from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def call(url: str, method: str = "GET", token: str = "", payload: dict | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = Request(
        url=url,
        method=method,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers=headers,
    )
    try:
        with urlopen(req, timeout=20) as res:
            body = res.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        raise RuntimeError(f"{method} {url} -> {exc.code}: {exc.read().decode('utf-8')}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal production smoke checks.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/api")
    parser.add_argument("--admin-token", default="")
    parser.add_argument("--contributor-token", default="")
    parser.add_argument("--startup-token", default="")
    args = parser.parse_args()

    health = call(f"{args.api_base}/health")
    print("Health:", health.get("status"))

    tasks = call(f"{args.api_base}/tasks")
    print("Tasks loaded:", len(tasks) if isinstance(tasks, list) else "unexpected")

    if args.admin_token:
        users = call(f"{args.api_base}/admin/users", token=args.admin_token)
        print("Admin users:", len(users) if isinstance(users, list) else "unexpected")

    if args.contributor_token:
        payouts = call(f"{args.api_base}/payout-requests", token=args.contributor_token)
        print("Contributor payouts query ok:", isinstance(payouts, list))

    if args.startup_token:
        startup_requests = call(f"{args.api_base}/startup-task-requests", token=args.startup_token)
        print("Startup task requests query ok:", isinstance(startup_requests, list))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Workflow smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
