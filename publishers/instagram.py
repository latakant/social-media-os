import os
import time

import cloudinary
import cloudinary.uploader
import requests

from publishers.base import PublishError, PublishResult

_GRAPH = "https://graph.facebook.com/v19.0"
_POLL_MAX = 10
_POLL_INTERVAL = 3  # seconds between container status checks


class InstagramPublisher:

    def __init__(self) -> None:
        self._token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
        self._user_id = os.environ["INSTAGRAM_USER_ID"]
        cloudinary.config(
            cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
            api_key=os.environ["CLOUDINARY_API_KEY"],
            api_secret=os.environ["CLOUDINARY_API_SECRET"],
        )

    def post(self, content: str, image_path: str | None = None) -> PublishResult:
        if not image_path:
            raise PublishError(400, "Instagram requires an image")

        image_url = self._upload_image(image_path)
        creation_id = self._create_container(image_url, content)
        self._wait_for_container(creation_id)
        post_id = self._publish_container(creation_id)
        return PublishResult(platform_post_id=post_id)

    # ── Steps ───────────────────────────────────────────────────────────────

    def _upload_image(self, image_path: str) -> str:
        result = cloudinary.uploader.upload(
            image_path,
            folder="social-intel",
            resource_type="image",
        )
        return result["secure_url"]

    def _create_container(self, image_url: str, caption: str) -> str:
        resp = requests.post(
            f"{_GRAPH}/{self._user_id}/media",
            params={"image_url": image_url, "caption": caption,
                    "access_token": self._token},
            timeout=15,
        )
        if resp.status_code != 200:
            raise PublishError(resp.status_code, resp.text)
        return resp.json()["id"]

    def _wait_for_container(self, creation_id: str) -> None:
        """Poll until the media container is FINISHED processing."""
        for _ in range(_POLL_MAX):
            resp = requests.get(
                f"{_GRAPH}/{creation_id}",
                params={"fields": "status_code", "access_token": self._token},
                timeout=10,
            )
            if resp.status_code != 200:
                raise PublishError(resp.status_code, resp.text)
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise PublishError(500, f"Container failed: {resp.text}")
            time.sleep(_POLL_INTERVAL)
        raise PublishError(408, "Container timed out after polling")

    def _publish_container(self, creation_id: str) -> str:
        resp = requests.post(
            f"{_GRAPH}/{self._user_id}/media_publish",
            params={"creation_id": creation_id, "access_token": self._token},
            timeout=15,
        )
        if resp.status_code != 200:
            raise PublishError(resp.status_code, resp.text)
        return resp.json()["id"]
