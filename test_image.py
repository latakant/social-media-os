"""Quick test — generate one image from the last post and open it."""
import os
from dotenv import load_dotenv
load_dotenv()

from agents.image import ImageAgent

post = """I've found that multi-agent systems often fail due to poorly designed orchestration patterns.
In a basic setup, you have one agent per task and they communicate through a central hub — as the system
grows, the hub becomes a bottleneck. To avoid this, I use a hierarchical orchestration pattern:
1. Divide tasks into sub-tasks
2. Assign sub-tasks to agent clusters
3. Use a local hub for each cluster
This reduces communication overhead by 50% as the system scales."""

agent = ImageAgent()
path = agent.generate(post)
print(f"\nImage: {path}")
os.startfile(path)  # opens in default image viewer
