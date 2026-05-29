"""Check local configuration for the OBHRM literature monitor."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
OPTIONAL_ENV = [
    "OBHRM_CONTACT_EMAIL",
    "OBHRM_CROSSREF_MAILTO",
    "OBHRM_OPENALEX_MAILTO",
    "OBHRM_LARK_WEBHOOK_URL",
    "OBHRM_LARK_WEBHOOK_SECRET",
]


def load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip().lstrip("\ufeff"), value.strip().strip('"').strip("'"))


def lark_signature(secret: str, timestamp: str) -> str:
    payload = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(payload, b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def test_lark() -> None:
    webhook = os.environ.get("OBHRM_LARK_WEBHOOK_URL")
    if not webhook:
        raise RuntimeError("OBHRM_LARK_WEBHOOK_URL is not set")
    payload = {
        "msg_type": "text",
        "content": {"text": "OBHRM literature monitor test message."},
    }
    secret = os.environ.get("OBHRM_LARK_WEBHOOK_SECRET")
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = lark_signature(secret, timestamp)
    request = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check OBHRM monitor configuration.")
    parser.add_argument("--test-lark", action="store_true", help="Send a Lark webhook test message.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv()
    print(f"Repo root: {REPO_ROOT}")
    for relative in [
        "config/monitor.example.yaml",
        "config/journal_scope.example.yaml",
        "data/whitelist",
        "outputs",
        "logs",
    ]:
        path = REPO_ROOT / relative
        print(f"{relative}: {'OK' if path.exists() else 'MISSING'}")

    print("\nEnvironment variables:")
    for name in OPTIONAL_ENV:
        value = os.environ.get(name)
        state = "set" if value else "not set"
        print(f"- {name}: {state}")

    print("\nLocal report generation does not require push variables.")
    if args.test_lark:
        test_lark()
        print("Lark test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
