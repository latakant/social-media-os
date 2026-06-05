from dataclasses import dataclass, field


@dataclass
class ContentContract:
    """Master content contract — single source of truth for all platform outputs."""
    topic: str                          # "What is ReAct" / "MCP Server Design" / "LangGraph vs LangChain"
    content_type: str                   # concept | architecture | build_update | lesson | comparison
    core_insight: str                   # One sentence — the main idea
    key_points: list[str]               # 3-6 bullet points
    call_to_action: str                 # closing question or action
    supporting_details: dict = field(default_factory=dict)  # template-specific extra data
    # Orchestrator-level fields
    audience: str = "developers"
    objective: str = "thought_leadership"
    platforms: list[str] = field(default_factory=list)
    knowledge_context: list = field(default_factory=list)
