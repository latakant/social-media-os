from dataclasses import dataclass
from typing import Protocol


@dataclass
class PublishResult:
    platform_post_id: str


class PublishError(Exception):
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        super().__init__(f"{status_code}: {body}")


class Publisher(Protocol):
    """Posts approved content to a social platform."""

    def post(self, content: str, image_path: str | None = None) -> PublishResult: ...
