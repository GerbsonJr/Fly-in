"""Listing and choosing the maps shipped with the project."""

from __future__ import annotations

import os
from typing import Callable, Optional

from fly_in.core.settings import MAPS_DIR


class MapCatalog:
    """Finds the map files of a folder and lets the user pick one."""

    RANKS = {"easy": 0, "medium": 1, "hard": 2, "challenger": 3}

    def __init__(self, folder: str = MAPS_DIR) -> None:
        """Remember the folder to scan (``invalid`` maps are skipped)."""
        self._folder = folder

    def find(self) -> list[str]:
        """Return the map files, easiest first, then by name."""
        paths: list[str] = []
        for root, dirs, files in os.walk(self._folder):
            dirs[:] = [name for name in dirs if name != "invalid"]
            paths.extend(
                os.path.join(root, name)
                for name in files if name.endswith(".txt")
            )
        return sorted(paths, key=self._sort_key)

    def choose(self, ask: Callable[[str], str] = input) -> Optional[str]:
        """List the maps and ask for one.

        Args:
            ask: Function that shows a prompt and returns the answer.

        Returns:
            The chosen path, or None if the user quits or no map exists.
        """
        maps = self.find()
        if not maps:
            return None
        print("Available maps:")
        for number, path in enumerate(maps, start=1):
            print(f"  {number:2d}) {os.path.relpath(path, self._folder)}")
        while True:
            try:
                answer = ask("Choose a map (number, q to quit): ").strip()
            except EOFError:
                return None
            if answer.lower() in ("q", "quit"):
                return None
            if answer.isascii() and answer.isdigit():
                if 1 <= int(answer) <= len(maps):
                    return maps[int(answer) - 1]
            print("Invalid choice.")

    def _sort_key(self, path: str) -> tuple[int, str]:
        """Order by difficulty folder, then by path."""
        folder = os.path.basename(os.path.dirname(path))
        return (self.RANKS.get(folder, len(self.RANKS)), path)
