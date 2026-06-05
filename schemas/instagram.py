from dataclasses import dataclass
from datetime import datetime


@dataclass
class InstagramSnapshot:
    followers: int
    profile_visits: int
    story_views: int
    post_reach: int
    post_impressions: int
    engagements: int              # likes + comments + saves + shares
    followers_gained: int
    followers_lost: int
    audience_gender: dict[str, float]   # {"male": 0.88, "female": 0.12}
    audience_age: dict[str, float]      # {"25-34": 0.45, "18-24": 0.20, ...}
    active_hours: dict[str, int]        # {"18": 320, "19": 410, ...} — hour → count
    captured_at: datetime
    period_days: int = 30
