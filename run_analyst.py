"""Run the AnalystAgent on a snapshot and store findings in DB.

Usage:
  python run_analyst.py
  python run_analyst.py --snapshot data/snapshots/june_2026.json
  python run_analyst.py --snapshot data/snapshots/june_2026.json --platform instagram
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from agents.analyst import AnalystAgent
from memory.store import get_latest_analysis, save_analysis_report
from schemas.platform import PlatformSnapshot

load_dotenv()

DIV = "=" * 52


def _load_snapshot(path: str, platform: str) -> PlatformSnapshot:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    reach = data["post_reach"]
    profile_visits = data["profile_visits"]
    gained = data["followers_gained"]
    lost = data["followers_lost"]
    return PlatformSnapshot(
        platform=platform,
        captured_at=datetime.fromisoformat(data["captured_at"]),
        period_days=data["period_days"],
        reach=reach,
        impressions=data["post_impressions"],
        engagements=data["engagements"],
        followers_net=gained - lost,
        profile_visits=profile_visits,
        engagement_rate=data["engagements"] / reach if reach else 0.0,
        conversion_rate=(gained - lost) / profile_visits if profile_visits else 0.0,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AnalystAgent on a platform snapshot")
    parser.add_argument("--snapshot", default="data/snapshots/june_2026.json",
                        help="Path to snapshot JSON file")
    parser.add_argument("--platform", default="linkedin",
                        help="Platform name (linkedin, instagram)")
    args = parser.parse_args()

    print(f"\n{DIV}")
    print("AnalystAgent")
    print(f"{DIV}\n")
    print(f"Snapshot:  {args.snapshot}")
    print(f"Platform:  {args.platform}\n")

    snapshot = _load_snapshot(args.snapshot, args.platform)
    print("Running analysis...")
    report = AnalystAgent().analyze(snapshot)

    print(f"\nTop Priority:\n  {report.top_priority}\n")

    print("Findings:")
    for f in report.findings:
        print(f"  [{f.signal_strength.upper():8}] [{f.category}] {f.observation}")

    print("\nRecommendations:")
    for r in report.recommendations:
        print(f"  • {r}")

    save_analysis_report(report)
    print(f"\n{DIV}")
    print("Findings stored in DB.")
    print(f"{DIV}\n")


if __name__ == "__main__":
    main()
