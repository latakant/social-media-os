"""One-shot LinkedIn OAuth flow.

Setup:
  1. Create app at developers.linkedin.com
  2. Add redirect URI: http://localhost:8080/callback
  3. Request products: "Share on LinkedIn" + "Sign In with LinkedIn using OpenID Connect"
  4. Add to .env:
       LINKEDIN_CLIENT_ID=your_client_id
       LINKEDIN_CLIENT_SECRET=your_client_secret
  5. Run: python get_linkedin_token.py
  6. Browser opens -> log in -> token printed and saved to .env
"""

import os
import sys
import webbrowser
import urllib.parse
import urllib.request
import json
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI  = "http://localhost:8080/callback"
SCOPES        = "openid email profile w_member_social"
PORT          = 8080

if not CLIENT_ID or not CLIENT_SECRET:
    print("Missing LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET in .env")
    sys.exit(1)

STATE = "localdev"
_auth_code: list[str] = []


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        if params.get("state") != STATE:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State mismatch. Try again.")
            return

        code = params.get("code", "")
        _auth_code.append(code)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Authorized. You can close this tab.</h2>")

    def log_message(self, *args) -> None:
        pass  # silence request logs


def exchange_code(code: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type":    "authorization_code",
        "code":          code,
        "redirect_uri":  REDIRECT_URI,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_urn(token: str) -> str:
    req = urllib.request.Request(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return f"urn:li:person:{data['sub']}", data.get("name", "")


def save_to_env(token: str, urn: str) -> None:
    env_path = Path(".env")
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = {}

    new_lines = []
    for line in lines:
        if line.startswith("LINKEDIN_ACCESS_TOKEN="):
            new_lines.append(f"LINKEDIN_ACCESS_TOKEN={token}")
            updated["token"] = True
        elif line.startswith("LINKEDIN_PERSON_URN="):
            new_lines.append(f"LINKEDIN_PERSON_URN={urn}")
            updated["urn"] = True
        else:
            new_lines.append(line)

    if "token" not in updated:
        new_lines.append(f"LINKEDIN_ACCESS_TOKEN={token}")
    if "urn" not in updated:
        new_lines.append(f"LINKEDIN_PERSON_URN={urn}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main() -> None:
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        + urllib.parse.urlencode({
            "response_type": "code",
            "client_id":     CLIENT_ID,
            "redirect_uri":  REDIRECT_URI,
            "state":         STATE,
            "scope":         SCOPES,
        })
    )

    print(f"Opening browser for LinkedIn login...")
    print(f"If browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", PORT), CallbackHandler)
    print(f"Waiting for callback on port {PORT}...")
    while not _auth_code:
        server.handle_request()

    print("Got authorization code. Exchanging for token...")
    token_data = exchange_code(_auth_code[0])
    token = token_data["access_token"]
    expires_in = token_data.get("expires_in", "unknown")

    urn, name = fetch_urn(token)

    print(f"\nAuthenticated as: {name}")
    print(f"Token expires in: {expires_in}s (~{int(expires_in)//86400} days)")
    print(f"Person URN:       {urn}")

    save_to_env(token, urn)
    print("\nSaved to .env. Run python run_sprint1.py to post.")


if __name__ == "__main__":
    main()
