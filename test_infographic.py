"""Test architecture card with Option B insight block."""
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from agents.infographic import InfographicAgent

# Reuse existing illustration (skip HF call for speed)
agent = InfographicAgent()

post = """The Social Media Agent: four agents in a pipeline.
Analyst reads Instagram metrics and produces an ObservationReport.
Writer drafts a LinkedIn post filtered through brand_voice.md.
Reviewer checks tone, format, quality — APPROVE or REJECT verdict.
Publisher uploads an AI-generated infographic and posts to LinkedIn live.
The loop: Observe → Generate → Measure → Learn."""

print("Generating architecture card...")
path = agent.generate(post)
print(f"Saved: {path} ({Path(path).stat().st_size // 1024}KB)")
