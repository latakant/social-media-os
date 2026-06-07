"""AnalyticsService — analyzes platform metrics and returns structured observations.

Service: takes a snapshot, returns an ObservationReport. No side effects,
no state. The caller decides what to do with the findings.
"""

import json
from datetime import datetime, timezone

from groq import Groq

from schemas.platform import PlatformSnapshot
from schemas.reports import Finding, ObservationReport


_SYSTEM = """You are a social media intelligence analyst.

You receive platform metrics and produce structured observations. You identify patterns,
diagnose problems, and recommend actions. You do not generate content — only analysis.

Always return valid JSON matching the exact schema provided. No markdown. No prose outside JSON."""


_PROMPT = """Analyze this social media platform snapshot and return an ObservationReport as JSON.

Platform snapshot:
{snapshot_json}

Return JSON with this exact structure:
{{
  "findings": [
    {{
      "category": "audience|growth|content|engagement",
      "observation": "one clear sentence",
      "signal_strength": "strong|moderate|weak",
      "supporting_metrics": {{"metric_name": numeric_value}}
    }}
  ],
  "hypotheses": ["one sentence explaining why the numbers look this way"],
  "recommendations": ["specific actionable step"],
  "top_priority": "single most important action to take right now"
}}

Rules:
- findings: 3–6 entries, one distinct insight each
- hypotheses: explain causation, not correlation
- recommendations: specific, not generic ("Post at 19:00 IST" not "Post at peak times")
- top_priority: one sentence, the single highest-leverage action"""


class AnalyticsService:

    def __init__(self) -> None:
        self._client = Groq()

    def analyze(self, snapshot: PlatformSnapshot) -> ObservationReport:
        payload = {
            "platform": snapshot.platform,
            "period_days": snapshot.period_days,
            "reach": snapshot.reach,
            "impressions": snapshot.impressions,
            "engagements": snapshot.engagements,
            "followers_net": snapshot.followers_net,
            "profile_visits": snapshot.profile_visits,
            "engagement_rate": snapshot.engagement_rate,
            "conversion_rate": snapshot.conversion_rate,
        }

        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _PROMPT.format(
                    snapshot_json=json.dumps(payload, indent=2)
                )},
            ],
        )

        raw = json.loads(response.choices[0].message.content)

        findings = [
            Finding(
                category=f["category"],
                observation=f["observation"],
                signal_strength=f["signal_strength"],
                supporting_metrics=f["supporting_metrics"],
            )
            for f in raw["findings"]
        ]

        return ObservationReport(
            platform=snapshot.platform,
            period_end=snapshot.captured_at,
            generated_at=datetime.now(timezone.utc),
            findings=findings,
            hypotheses=raw["hypotheses"],
            recommendations=raw["recommendations"],
            top_priority=raw["top_priority"],
        )
