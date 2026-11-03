"""Translation of the color names of a map into display colors."""

from __future__ import annotations

import colorsys
import hashlib
from typing import Optional

from fly_in.core.settings import ANSI_CODES, RGB_COLORS

Color = tuple[int, int, int]


class Palette:
    """Gives a color to any color word written in a map file.

    The subject accepts any single word as a color, so there is no fixed
    list. Known names use a fixed color; any other word gets a stable
    color computed from the word itself, so it is always visible and
    always the same.
    """

    def rgb(self, name: Optional[str], default: Color) -> Color:
        """Return the RGB color of a name (``default`` when no color)."""
        if name is None:
            return default
        key = name.lower()
        known = RGB_COLORS.get(key)
        if known is not None:
            return known
        return self._hashed(key)

    def ansi(self, name: Optional[str]) -> Optional[str]:
        """Return the SGR parameters of a name, or None without color."""
        if name is None:
            return None
        code = ANSI_CODES.get(name.lower())
        if code is not None:
            return code
        red, green, blue = self.rgb(name, (255, 255, 255))
        return f"38;2;{red};{green};{blue}"

    @staticmethod
    def _hashed(key: str) -> Color:
        """Build a bright color from the hash of an unknown word."""
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        red, green, blue = colorsys.hsv_to_rgb(digest[0] / 255, 0.65, 0.95)
        return (int(red * 255), int(green * 255), int(blue * 255))
