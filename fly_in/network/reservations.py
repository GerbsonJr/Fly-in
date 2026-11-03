"""Reservation table of zone and link usage over time."""

from __future__ import annotations

from fly_in.core.plan import Route


class Reservations:
    """Counts, for every turn, how busy zones and connections are.

    Occupancy of a zone at turn ``t`` is the number of drones inside it
    right after turn ``t``; drones leaving a zone during turn ``t`` do not
    count, which frees capacity for drones entering during the same turn.
    A drone using a connection (also in flight) counts on that connection
    for every turn of its movement, whatever the direction.

    Zones without a limit (start and end hubs) are never stored.
    """

    def __init__(self) -> None:
        """Create an empty table (one list of counters per zone / link)."""
        self._zone_use: dict[str, list[int]] = {}
        self._link_use: dict[tuple[str, str], list[int]] = {}

    def zone_has_room(self, name: str, capacity: int, turn: int) -> bool:
        """Return True if one more drone fits in the zone at ``turn``."""
        row = self._zone_use.get(name)
        return row is None or turn >= len(row) or row[turn] < capacity

    def link_has_room(
        self, key: tuple[str, str], capacity: int, turn: int
    ) -> bool:
        """Return True if one more drone can use the link at ``turn``."""
        row = self._link_use.get(key)
        return row is None or turn >= len(row) or row[turn] < capacity

    def reserve(self, route: Route) -> None:
        """Add the usage of a route to the table."""
        self._apply(route, 1)

    def release(self, route: Route) -> None:
        """Remove the usage of a route from the table."""
        self._apply(route, -1)

    def _apply(self, route: Route, delta: int) -> None:
        """Add ``delta`` to every counter used by the route."""
        for name, turn in route.zone_stays:
            zone_row = self._zone_use.setdefault(name, [])
            if turn >= len(zone_row):
                zone_row.extend([0] * (turn + 1 - len(zone_row)))
            zone_row[turn] += delta
        for key, turn in route.link_uses:
            link_row = self._link_use.setdefault(key, [])
            if turn >= len(link_row):
                link_row.extend([0] * (turn + 1 - len(link_row)))
            link_row[turn] += delta
