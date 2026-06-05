import os
import time
from pathlib import Path

import requests

from publishers.base import PublishError, PublishResult


class LinkedInPublisher:
    _BASE = "https://api.linkedin.com/v2"

    def __init__(self) -> None:
        self._token = os.environ["LINKEDIN_ACCESS_TOKEN"]
        self._person_urn = os.environ["LINKEDIN_PERSON_URN"]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _upload_image(self, image_path: str) -> str:
        """Upload image to LinkedIn. Returns asset URN."""
        # Step 1 — register upload
        register_body = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": self._person_urn,
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }],
            }
        }
        resp = requests.post(
            f"{self._BASE}/assets?action=registerUpload",
            headers=self._headers(),
            json=register_body,
            timeout=15,
        )
        if resp.status_code != 200:
            raise PublishError(resp.status_code, f"Image register failed: {resp.text}")

        data = resp.json()
        upload_url = data["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset_urn = data["value"]["asset"]

        # Step 2 — upload binary
        image_bytes = Path(image_path).read_bytes()
        upload_resp = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/octet-stream",
            },
            data=image_bytes,
            timeout=30,
        )
        if upload_resp.status_code not in (200, 201):
            raise PublishError(upload_resp.status_code, f"Image upload failed: {upload_resp.text}")

        return asset_urn

    def post(self, content: str, image_path: str | None = None) -> PublishResult:
        if image_path:
            asset_urn = self._upload_image(image_path)
            share_content = {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "IMAGE",
                "media": [{
                    "status": "READY",
                    "media": asset_urn,
                }],
            }
        else:
            share_content = {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE",
            }

        body = {
            "author": self._person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": share_content,
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        for attempt in range(3):
            resp = requests.post(
                f"{self._BASE}/ugcPosts",
                headers=self._headers(),
                json=body,
                timeout=15,
            )
            if resp.status_code == 201:
                platform_post_id = resp.headers.get("x-restli-id", "unknown")
                return PublishResult(platform_post_id=platform_post_id)
            if resp.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            raise PublishError(resp.status_code, resp.text)

        raise PublishError(429, "Rate limit exceeded after 3 retries")
