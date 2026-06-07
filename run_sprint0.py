"""Sprint 0 validation: Instagram data → PlatformSnapshot → ObservationReport

Run: python run_sprint0.py
Done condition: top_priority correctly identifies the conversion problem.
"""

import json
from datetime import datetime

from dotenv import load_dotenv

from schemas.instagram import InstagramSnapshot
from normalizers.instagram import InstagramNormalizer
from services.analytics_service import AnalyticsService

load_dotenv()


def load_snapshot(path: str) -> InstagramSnapshot:
    with open(path) as f:
        data = json.load(f)
    data["captured_at"] = datetime.fromisoformat(data["captured_at"])
    return InstagramSnapshot(**data)


def main() -> None:
    print("=" * 50)
    print("Sprint 0 — Social Intelligence Agent")
    print("=" * 50)

    raw = load_snapshot("data/snapshots/june_2026.json")
    print(f"\nLoaded:     {raw.followers} followers · {raw.profile_visits} profile visits · {raw.story_views} story views")

    snapshot = InstagramNormalizer().normalize(raw)
    print(f"Normalized: engagement_rate={snapshot.engagement_rate:.2%} · conversion_rate={snapshot.conversion_rate:.2%}")

    print("\nAnalyzing with Claude...\n")
    report = AnalyticsService().analyze(snapshot)

    print(f"TOP PRIORITY\n  {report.top_priority}\n")

    print("FINDINGS")
    for f in report.findings:
        print(f"  [{f.signal_strength.upper():8s}] [{f.category}] {f.observation}")

    print("\nHYPOTHESES")
    for h in report.hypotheses:
        print(f"  - {h}")

    print("\nRECOMMENDATIONS")
    for r in report.recommendations:
        print(f"  -> {r}")

    print("\n" + "=" * 50)
    print("Sprint 0 complete if top_priority identifies the conversion gap.")
    print("=" * 50)


if __name__ == "__main__":
    main()
