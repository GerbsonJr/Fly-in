"""Project wide constants."""

import os

PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
)))
ASSETS_DIR: str = os.path.join(PROJECT_ROOT, "assets")

UNLIMITED: int = 10 ** 9
"""Capacity used for zones without a limit (start and end hubs)."""

ZONE_PREFIXES: tuple[str, ...] = ("start_hub", "end_hub", "hub")
ALLOWED_HUB_TAGS: tuple[str, ...] = ("zone", "color", "max_drones")
ALLOWED_CONN_TAGS: tuple[str, ...] = ("max_link_capacity",)

ANSI_RESET: str = "\033[0m"

ANSI_CODES: dict[str, str] = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "gray": "90",
    "grey": "90",
    "orange": "38;5;208",
    "purple": "38;5;129",
    "violet": "38;5;135",
    "pink": "38;5;213",
    "brown": "38;5;94",
    "gold": "38;5;220",
    "lime": "38;5;118",
    "maroon": "38;5;88",
    "crimson": "38;5;161",
    "teal": "38;5;30",
    "navy": "38;5;18",
    "darkred": "38;5;88",
    "rainbow": "38;5;201",
}


RGB_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (30, 30, 30),
    "red": (220, 60, 60),
    "green": (60, 170, 80),
    "yellow": (240, 220, 70),
    "blue": (60, 100, 230),
    "magenta": (200, 60, 200),
    "cyan": (60, 200, 210),
    "white": (240, 240, 240),
    "gray": (130, 130, 130),
    "grey": (130, 130, 130),
    "orange": (240, 150, 40),
    "purple": (140, 70, 200),
    "violet": (160, 110, 220),
    "pink": (240, 150, 190),
    "brown": (130, 80, 40),
    "gold": (230, 190, 40),
    "lime": (140, 230, 60),
    "maroon": (128, 30, 50),
    "crimson": (200, 30, 70),
    "teal": (30, 140, 140),
    "navy": (30, 40, 120),
    "darkred": (140, 20, 20),
    "rainbow": (200, 100, 200),
}
"""Colors used by the graphical window (default: a neutral gray-blue)."""
