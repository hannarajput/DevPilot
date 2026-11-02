"""DevPilot Entry Point — One-Click Development Workspace Manager."""

import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from devpilot.ui.app import DevPilotApp
from devpilot.utils.logger import logger


def main():
    try:
        app = DevPilotApp()
        app.mainloop()
    except Exception as e:
        logger.error(f"Fatal DevPilot runtime error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
