"""LinkedInProfileWorkflow — generates a complete optimized LinkedIn profile.

Reads resume + brand voice + target JD, runs ProfileWriterAgent for each
section, and writes a formatted markdown document ready to copy-paste
into LinkedIn.

Usage:
    python run_profile.py
    python run_profile.py --resume path/to/resume.md --output linkedin_profile.md
"""

from __future__ import annotations

from pathlib import Path

from agents.profile_writer import ProfileWriterAgent


_BRAND_VOICE_PATH = Path("knowledge/brand_voice.md")

# ── Resume data ──────────────────────────────────────────────────────────────

_RESUME_SUMMARY = """
Agentic AI Engineer. Built Social Media OS — a production multi-agent pipeline
(StrategistAgent, InformationArchitectAgent, LayoutAgent, ReviewAgent,
VisualBlockGenerator) that converts a topic into LinkedIn posts + Instagram
captions + rendered infographics with human-in-the-loop Telegram approval.
Background in enterprise backend engineering (Salesforce, REST APIs, CI/CD).
Experience with LangGraph, LangChain, RAG, MCP, FastAPI, Docker, AWS.
"""

_ALL_SKILLS = [
    "Python", "Multi-Agent Systems", "LLM Orchestration", "LangGraph", "LangChain",
    "MCP (Model Context Protocol)", "RAG", "Prompt Engineering", "Agent Design",
    "FastAPI", "REST APIs", "Async Workflows", "Groq", "Docker", "Kubernetes",
    "AWS", "CI/CD", "Redis", "SQLite", "Playwright", "Jinja2",
    "Telegram Bot API", "LinkedIn API", "Evaluation", "Observability",
    "LangFuse", "Guardrails", "Java", "Spring Boot", "Salesforce",
]

_PROJECTS = [
    {
        "name": "Social Media OS",
        "url": "https://github.com/latakant/social-media-os",
        "description": "Production multi-agent pipeline: topic → infographic + LinkedIn post + Instagram caption, with Telegram approval gate. 5 specialized agents, ContextEngine, async parallel execution.",
        "tech": ["Python", "Groq", "Playwright", "LLM Orchestration", "Multi-Agent Systems"],
    },
    {
        "name": "Agentic Research Assistant",
        "url": "",
        "description": "LangGraph multi-agent workflow with planner, researcher, reviewer agents. FastAPI + Docker.",
        "tech": ["LangGraph", "LangChain", "FastAPI", "Docker"],
    },
    {
        "name": "RAG Knowledge Assistant",
        "url": "",
        "description": "End-to-end RAG pipeline with evaluation workflows.",
        "tech": ["LangChain", "RAG", "Vector DB"],
    },
    {
        "name": "MCP Tool Server",
        "url": "",
        "description": "Custom MCP-compatible tool server for LLM-external service interaction.",
        "tech": ["MCP", "Python"],
    },
]

_PRODAPT_BULLETS = [
    "Developed enterprise workflow automation on Salesforce (Apex, Flow, OmniStudio)",
    "Built and consumed REST APIs for cross-system data exchange",
    "Implemented integration patterns, input validation, and business logic",
    "Contributed to CI/CD pipeline and Agile delivery",
]

# ── JD summary ────────────────────────────────────────────────────────────────

_TARGET_ROLE = """
Role: Associate Agentic AI Engineer

Key requirements:
- Design and build agentic AI workflows using LangGraph, CrewAI, AutoGen
- Build multi-agent systems coordinating reasoning, tool use, memory, task execution
- Implement MCP tools and custom tool interfaces
- Orchestrate LLM interactions via LangChain — retrieval, tools, memory, agents
- Design, test, and optimize prompt strategies; support prompt versioning
- Python backend services using FastAPI; async workflows; REST APIs
- AWS (including Bedrock); Docker; Kubernetes
- Redis / ElastiCache for agent memory and caching
- Observability with Langfuse; evaluation harnesses; guardrails
- GitHub workflows, code reviews, release validation
"""


# ── Workflow ──────────────────────────────────────────────────────────────────

class LinkedInProfileWorkflow:

    def __init__(self) -> None:
        self._agent = ProfileWriterAgent()
        self._brand_voice = (
            _BRAND_VOICE_PATH.read_text(encoding="utf-8")
            if _BRAND_VOICE_PATH.exists() else ""
        )

    def run(self, resume_path: str | None = None, output_path: str = "linkedin_profile.md") -> str:
        resume_text = (
            Path(resume_path).read_text(encoding="utf-8")
            if resume_path and Path(resume_path).exists()
            else _RESUME_SUMMARY
        )

        print("Generating headline...")
        headline = self._agent.generate_headline(
            resume_summary=_RESUME_SUMMARY,
            target_role=_TARGET_ROLE,
            brand_voice=self._brand_voice,
        )
        _print_done("Headline", headline[:60])

        print("Generating About section...")
        about = self._agent.generate_about(
            resume=resume_text,
            target_role=_TARGET_ROLE,
            brand_voice=self._brand_voice,
        )
        _print_done("About", f"{len(about)} chars")

        print("Generating experience bullets — Prodapt...")
        prodapt_bullets = self._agent.generate_experience(
            role_title="Software Engineer",
            company="Prodapt",
            dates="Oct 2021 – Aug 2022",
            current_bullets=_PRODAPT_BULLETS,
            target_role=_TARGET_ROLE,
        )
        _print_done("Prodapt", f"{len(prodapt_bullets)} bullets")

        print("Generating skills...")
        skills = self._agent.generate_skills(
            all_skills=_ALL_SKILLS,
            target_role=_TARGET_ROLE,
        )
        _print_done("Skills", f"top 3: {', '.join(skills['top_3'])}")

        print("Generating Featured section...")
        featured = self._agent.generate_featured(
            projects=_PROJECTS,
            target_role=_TARGET_ROLE,
        )
        _print_done("Featured", f"{len(featured['pins'])} pins")

        doc = _build_document(
            headline=headline,
            about=about,
            prodapt_bullets=prodapt_bullets,
            skills=skills,
            featured=featured,
        )

        Path(output_path).write_text(doc, encoding="utf-8")
        print(f"\nSaved: {output_path}")
        return doc


# ── Document builder ─────────────────────────────────────────────────────────

def _build_document(
    headline: str,
    about: str,
    prodapt_bullets: list[str],
    skills: dict,
    featured: dict,
) -> str:
    char_warn = lambda text, limit: f" [OVER LIMIT] {len(text)} chars — limit is {limit}!" if len(text) > limit else f"  OK {len(text)}/{limit} chars"

    lines = [
        "# LinkedIn Profile — Latakant Sharma",
        "# Copy-paste each section into LinkedIn",
        "",
        "=" * 60,
        "",
        "## 1. HEADLINE",
        f"Character count:{char_warn(headline, 220)}",
        "",
        headline,
        "",
        "=" * 60,
        "",
        "## 2. ABOUT / SUMMARY",
        f"Character count:{char_warn(about, 2600)}",
        "",
        about,
        "",
        "=" * 60,
        "",
        "## 3. EXPERIENCE — Software Engineer at Prodapt",
        "   Oct 2021 – Aug 2022 · Bengaluru, India",
        "",
    ]

    for b in prodapt_bullets:
        lines.append(f"• {b}")

    lines += [
        "",
        "=" * 60,
        "",
        "## 4. SKILLS",
        "",
        "### Pin these 3 as Top Skills (shown on profile card):",
        "",
    ]
    for i, s in enumerate(skills["top_3"], 1):
        lines.append(f"  {i}. {s}")

    lines += [
        "",
        "### Remaining skills to add:",
        "",
    ]
    for s in skills.get("remaining_12", []):
        lines.append(f"  • {s}")

    lines += [
        "",
        "=" * 60,
        "",
        "## 5. FEATURED SECTION",
        f"   Rationale: {featured.get('rationale', '')}",
        "",
    ]

    for i, pin in enumerate(featured.get("pins", []), 1):
        lines += [
            f"### Pin {i} — {pin.get('type', '').upper()}",
            f"Title      : {pin.get('title', '')}",
            f"URL        : {pin.get('url', '')}",
            f"Description: {pin.get('description', '')}",
            "",
        ]

    lines += [
        "=" * 60,
        "",
        "## NOTES",
        "- Social Media OS project: add to Experience section as a separate entry",
        "  Title: 'Agentic AI Engineer (Independent)' | 2025 – Present",
        "- Turn on 'Open to Work' for: Agentic AI Engineer, AI Engineer, LLM Engineer",
        "- Request recommendations from anyone who saw your technical work",
    ]

    return "\n".join(lines)


def _print_done(label: str, detail: str) -> None:
    print(f"  [done] {label}: {detail}")
