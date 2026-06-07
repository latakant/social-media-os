"""Generate an optimized LinkedIn profile document.

Usage:
    python run_profile.py
    python run_profile.py --resume C:/path/to/resume.md
    python run_profile.py --output my_linkedin.md
"""

import argparse
from pathlib import Path
from dotenv import load_dotenv

from workflows.linkedin_profile import LinkedInProfileWorkflow

load_dotenv()

DIV = "=" * 52

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate optimized LinkedIn profile")
    parser.add_argument("--resume", default=None, help="Path to resume .md file")
    parser.add_argument("--output", default="linkedin_profile.md", help="Output file path")
    args = parser.parse_args()

    print(f"\n{DIV}")
    print("LinkedIn Profile Generator")
    print(f"{DIV}\n")

    workflow = LinkedInProfileWorkflow()
    doc = workflow.run(resume_path=args.resume, output_path=args.output)

    print(f"\n{DIV}")
    print(f"Done. Open: {Path(args.output).resolve()}")
    print(f"{DIV}\n")
