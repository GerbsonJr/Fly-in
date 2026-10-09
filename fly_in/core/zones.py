"""Zone model: zone types and zones."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from fly_in.core.settings import UNLIMITED


class ZoneType(Enum):
    """Kind of zone, which defines the cost of moving into it."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def move_cost(self) -> int:
        """Return the number of turns needed to move into this zone."""
        if self is ZoneType.RESTRICTED:
            return 2
        return 1

    @property
    def is_enterable(self) -> bool:
        """Return False for blocked zones, True otherwise."""
        return self is not ZoneType.BLOCKED

    @classmethod
    def from_string(cls, value: str) -> ZoneType:
        """Convert text to a ZoneType.

        Args:
            value: One of normal, blocked, restricted, priority.

        Raises:
            ValueError: If the text is not a valid zone type.
        """
        try:
            return cls(value)
        except ValueError:
            valid = ", ".join(member.value for member in cls)
            raise ValueError(
                f"invalid zone type '{value}' (expected one of: {valid})"
            ) from None


@dataclass(frozen=True)
class Zone:
    """A node of the network.

    Attributes:
        name: Unique zone name (no dashes or spaces).
        x: Integer x coordinate.
        y: Integer y coordinate.
        zone_type: Type of the zone.
        color: Optional color name used for display.
        max_drones: Maximum simultaneous drones (ignored on start/end).
        is_start: True for the start hub.
        is_end: True for the end hub.
    """

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: Optional[str] = None
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False

    @property
    def capacity(self) -> int:
        """Return how many drones can occupy the zone at the same time."""
        if self.is_start or self.is_end:
            return UNLIMITED
        return self.max_drones
