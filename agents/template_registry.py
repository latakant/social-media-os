import json
from pathlib import Path


TEMPLATES_DIR = Path("templates")

AVAILABLE = [
    "build_card",
    "concept_card",
    "architecture_card",
    "lesson_card",
    "comparison_card",
    "lifecycle_card",
    "cheat_sheet_card",
    "architecture_card_v2",
    "cheat_sheet_v2",
]


def load_schema(content_type: str) -> dict:
    path = TEMPLATES_DIR / content_type / "schema.json"
    if not path.exists():
        raise ValueError(f"No schema found for template: {content_type}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_template_path(content_type: str) -> Path:
    path = TEMPLATES_DIR / content_type / "template.html"
    if not path.exists():
        raise ValueError(f"No template found for: {content_type}")
    return path


def schema_as_prompt(content_type: str) -> str:
    """Returns schema fields as a prompt-friendly description."""
    schema = load_schema(content_type)
    lines = [f'Template: "{content_type}"', f'Description: {schema["description"]}', "", "Required fields:"]
    for field, spec in schema["fields"].items():
        t = spec["type"]
        desc = spec["description"]
        if t == "array":
            mn = spec.get("min", 1)
            mx = spec.get("max", 10)
            lines.append(f'  "{field}": array of {mn}-{mx} items — {desc}')
        else:
            lines.append(f'  "{field}": {t} — {desc}')
    return "\n".join(lines)
