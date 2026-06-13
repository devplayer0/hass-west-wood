#!/usr/bin/env python
"""Log in to the West Wood Club (PerfectGym) API and print the bearer token.

The token is written to stdout (and nothing else), so it can be piped to a file:

    python login.py > token.txt

Credentials are read from the WESTWOOD_EMAIL and WESTWOOD_PASSWORD environment
variables; any that are missing are prompted for on the terminal. Prompts and
errors go to stderr, keeping stdout clean for the token.
"""

import getpass
import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = "https://goapi2.perfectgym.com"
WHITE_LABEL_ID = "7d073db5-0ef8-4d78-89ec-4a8bebaf4cbc"
USER_AGENT = (
    "West Wood Club/1.28.3.0 "
    "(com.perfectgym.perfectgymgo2.westwoodclub; build:1028003000; Android 16)"
)


def log_in(email: str, password: str) -> str:
    """Return the bearer token (the value for the Authorization header)."""
    body = json.dumps(
        {
            "email": email,
            "password": password,
            "clientApplicationInfo": {
                "type": "whitelabel",
                "whiteLabelId": WHITE_LABEL_ID,
            },
        }
    ).encode()

    request = urllib.request.Request(
        f"{BASE_URL}/v1/Authorize/LogInWithEmail",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept-Language": "en",
            "X-Go-App-Platform": "Android",
            "X-Go-App-Version": "1.28.3",
            "X-Go-White-Label-ID": WHITE_LABEL_ID,
            "User-Agent": USER_AGENT,
        },
    )

    with urllib.request.urlopen(request) as response:
        payload = json.load(response)

    if payload.get("errors"):
        raise SystemExit(f"login failed: {payload['errors']}")

    data = payload.get("data") or {}
    token = data.get("token")
    if not token:
        raise SystemExit(f"no token in response: {payload}")
    return token


def main() -> None:
    email = os.environ.get("WESTWOOD_EMAIL") or input("Email: ")
    password = os.environ.get("WESTWOOD_PASSWORD") or getpass.getpass("Password: ")

    try:
        token = log_in(email, password)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"request failed: {exc.reason}")

    print(token)


if __name__ == "__main__":
    main()
