"""Network of zones and connections (implemented without graph libraries)."""

from __future__ import annotations

import heapq
from typing import Optional

from fly_in.core.links import Connection, make_link_key
from fly_in.core.zones import Zone


class NetworkError(ValueError):
    """Raised when the network is built in an inconsistent way."""


class Network:
    """Network of zones linked by bidirectional connections."""

    def __init__(self) -> None:
        """Create an empty graph."""
        self._zones: dict[str, Zone] = {}
        self._connections: dict[tuple[str, str], Connection] = {}
        self._adjacency: dict[str, list[tuple[Zone, Connection]]] = {}
        self._start: Optional[Zone] = None
        self._end: Optional[Zone] = None

    # ------------------------------------------------------------ building
    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph.

        Raises:
            NetworkError: On duplicated names or duplicated start/end hubs.
        """
        if zone.name in self._zones:
            raise NetworkError(f"duplicate zone name '{zone.name}'")
        if zone.is_start:
            if self._start is not None:
                raise NetworkError("more than one start_hub defined")
            self._start = zone
        if zone.is_end:
            if self._end is not None:
                raise NetworkError("more than one end_hub defined")
            self._end = zone
        self._zones[zone.name] = zone
        self._adjacency[zone.name] = []

    def add_connection(self, connection: Connection) -> None:
        """Add a bidirectional connection between two known zones.

        Raises:
            NetworkError: On unknown zones, self loops or duplicates.
        """
        for name in (connection.zone_a, connection.zone_b):
            if name not in self._zones:
                raise NetworkError(f"connection uses undefined zone '{name}'")
        if connection.zone_a == connection.zone_b:
            raise NetworkError(
                f"connection '{connection.name}' links a zone to itself"
            )
        if connection.key in self._connections:
            raise NetworkError(f"duplicate connection '{connection.name}'")
        self._connections[connection.key] = connection
        zone_a = self._zones[connection.zone_a]
        zone_b = self._zones[connection.zone_b]
        self._adjacency[zone_a.name].append((zone_b, connection))
        self._adjacency[zone_b.name].append((zone_a, connection))

    # ------------------------------------------------------------- queries
    @property
    def zones(self) -> list[Zone]:
        """Return all zones in definition order."""
        return list(self._zones.values())

    @property
    def connections(self) -> list[Connection]:
        """Return all connections in definition order."""
        return list(self._connections.values())

    @property
    def start(self) -> Zone:
        """Return the start hub.

        Raises:
            NetworkError: If there is no start hub.
        """
        if self._start is None:
            raise NetworkError("missing start_hub")
        return self._start

    @property
    def end(self) -> Zone:
        """Return the end hub.

        Raises:
            NetworkError: If there is no end hub.
        """
        if self._end is None:
            raise NetworkError("missing end_hub")
        return self._end

    def zone(self, name: str) -> Zone:
        """Return a zone by name (KeyError if unknown)."""
        return self._zones[name]

    def has_zone(self, name: str) -> bool:
        """Return True if a zone with this name exists."""
        return name in self._zones

    def find_connection(
        self, name_a: str, name_b: str
    ) -> Optional[Connection]:
        """Return the connection between two zones, if there is one."""
        return self._connections.get(make_link_key(name_a, name_b))

    def neighbors(self, name: str) -> list[tuple[Zone, Connection]]:
        """Return the zones a drone can enter from ``name`` (no blocked)."""
        return [
            (zone, conn)
            for zone, conn in self._adjacency[name]
            if zone.zone_type.is_enterable
        ]

    def distances_to_end(self) -> dict[str, int]:
        """Return the minimum movement cost from each zone to the end.

        Capacities are ignored, blocked zones are never crossed. Zones
        that cannot reach the end are absent from the result. Runs a
        Dijkstra search from the end hub in O((V + E) log V).
        """
        end = self.end
        dist: dict[str, int] = {end.name: 0}
        heap: list[tuple[int, str]] = [(0, end.name)]
        while heap:
            cost, name = heapq.heappop(heap)
            if cost > dist.get(name, cost):
                continue
            step = self._zones[name].zone_type.move_cost
            for zone, _ in self._adjacency[name]:
                if not zone.zone_type.is_enterable:
                    continue
                candidate = cost + step
                if candidate < dist.get(zone.name, candidate + 1):
                    dist[zone.name] = candidate
                    heapq.heappush(heap, (candidate, zone.name))
        return dist
