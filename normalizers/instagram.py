from schemas.instagram import InstagramSnapshot
from schemas.platform import PlatformSnapshot


class InstagramNormalizer:

    def normalize(self, raw: InstagramSnapshot) -> PlatformSnapshot:
        reach = raw.post_reach
        followers_net = raw.followers_gained - raw.followers_lost

        engagement_rate = raw.engagements / reach if reach > 0 else 0.0
        conversion_rate = followers_net / raw.profile_visits if raw.profile_visits > 0 else 0.0

        return PlatformSnapshot(
            platform="instagram",
            captured_at=raw.captured_at,
            period_days=raw.period_days,
            reach=reach,
            impressions=raw.post_impressions,
            engagements=raw.engagements,
            followers_net=followers_net,
            profile_visits=raw.profile_visits,
            engagement_rate=round(engagement_rate, 4),
            conversion_rate=round(conversion_rate, 4),
        )
