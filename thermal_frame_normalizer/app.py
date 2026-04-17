from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from thermal_frame_normalizer.ui import launch_app
else:
    from .ui import launch_app


def main() -> None:
    launch_app()


if __name__ == "__main__":
    main()
