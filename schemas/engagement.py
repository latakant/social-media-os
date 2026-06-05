from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class EngagementResult:
    impressions: int
    reach: int
    likes: int
    comments: int
    shares: int
    saves: int
    engagement_rate: float
    collected_at: datetime


@dataclass
class PostRecord:
    post_id: str
    platform: str
    generated_content: str
    approved_content: str
    posted_at: datetime
    engagement_result: EngagementResult | None = None
    experiment_id: str | None = None
    platform_post_id: str | None = None   # LinkedIn URN returned after publishing


@dataclass
class Experiment:
    id: str
    hypothesis: str
    variable: str
    started_at: datetime
    post_ids: list[str] = field(default_factory=list)
    outcome: str | None = None
    metric_delta: float | None = None
    confidence: Literal['low', 'medium', 'high'] | None = None
    concluded_at: datetime | None = None
