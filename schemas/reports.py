from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class ReviewResult:
    verdict: Literal['APPROVE', 'REVISE', 'REJECT']
    passed: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class Finding:
    category: Literal['audience', 'growth', 'content', 'engagement']
    observation: str
    signal_strength: Literal['strong', 'moderate', 'weak']
    supporting_metrics: dict[str, float]


@dataclass
class ObservationReport:
    platform: str
    period_end: datetime
    generated_at: datetime
    findings: list[Finding]
    hypotheses: list[str]
    recommendations: list[str]
    top_priority: str
