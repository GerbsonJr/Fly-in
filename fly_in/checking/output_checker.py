"""Independent validator of a simulation output."""

from __future__ import annotations

from collections import Counter
from typing import Optional, Sequence

from fly_in.core.settings import UNLIMITED
from fly_in.network.topology import Network
from fly_in.core.links import Connection
from fly_in.core.zones import ZoneType


class CheckError(Exception):
    """Raised when a simulation output breaks a rule of the subject."""


class OutputChecker:
    """Replays the printed simulation and checks every rule.

    It only reads the output lines (not the planner data structures), so
    it can also be used to check the output of any other program.
    Checks: adjacency, blocked zones, 2-turn restricted moves that cannot
    wait on the connection, zone capacity, link capacity, one movement per
    drone and per turn, and delivery of every drone.
    """

    def __init__(self, graph: Network, nb_drones: int) -> None:
        """Prepare the validator for a map."""
        self._graph = graph
        self._nb_drones = nb_drones

    def validate(self, lines: Sequence[str]) -> None:
        """Check a whole simulation.

        Args:
            lines: One string per turn, e.g. ``"D1-roof1 D2-corridorA"``.

        Raises:
            CheckError: Describing the first broken rule.
        """
        graph = self._graph
        start, end = graph.start.name, graph.end.name
        # None means "in flight"; delivered drones are removed.
        where: dict[int, Optional[str]] = {
            drone: start for drone in range(1, self._nb_drones + 1)
        }
        flights: dict[int, tuple[Connection, str]] = {}
        for turn, line in enumerate(lines, start=1):
            seen: set[int] = set()
            link_use: Counter[tuple[str, str]] = Counter()
            next_flights: dict[int, tuple[Connection, str]] = {}
            for token in line.split():
                drone, target = self._split_token(token, turn)
                if drone in seen:
                    raise CheckError(
                        f"turn {turn}: D{drone} moves twice"
                    )
                seen.add(drone)
                if drone not in where:
                    raise CheckError(
                        f"turn {turn}: D{drone} unknown or already delivered"
                    )
                if drone in flights:
                    conn, dest = flights[drone]
                    if target != dest:
                        raise CheckError(
                            f"turn {turn}: D{drone} is in flight on "
                            f"'{conn.name}' and must arrive at '{dest}'"
                        )
                    link_use[conn.key] += 1
                    where[drone] = dest
                    continue
                current = where[drone]
                if current is None:
                    raise CheckError(f"turn {turn}: D{drone} lost")
                conn, dest, in_flight = self._resolve(
                    current, target, turn, drone
                )
                link_use[conn.key] += 1
                if in_flight:
                    next_flights[drone] = (conn, dest)
                    where[drone] = None
                else:
                    where[drone] = dest
            for drone in flights:
                if drone not in seen:
                    raise CheckError(
                        f"turn {turn}: D{drone} cannot wait on a connection"
                    )
            flights = next_flights
            self._check_capacities(turn, where, link_use)
            for drone in [d for d, z in where.items() if z == end]:
                del where[drone]
        if where or flights:
            missing = sorted(where)
            raise CheckError(
                f"simulation ended with undelivered drones: {missing}"
            )

    # ----------------------------------------------------------- helpers
    @staticmethod
    def _split_token(token: str, turn: int) -> tuple[int, str]:
        """Split ``D<ID>-<target>`` into the id and the target."""
        head, sep, target = token.partition("-")
        if not sep or not target or not head.startswith("D"):
            raise CheckError(
                f"turn {turn}: malformed movement '{token}'"
            )
        if not head[1:].isdigit():
            raise CheckError(
                f"turn {turn}: malformed drone id in '{token}'"
            )
        return int(head[1:]), target

    def _resolve(
        self, current: str, target: str, turn: int, drone: int
    ) -> tuple[Connection, str, bool]:
        """Interpret a movement of a drone that is standing in a zone.

        Returns:
            The used connection, the destination zone and whether the
            drone is now in flight.
        """
        graph = self._graph
        if "-" in target:
            zone_a, _, zone_b = target.partition("-")
            conn = graph.find_connection(zone_a, zone_b)
            if conn is None or current not in (zone_a, zone_b):
                raise CheckError(
                    f"turn {turn}: D{drone} cannot use '{target}' "
                    f"from '{current}'"
                )
            dest = conn.other(current)
            if graph.zone(dest).zone_type is not ZoneType.RESTRICTED:
                raise CheckError(
                    f"turn {turn}: D{drone}: '{target}' leads to a "
                    "zone that is not restricted"
                )
            return conn, dest, True
        if not graph.has_zone(target):
            raise CheckError(f"turn {turn}: unknown zone '{target}'")
        conn_found = graph.find_connection(current, target)
        if conn_found is None:
            raise CheckError(
                f"turn {turn}: D{drone}: '{current}' and '{target}' "
                "are not connected"
            )
        zone = graph.zone(target)
        if zone.zone_type is ZoneType.BLOCKED:
            raise CheckError(
                f"turn {turn}: D{drone} enters blocked zone '{target}'"
            )
        if zone.zone_type is ZoneType.RESTRICTED:
            raise CheckError(
                f"turn {turn}: D{drone}: moving to restricted zone "
                f"'{target}' takes 2 turns; use the connection name"
            )
        return conn_found, target, False

    def _check_capacities(
        self,
        turn: int,
        where: dict[int, Optional[str]],
        link_use: Counter[tuple[str, str]],
    ) -> None:
        """Verify zone and link capacities after a turn."""
        occupancy = Counter(z for z in where.values() if z is not None)
        for name, count in occupancy.items():
            zone = self._graph.zone(name)
            if zone.capacity < UNLIMITED and count > zone.capacity:
                raise CheckError(
                    f"turn {turn}: zone '{name}' holds {count} drones "
                    f"(max {zone.capacity})"
                )
        for key, count in link_use.items():
            conn = self._graph.find_connection(*key)
            if conn is not None and count > conn.max_link_capacity:
                raise CheckError(
                    f"turn {turn}: connection '{conn.name}' used by "
                    f"{count} drones (max {conn.max_link_capacity})"
                )
