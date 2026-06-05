"""Fetch your LinkedIn Person URN from your access token.

Run: python get_linkedin_urn.py
Copy the URN printed here into .env as LINKEDIN_PERSON_URN
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
if not token:
    print("LINKEDIN_ACCESS_TOKEN not set in .env")
    raise SystemExit(1)

resp = requests.get(
    "https://api.linkedin.com/v2/userinfo",
    headers={"Authorization": f"Bearer {token}"},
    timeout=10,
)

if resp.status_code != 200:
    print(f"Error {resp.status_code}: {resp.text}")
    raise SystemExit(1)

data = resp.json()
sub = data.get("sub", "")
urn = f"urn:li:person:{sub}"

print(f"Name:  {data.get('name', 'unknown')}")
print(f"Email: {data.get('email', 'unknown')}")
print(f"\nAdd to .env:")
print(f"LINKEDIN_PERSON_URN={urn}")
