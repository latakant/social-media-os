from typing import Protocol


class PlatformAgent(Protocol):
    """Converts a content contract into platform-native text."""

    def adapt(self, contract: dict) -> str: ...
