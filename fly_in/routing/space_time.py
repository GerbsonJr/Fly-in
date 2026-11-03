"""Space-time pathfinding for a single drone."""

from __future__ import annotations

import heapq
import random
from typing import Optional

from fly_in.core.plan import Move, Route
from fly_in.core.settings import UNLIMITED
from fly_in.core.zones import ZoneType
from fly_in.network.reservations import Reservations
from fly_in.network.topology import Network

StateKey = tuple[str, int]


class SchedulingError(Exception):
    """Raised when no valid schedule can be produced."""


class SpaceTimePlanner:
    """Finds the earliest arrival path of one drone given reservations.

    The search runs on the time-expanded graph whose states are
    ``(zone, turn)``. Waiting, moving to a zone (1 turn) and moving to a
    restricted zone (2 turns, link busy during both) are the transitions.
    A* is used with the capacity-free distance to the end as an admissible
    and consistent heuristic. Among routes with the same arrival turn it
    prefers priority zones, then fewer waits outside the start hub.
    """

    NON_PRIORITY_WEIGHT = 1.0
    WAIT_WEIGHT = 0.25

    def __init__(self, graph: Network, horizon: int) -> None:
        """Prepare the planner.

        Args:
            graph: The network.
            horizon: Last turn the search is allowed to reach.

        Raises:
            SchedulingError: If the end cannot be reached from the start.
        """
        self._graph = graph
        self._horizon = horizon
        self._dist = graph.distances_to_end()
        if graph.start.name not in self._dist:
            raise SchedulingError(
                "no path between start_hub and end_hub "
                "(blocked zones or disconnected network)"
            )
        self._capacity: dict[str, int] = {}
        self._hop_weight: dict[str, float] = {}
        for zone in graph.zones:
            self._capacity[zone.name] = zone.capacity
            preferred = zone.zone_type is ZoneType.PRIORITY or zone.is_end
            self._hop_weight[zone.name] = (
                0.0 if preferred else self.NON_PRIORITY_WEIGHT
            )

    @property
    def shortest_cost(self) -> int:
        """Return the capacity-free movement cost from start to end."""
        return self._dist[self._graph.start.name]

    def plan(
        self,
        drone_id: int,
        table: Reservations,
        rng: Optional[random.Random] = None,
        jitter: float = 0.0,
    ) -> Optional[Route]:
        """Plan the earliest arrival route of a drone.

        Args:
            drone_id: Identifier of the drone.
            table: Current reservations (not modified).
            rng: Random source used to break ties differently.
            jitter: Amplitude of the random tie-break noise.

        Returns:
            The route, or None if the end is unreachable before the
            horizon with the current reservations.
        """
        graph = self._graph
        start_name = graph.start.name
        end_name = graph.end.name
        dist = self._dist
        horizon = self._horizon
        capacity = self._capacity
        hop_weight = self._hop_weight
        zone_has_room = table.zone_has_room
        link_has_room = table.link_has_room
        noise: dict[str, float] = {}
        if rng is not None and jitter > 0:
            noise = {name: rng.random() * jitter for name in capacity}
        first: StateKey = (start_name, 0)
        best: dict[StateKey, float] = {first: 0.0}
        parent: dict[StateKey, Optional[StateKey]] = {first: None}
        heap: list[tuple[float, float, int, int, str]] = [
            (float(dist[start_name]), 0.0, 0, 0, start_name)
        ]
        counter = 1
        infinity = float("inf")
        while heap:
            _, sec, _, turn, name = heapq.heappop(heap)
            if best[(name, turn)] < sec:
                continue
            if name == end_name:
                return self._build_route(drone_id, parent, (name, turn))
            options: list[tuple[str, int, float]] = []
            if name == start_name:
                options.append((name, turn + 1, 0.0))
            elif zone_has_room(name, capacity[name], turn + 1):
                options.append((name, turn + 1, self.WAIT_WEIGHT))
            for hop in graph.hops(name):
                if not link_has_room(hop.link_key, hop.link_capacity,
                                     turn + 1):
                    continue
                arrive = turn + hop.cost
                if hop.cost == 2 and not link_has_room(
                    hop.link_key, hop.link_capacity, turn + 2
                ):
                    continue
                if not zone_has_room(hop.name, hop.capacity, arrive):
                    continue
                extra = hop_weight[hop.name]
                if noise:
                    extra += noise[hop.name]
                options.append((hop.name, arrive, extra))
            for new_name, new_turn, extra in options:
                remaining = dist.get(new_name)
                if remaining is None or new_turn + remaining > horizon:
                    continue
                key: StateKey = (new_name, new_turn)
                new_sec = sec + extra
                if new_sec < best.get(key, infinity):
                    best[key] = new_sec
                    parent[key] = (name, turn)
                    heapq.heappush(
                        heap,
                        (new_turn + remaining, new_sec, counter,
                         new_turn, new_name),
                    )
                    counter += 1
        return None

    def _build_route(
        self,
        drone_id: int,
        parent: dict[StateKey, Optional[StateKey]],
        last: StateKey,
    ) -> Route:
        """Convert the chain of search states into a Route.

        Stays in zones without a limit (start and end) are not recorded:
        they never constrain other drones.
        """
        keys: list[StateKey] = []
        current: Optional[StateKey] = last
        while current is not None:
            keys.append(current)
            current = parent[current]
        keys.reverse()
        route = Route(drone_id=drone_id, arrival=last[1])
        for (zone_a, turn_a), (zone_b, turn_b) in zip(keys, keys[1:]):
            limited = self._capacity[zone_b] < UNLIMITED
            if zone_a == zone_b:
                if limited:
                    route.zone_stays.append((zone_b, turn_b))
                continue
            conn = self._graph.find_connection(zone_a, zone_b)
            if conn is None:
                raise SchedulingError("internal error: broken search path")
            if turn_b - turn_a == 1:
                route.moves.append(Move(turn_b, drone_id, zone_b, zone_b))
                route.link_uses.append((conn.key, turn_b))
            else:
                route.moves.append(
                    Move(turn_a + 1, drone_id, f"{zone_a}-{zone_b}",
                         zone_b, True)
                )
                route.moves.append(Move(turn_b, drone_id, zone_b, zone_b))
                route.link_uses.append((conn.key, turn_a + 1))
                route.link_uses.append((conn.key, turn_b))
            if limited:
                route.zone_stays.append((zone_b, turn_b))
        return route
