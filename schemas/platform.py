from dataclasses import dataclass
from datetime import datetime


@dataclass
class PlatformSnapshot:
    platform: str
    captured_at: datetime
    period_days: int

    reach: int
    impressions: int
    engagements: int
    followers_net: int        # gained - lost
    profile_visits: int

    engagement_rate: float    # engagements / reach
    conversion_rate: float    # followers_net / profile_visits
