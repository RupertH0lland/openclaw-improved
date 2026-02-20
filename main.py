"""AI Orchestrator - CLI entry point. All config via command line."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cli import main

if __name__ == "__main__":
    main()
