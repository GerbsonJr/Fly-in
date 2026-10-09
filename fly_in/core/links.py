"""Connection model: bidirectional links between zones."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    """A bidirectional edge between two zones.

    Attributes:
        zone_a: Name of the first zone (as written in the map file).
        zone_b: Name of the second zone.
        max_link_capacity: Maximum drones traversing it simultaneously.
    """

    zone_a: str
    zone_b: str
    max_link_capacity: int = 1

    @property
    def name(self) -> str:
        """Return the connection name as written in the map file."""
        return f"{self.zone_a}-{self.zone_b}"

    @property
    def key(self) -> tuple[str, str]:
        """Return an order independent identifier of the connection."""
        return make_link_key(self.zone_a, self.zone_b)

    def other(self, zone_name: str) -> str:
        """Return the zone at the other end of the connection."""
        return self.zone_b if zone_name == self.zone_a else self.zone_a


def make_link_key(name_a: str, name_b: str) -> tuple[str, str]:
    """Build an order independent key for a pair of zone names."""
    if name_a <= name_b:
        return (name_a, name_b)
    return (name_b, name_a)
