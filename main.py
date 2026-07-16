"""Ponto de entrada do wslView."""
from __future__ import annotations

import sys


def _check_platform() -> None:
    if not sys.platform.startswith("win"):
        print("wslView é compatível apenas com Windows.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    _check_platform()
    from gui import WslViewApp

    app = WslViewApp()
    app.mainloop()


if __name__ == "__main__":
    main()
