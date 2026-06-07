# Social Media OS

An agentic content pipeline that turns a topic into platform-ready posts — LinkedIn carousels, Instagram captions, and infographic images — with a human approval step via Telegram before publishing.

## Architecture

```
Topic Input
    ↓
ContextEngine          — assembles brand voice + curriculum position + analytics
    ↓
StrategistAgent        — decides angle, hook, and framing (LLM)
    ↓
InformationArchitectAgent  — extracts ContentGraph from contract (LLM)
    ↓
LayoutAgent            — selects template, fills card data (LLM + rule-based)
    ↓
InfographicAgent       — renders image via Playwright + Jinja2
    ↓
Platform Adapters      — generate LinkedIn / Instagram post text (LLM)
    ↓
ReviewAgent            — quality gate (LLM)
    ↓
Telegram Approval      — human approve / reject / redraft
    ↓
Publishers             — post to LinkedIn API / Instagram API
```

## Layer Separation

| Layer | Path | Responsibility |
|-------|------|----------------|
| Agents | `agents/` | LLM decision-makers (strategist, architect, layout, review) |
| Services | `services/` | Storage, retrieval, transformation (knowledge, analytics, style, context) |
| Renderers | `renderers/` | Image and HTML output (block renderer, infographic, SVG layout) |
| Orchestrator | `orchestrator/` | Workflow coordination |
| Publishers | `publishers/` | Platform API clients |

## Key Design Decisions

**ContextEngine** — all context (brand voice, curriculum position, analytics) is assembled once before the first LLM call. No scattered prompt mutation across the pipeline.

**StrategistAgent** — replaces a generic planner. Reasons about *how* to communicate a topic given what analytics says is working, where the topic sits in the curriculum, and the brand voice. Outputs `angle`, `hook`, and `framing` alongside the standard contract fields.

**Knowledge Graph** — a 50-node curriculum graph (`knowledge/knowledge_graph.json`) tracks what has been posted, prerequisites, and business importance. The system picks the next highest-priority unposted node automatically.

**ContentGraph** — the central data structure. One graph representation drives the infographic (via template selection), the post text (via adapters), and the carousel (via VisualBlockGenerator). Same intelligence, multiple output formats.

**VisualBlock Carousel** — `ContentGraph → Carousel(VisualBlock[])` via a rule-based generator (no LLM). Each block type (`what`, `flow`, `takeaway`) maps to a template. Rendered as a PNG album and sent as a Telegram photo album for approval.

## Templates

| Template | Use Case |
|----------|----------|
| `concept_card` | What something IS — single-concept explanation |
| `architecture_card_v2` | System diagrams — SVG nodes + bezier edges |
| `lifecycle_card` | Sequential workflows — phases as columns |
| `cheat_sheet_v2` | Reference grids — multi-card CSS grid layout |
| `comparison_card` | A vs B with tradeoff dimensions |
| `block_what / block_flow / block_takeaway` | Carousel slide types |

## Visual Styles

| Style | Description |
|-------|-------------|
| `linear_dark` | Navy + sky-blue + Inter (baseline) |
| `technical_blueprint` | Near-black + cyan + JetBrains Mono + grid background |
| `modern_saas` | Zinc + violet + 20px radius |
| `apple_minimal` | Pure black + iOS blue + system fonts |
| `light_minimal` | White + LinkedIn blue — optimised for carousel readability |

## Stack

- **Python 3.11+**
- **Groq** (llama-3.3-70b-versatile) — all LLM calls
- **Playwright** — headless browser rendering of Jinja2 HTML → PNG
- **Jinja2** — template engine for infographic HTML
- **Telegram Bot API** — human-in-the-loop approval
- **LinkedIn API + Instagram Graph API** — publishing
- **SQLite** — post records, analytics storage

## Usage

```bash
# Pick next topic from knowledge graph automatically
python run.py

# Specific topic
python run.py "What is ReAct" --style technical_blueprint

# Multiple platforms
python run.py "MCP Architecture" --platforms linkedin instagram --style linear_dark

# Run analytics on a platform snapshot
python run_analyst.py --snapshot data/snapshots/june_2026.json --platform linkedin

# Render carousel without Telegram
python test_carousel.py "RAG Pipeline" --style modern_saas
```

## Setup

```bash
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Fill in: GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
#          LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN
```
