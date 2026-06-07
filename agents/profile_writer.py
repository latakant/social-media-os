"""ProfileWriterAgent — generates optimized LinkedIn profile sections.

Takes resume text + brand voice + target JD and produces each section
of the LinkedIn profile tuned for the role. One LLM call per section
so each prompt stays focused and the output stays within LinkedIn limits.

LinkedIn character limits enforced:
  Headline  : 220 chars
  About     : 2600 chars
  Experience: 2000 chars per role
"""

import json
from groq import Groq


_SYSTEM = """You are a LinkedIn profile writer specializing in AI engineering roles.

You write crisp, specific, technically credible profile copy. No buzzwords,
no hustle-culture language, no vague claims. Every sentence either signals
technical depth or shows proof of work.

Return only valid JSON. No markdown outside JSON."""


# ── Headline ────────────────────────────────────────────────────────────────

_HEADLINE_PROMPT = """Write a LinkedIn headline for this engineer.

RESUME SUMMARY:
{resume_summary}

TARGET ROLE:
{target_role}

BRAND VOICE:
{brand_voice}

Rules:
- Max 220 characters
- Lead with what they BUILD, not their job title
- Include 2-3 specific technical signals (e.g. "Multi-Agent Systems", "LLM Orchestration")
- No generic phrases: "passionate about", "results-driven", "seeking opportunities"
- Format: [What you build] | [Technical signals] | [Current context]

Return JSON: {{"headline": "..."}}"""


# ── About ────────────────────────────────────────────────────────────────────

_ABOUT_PROMPT = """Write a LinkedIn About section for this engineer.

FULL RESUME:
{resume}

TARGET ROLE:
{target_role}

BRAND VOICE:
{brand_voice}

Structure (follow this order):
1. Hook (1 sentence) — the single most specific thing about what they build. Not "I am a developer". Something like "I build multi-agent systems that..."
2. What they do technically (2-3 sentences) — specific systems, architectures, decisions
3. Flagship project proof (2-3 sentences) — social-media-os: what it does, how it's architected, what's interesting about it
4. Background + trajectory (1-2 sentences) — where they came from, where they're headed
5. What they're looking for (1 sentence) — specific, not generic

Rules:
- Max 2600 characters
- Write in first person
- No bullet points — this is flowing prose
- No emojis
- No hashtags
- Technical terms are fine and expected — this is an AI engineering audience
- Never start with "I am" or "I'm a"

Return JSON: {{"about": "..."}}"""


# ── Experience ───────────────────────────────────────────────────────────────

_EXPERIENCE_PROMPT = """Rewrite the experience bullets for this role on LinkedIn.

ROLE: {role_title} at {company}
DATES: {dates}

CURRENT BULLETS:
{current_bullets}

TARGET ROLE THIS PROFILE IS OPTIMIZED FOR:
{target_role}

Rules:
- 3-4 bullets maximum
- Each bullet: starts with a strong verb, names specific technology or outcome
- No vague language: "contributed to", "worked on", "helped with"
- If the role used Salesforce — say Salesforce specifically, not "enterprise platform"
- Keep it honest — do not invent outcomes
- Each bullet under 200 characters

Return JSON: {{"bullets": ["...", "...", "..."]}}"""


# ── Skills ───────────────────────────────────────────────────────────────────

_SKILLS_PROMPT = """Order and select the top LinkedIn skills for this engineer's profile.

SKILLS FROM RESUME:
{all_skills}

TARGET ROLE REQUIREMENTS:
{target_role}

Rules:
- Select exactly 15 skills total
- Order by relevance to the target role (most relevant first)
- First 3 are "top skills" pinned on LinkedIn — make them the strongest signal
- Use LinkedIn's standard skill names where possible (e.g. "LangChain" not "langchain-community")
- No soft skills (no "teamwork", "communication")

Return JSON:
{{
  "top_3": ["skill1", "skill2", "skill3"],
  "remaining_12": ["skill4", ..., "skill15"]
}}"""


# ── Featured ─────────────────────────────────────────────────────────────────

_FEATURED_PROMPT = """Write the Featured section strategy for this LinkedIn profile.

PROJECTS:
{projects}

TARGET ROLE:
{target_role}

The Featured section can pin: GitHub repos, LinkedIn posts, articles, links.

Return JSON:
{{
  "pins": [
    {{
      "type": "github | post | link",
      "title": "...",
      "description": "One sentence — what this shows to a recruiter or hiring manager",
      "url": "..."
    }}
  ],
  "rationale": "One sentence on why this ordering signals the right things for this role"
}}"""


class ProfileWriterAgent:

    def __init__(self) -> None:
        self._client = Groq()

    def generate_headline(self, resume_summary: str, target_role: str, brand_voice: str) -> str:
        raw = self._call(_HEADLINE_PROMPT.format(
            resume_summary=resume_summary,
            target_role=target_role,
            brand_voice=brand_voice,
        ))
        return raw["headline"]

    def generate_about(self, resume: str, target_role: str, brand_voice: str) -> str:
        raw = self._call(_ABOUT_PROMPT.format(
            resume=resume,
            target_role=target_role,
            brand_voice=brand_voice,
        ))
        return raw["about"]

    def generate_experience(
        self,
        role_title: str,
        company: str,
        dates: str,
        current_bullets: list[str],
        target_role: str,
    ) -> list[str]:
        raw = self._call(_EXPERIENCE_PROMPT.format(
            role_title=role_title,
            company=company,
            dates=dates,
            current_bullets="\n".join(f"- {b}" for b in current_bullets),
            target_role=target_role,
        ))
        return raw["bullets"]

    def generate_skills(self, all_skills: list[str], target_role: str) -> dict:
        raw = self._call(_SKILLS_PROMPT.format(
            all_skills=", ".join(all_skills),
            target_role=target_role,
        ))
        return raw

    def generate_featured(self, projects: list[dict], target_role: str) -> dict:
        raw = self._call(_FEATURED_PROMPT.format(
            projects=json.dumps(projects, indent=2),
            target_role=target_role,
        ))
        return raw

    def _call(self, prompt: str) -> dict:
        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return json.loads(response.choices[0].message.content)
