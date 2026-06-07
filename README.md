# Social Media OS

An agentic content pipeline that converts a topic into platform-ready LinkedIn posts and Instagram captions — with rendered infographic images and a human approval gate — using a layered multi-agent architecture built entirely in Python.

---

## The Problem

Creating consistent, high-quality technical content for LinkedIn and Instagram requires the same work every time:

1. Decide **what** to post next (from a curriculum of topics)
2. Decide **how** to frame it (angle, hook, tone) given what's working analytically
3. Extract the **information structure** (what goes in the visual vs. the post)
4. **Design and render** a visual (infographic or carousel)
5. Write the **post copy** for each platform separately
6. **Review** quality before publishing
7. Get **human approval** before it goes live
8. **Publish** via API

Doing this manually takes 2–3 hours per post. Doing it with generic AI tools produces generic output because each step has no context about brand voice, curriculum position, or past performance.

**This system automates the full pipeline with structured intelligence at every step.**

---

## How It Works — End to End

```
User Input (topic or auto-pick from knowledge graph)
        │
        ▼
  ContextEngine                    ← assembles brand voice + KG position + analytics
        │
        ▼
  StrategistAgent      [LLM]       ← decides angle, hook, framing
        │
        ▼
  ContentContract                  ← structured JSON: topic, type, insight, key points, hook
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
  InformationArchitectAgent [LLM]   Platform Adapters [LLM]
  → ContentGraph                    → LinkedIn post text
        │                           → Instagram caption
        ▼
  LayoutAgent [LLM + rule-based]
  → (template_name, card_data)
        │
        ▼
  InfographicAgent / BlockRenderer
  → PNG image (via Playwright)
        │
        ▼
  ReviewAgent [LLM]                ← quality gate
        │
        ▼
  Telegram Approval Bot            ← human: approve / reject / redraft
        │
        ▼
  Publishers                       ← LinkedIn API / Instagram Graph API
        │
        ▼
  KnowledgeService.mark_posted()   ← updates curriculum graph state
```

---

## Architecture — Layer Separation

The codebase is divided into five distinct layers. Each layer has one responsibility and does not reach into another layer's concerns.

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **Agents** | `agents/` | LLM-based decision making — reasoning, extraction, generation |
| **Services** | `services/` | State, retrieval, and transformation — no side effects on external systems |
| **Renderers** | `renderers/` | Convert structured data into visual output (PNG, HTML) |
| **Orchestrator** | `orchestrator/` | Coordinate the workflow — calls agents and services in sequence |
| **Publishers** | `publishers/` | External API clients — LinkedIn, Instagram |

**Rule enforced throughout:** An agent makes decisions. A service stores or retrieves. A renderer produces output. Nothing crosses these boundaries.

---

## File Structure — Annotated

```
social-intel/
│
├── run.py                          # CLI entry point
├── run_analyst.py                  # Run AnalyticsService on a platform snapshot
├── test_carousel.py                # Test VisualBlock carousel pipeline (no Telegram)
├── test_carousel_telegram.py       # Test carousel pipeline with Telegram approval
├── render_rag_carousel.py          # Render a hardcoded 3-slide carousel
│
├── orchestrator/
│   └── __init__.py                 # Orchestrator class — full pipeline coordination
│
├── agents/
│   ├── strategist.py               # StrategistAgent — angle, hook, framing (LLM)
│   ├── information_architect.py    # InformationArchitectAgent — ContentGraph extraction (LLM)
│   ├── layout_agent.py             # LayoutAgent — template selection + card filling (LLM)
│   ├── infographic.py              # InfographicAgent — renders HTML → PNG via Playwright
│   ├── visual_block_generator.py   # VisualBlockGenerator — ContentGraph → Carousel (rule-based)
│   ├── review.py                   # ReviewAgent — post quality gate (LLM)
│   ├── planner.py                  # PlannerAgent — legacy, replaced by StrategistAgent
│   ├── post_writer.py              # PostWriterAgent — legacy LinkedIn writer
│   ├── content.py                  # ContentAgent — legacy sprint agent
│   ├── content_generator.py        # ContentGeneratorAgent — legacy template-based generator
│   ├── image.py                    # ImageAgent — FLUX image prompt generation
│   ├── protocols.py                # PlatformAgent protocol definition (typing)
│   └── adapters/
│       ├── linkedin_adapter.py     # Generates LinkedIn post text from contract (LLM)
│       └── instagram_adapter.py    # Generates Instagram caption from contract (LLM)
│
├── services/
│   ├── context_engine.py           # ContextEngine — assembles ContentContext before LLM calls
│   ├── knowledge_service.py        # KnowledgeService — curriculum graph read/write
│   ├── analytics_service.py        # AnalyticsService — snapshot → ObservationReport (LLM)
│   ├── style_service.py            # StyleService — CSS preset loader
│   ├── template_registry.py        # TemplateRegistry — schema loader for LayoutAgent
│   └── memory_service.py           # MemoryService — SQLite read/write wrapper
│
├── renderers/
│   ├── block_renderer.py           # BlockRenderer — VisualBlock + style → PNG
│   ├── infographic_renderer.py     # InfographicRenderer — template pipeline (HTML → PNG)
│   └── svg_layout.py               # SvgLayout — node position engine for architecture_card_v2
│
├── schemas/
│   ├── content_contract.py         # ContentContract dataclass (topic, type, insight, hook…)
│   ├── visual_block.py             # VisualBlock + Carousel dataclasses (9 block types)
│   ├── platform.py                 # PlatformSnapshot — metrics input schema
│   ├── reports.py                  # ObservationReport + Finding — analytics output schema
│   ├── engagement.py               # Engagement metrics schema
│   └── instagram.py                # InstagramSnapshot schema
│
├── publishers/
│   ├── base.py                     # Publisher protocol + PublishResult + PublishError
│   ├── linkedin.py                 # LinkedInPublisher — posts via LinkedIn API
│   └── instagram.py                # InstagramPublisher — posts via Instagram Graph API
│
├── bots/
│   └── telegram_approval.py        # ApprovalBot — sends content to Telegram, handles responses
│
├── memory/
│   └── store.py                    # SQLite helpers — save/read post records and analytics
│
├── normalizers/
│   └── instagram.py                # Converts raw Instagram export JSON → PlatformSnapshot
│
├── knowledge/
│   ├── knowledge_graph.json        # 50-node curriculum graph (topics, layers, prerequisites)
│   └── brand_voice.md              # Brand voice guidelines injected into every prompt
│
├── templates/                      # Jinja2 HTML templates — one directory per card type
│   ├── _base.css                   # Shared CSS variables and base styles
│   ├── design-system/
│   │   ├── tokens.css              # Design tokens (colors, spacing, typography)
│   │   └── icons.html              # SVG icon library
│   ├── concept_card/               # What-something-IS layout
│   │   ├── template.html
│   │   └── schema.json             # Field definitions consumed by LayoutAgent
│   ├── architecture_card_v2/       # SVG-first system diagram (nodes + bezier edges)
│   ├── lifecycle_card/             # Sequential workflow — phases as columns
│   ├── cheat_sheet_v2/             # Multi-card CSS grid for reference content
│   ├── comparison_card/            # A vs B with dimensions
│   ├── build_card/                 # Build update layout
│   ├── lesson_card/                # Insight / lesson layout
│   ├── block_what/                 # Carousel slide — concept definition
│   ├── block_flow/                 # Carousel slide — process steps
│   └── block_takeaway/             # Carousel slide — key insight
│
├── styles/                         # Visual style presets (JSON CSS variable overrides)
│   ├── linear_dark.json            # Navy + sky-blue + Inter (default)
│   ├── technical_blueprint.json    # Near-black + cyan + JetBrains Mono + grid background
│   ├── modern_saas.json            # Zinc + violet + 20px radius
│   ├── apple_minimal.json          # Pure black + iOS blue + system fonts
│   └── light_minimal.json          # White + LinkedIn blue — carousel-optimised
│
└── pyproject.toml                  # Project metadata and dependencies
```

---

## Technology Stack — Where and Why

### Groq — `llama-3.3-70b-versatile`
**Where:** Every LLM call in the pipeline — StrategistAgent, InformationArchitectAgent, LayoutAgent, ReviewAgent, AnalyticsService, LinkedInAdapter, InstagramAdapter.

**Why:** Groq's inference speed (700+ tokens/sec on Llama 3.3 70B) means the full pipeline — 5–7 LLM calls — completes in under 30 seconds. All calls use `response_format: {"type": "json_object"}` for structured, schema-validated outputs. No streaming needed; deterministic JSON is the contract.

---

### Playwright (headless Chromium)
**Where:** `renderers/block_renderer.py`, `agents/infographic.py`

**Why:** Infographic images are authored as Jinja2 HTML + CSS, then rendered to PNG by a headless Chromium browser. This gives full CSS layout control (Grid, Flexbox, custom fonts, SVG) that no canvas or PIL-based approach can match. Playwright handles the HTML → screenshot → PNG pipeline with exact pixel dimensions per platform (1080×1080 LinkedIn square, 1080×1350 portrait, etc.).

---

### Jinja2
**Where:** `templates/*/template.html`, used in `renderers/infographic_renderer.py` and `renderers/block_renderer.py`

**Why:** Each card type is a Jinja2 HTML template that receives structured `card_data` from LayoutAgent. Templates handle display logic (loops, conditionals, truncation) while agents handle intelligence. This separation means templates can be redesigned without touching any Python.

---

### Python — asyncio + ThreadPoolExecutor
**Where:** `orchestrator/__init__.py` — parallel platform content generation

**Why:** LinkedIn and Instagram post generation are independent LLM calls. They run in parallel via `ThreadPoolExecutor` inside an `asyncio` event loop, cutting multi-platform generation time in half. The Playwright render also runs in a thread pool since Playwright's sync API blocks the event loop.

---

### Telegram Bot API — `python-telegram-bot`
**Where:** `bots/telegram_approval.py`

**Why:** Human-in-the-loop approval before publishing. The bot sends the rendered image + draft post text as a Telegram message with inline keyboard buttons (Approve / Reject / Redraft). On Redraft, the user can type feedback which gets injected back into the adapter prompt for the next iteration. Up to 4 redraft cycles before the pipeline skips the platform.

---

### LinkedIn API + Instagram Graph API — `requests`
**Where:** `publishers/linkedin.py`, `publishers/instagram.py`

**Why:** Direct REST API calls for publishing. LinkedIn uses the UGC Posts API (`/v2/ugcPosts`) with image upload. Instagram uses the Graph API two-step flow (media container creation → publish). Both publishers implement the `Publisher` protocol from `publishers/base.py`.

---

### SQLite
**Where:** `memory/store.py`, `memory/social_intel.db`

**Why:** Lightweight persistence for post records and analytics findings. No ORM — raw SQL via Python's `sqlite3`. Two tables: `post_record` (tracks what was published, platform post IDs, Telegram message IDs) and `analysis_report` (stores `ObservationReport` JSON from AnalyticsService). `KnowledgeService` uses the flat JSON knowledge graph separately.

---

### Knowledge Graph — `knowledge/knowledge_graph.json`
**Where:** `services/knowledge_service.py`

**Why:** A hand-authored curriculum of 50 nodes organized into layers (Foundation → Patterns → Systems → Architecture → Product). Each node has: topic, core insight, prerequisites, unlocks, business importance score, preferred templates, and posting state. `KnowledgeService.pick_next()` selects the highest-priority unposted node whose prerequisites are already posted — so the content curriculum has logical progression instead of random topic selection.

---

### CSS Design System — `templates/design-system/`
**Where:** `templates/_base.css`, `templates/design-system/tokens.css`, applied via `StyleService`

**Why:** All visual styles are defined as CSS custom properties (variables). `StyleService` loads a style preset JSON (e.g., `technical_blueprint.json`) and injects it as a `<style>` block that overrides `--color-primary`, `--font-family`, `--bg-color`, etc. This means any template can be rendered in any style with zero template changes — style and content are fully decoupled.

---

## Key Design Decisions

**ContextEngine as the single context assembly point**
All context — brand voice, curriculum position, analytics findings — is assembled into a `ContentContext` object once before any LLM call. Agents receive structured context, not accumulated prompt strings. This eliminates the common pattern of scattered `prompt += "..."` mutations that become undebuggable as the pipeline grows.

**StrategistAgent reasons before writing**
Most content pipelines go: topic → write. This pipeline goes: topic → *decide angle and hook* → write. The StrategistAgent sees brand voice, what's performing well analytically, and where the topic sits in the curriculum, then decides the strategic framing. Every downstream agent inherits this decision. The hook produced by the Strategist travels unchanged into the final post.

**ContentGraph as the central data structure**
One LLM extraction (InformationArchitectAgent) produces a `ContentGraph` — nodes, edges, phases, visual pattern. This single structure drives both the infographic (via LayoutAgent → template) and the carousel (via VisualBlockGenerator → VisualBlocks). Same intelligence, two output formats, no duplication.

**Deterministic vs. probabilistic separation**
Agents that make decisions use LLMs. Agents that transform data use rules. `VisualBlockGenerator` converts a `ContentGraph` into carousel slides with zero LLM calls — it applies deterministic mapping rules (node type → block type). `StyleService` loads a JSON file. `KnowledgeService` runs a scoring function. The LLM budget is spent only where reasoning is actually needed.

---

## Running the Pipeline

```bash
# Install dependencies
pip install groq requests python-telegram-bot python-dotenv jinja2
pip install playwright && playwright install chromium

# Copy and fill environment variables
cp .env.example .env

# Auto-pick next topic from knowledge graph
python run.py

# Specific topic, specific style
python run.py "What is ReAct" --style technical_blueprint

# Multi-platform
python run.py "MCP Architecture" --platforms linkedin instagram --style linear_dark

# Run analytics on a platform snapshot
python run_analyst.py --snapshot data/snapshots/june_2026.json --platform linkedin

# Test carousel rendering without Telegram
python test_carousel.py "RAG Pipeline" --style modern_saas
```

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Yes | All LLM calls |
| `TELEGRAM_BOT_TOKEN` | Yes | Approval bot |
| `TELEGRAM_CHAT_ID` | Yes | Your Telegram chat ID |
| `LINKEDIN_ACCESS_TOKEN` | Yes | Publishing to LinkedIn |
| `LINKEDIN_PERSON_URN` | Yes | Your LinkedIn profile URN |
| `INSTAGRAM_ACCESS_TOKEN` | Optional | Publishing to Instagram |
| `INSTAGRAM_ACCOUNT_ID` | Optional | Your Instagram business account ID |
