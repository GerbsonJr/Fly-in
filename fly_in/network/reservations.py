"""Reservation table of zone and link usage over time."""

from __future__ import annotations

from collections import defaultdict

from fly_in.core.settings import UNLIMITED
from fly_in.core.links import Connection
from fly_in.core.plan import Route
from fly_in.core.zones import Zone


class Reservations:
    """Counts, for every turn, how busy zones and connections are.

    Occupancy of a zone at turn ``t`` is the number of drones inside it
    right after turn ``t``; drones leaving a zone during turn ``t`` do not
    count, which frees capacity for drones entering during the same turn.
    A drone using a connection (also in flight) counts on that connection
    for every turn of its movement, whatever the direction.
    """

    def __init__(self) -> None:
        """Create an empty table."""
        self._zone_use: defaultdict[tuple[str, int], int] = defaultdict(int)
        self._link_use: defaultdict[
            tuple[tuple[str, str], int], int
        ] = defaultdict(int)

    def zone_has_room(self, zone: Zone, turn: int) -> bool:
        """Return True if one more drone fits in ``zone`` at ``turn``."""
        if zone.capacity >= UNLIMITED:
            return True
        return self._zone_use[(zone.name, turn)] < zone.capacity

    def link_has_room(self, connection: Connection, turn: int) -> bool:
        """Return True if one more drone can use the link at ``turn``."""
        used = self._link_use[(connection.key, turn)]
        return used < connection.max_link_capacity

    def reserve(self, route: Route) -> None:
        """Add the usage of a route to the table."""
        for key in route.zone_stays:
            self._zone_use[key] += 1
        for link_key in route.link_uses:
            self._link_use[link_key] += 1

    def release(self, route: Route) -> None:
        """Remove the usage of a route from the table."""
        for key in route.zone_stays:
            self._zone_use[key] -= 1
        for link_key in route.link_uses:
            self._link_use[link_key] -= 1
