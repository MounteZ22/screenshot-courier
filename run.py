"""Run Screenshot Courier. Execute this from the project root."""

import sys
from pathlib import Path

# Add project root to sys.path so `src` package is importable
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main

if __name__ == "__main__":
    main()
