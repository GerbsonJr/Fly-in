"""Global scheduling of the whole fleet."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Optional, Sequence

from fly_in.routing.space_time import SchedulingError, SpaceTimePlanner
from fly_in.network.topology import Network
from fly_in.network.reservations import Reservations
from fly_in.core.plan import Route
from fly_in.core.timetable import Schedule


@dataclass(frozen=True, order=True)
class Score:
    """Quality of a set of routes; lower is better (lexicographic)."""

    makespan: int
    drones_at_makespan: int
    total_arrival: int

    @classmethod
    def of(cls, routes: Sequence[Route]) -> Score:
        """Compute the score of a list of routes."""
        makespan = max(route.arrival for route in routes)
        return cls(
            makespan,
            sum(1 for route in routes if route.arrival == makespan),
            sum(route.arrival for route in routes),
        )


class FleetPlanner:
    """Builds a collision-free schedule that minimises the turn count.

    Phase 1 plans the drones one after another, each one taking the
    earliest arrival path allowed by the reservations of the previous ones
    (so drones spread over disjoint paths and wait when needed).
    Phase 2 is a randomised local search: a few drones are removed and
    replanned in a random order with random tie-breaking; the change is
    kept when the score does not get worse. Phase 2 stops as soon as the
    makespan reaches a proven lower bound, or on the time/iteration limit.
    """

    MAX_VICTIMS = 4
    RESTART_AFTER = 150

    def __init__(
        self,
        graph: Network,
        nb_drones: int,
        time_limit: float = 2.0,
        max_iterations: int = 5000,
        seed: int = 0,
        jitter: float = 0.5,
    ) -> None:
        """Configure the scheduler.

        Args:
            graph: The network.
            nb_drones: Number of drones to route.
            time_limit: Seconds allowed to the optimisation phase.
            max_iterations: Maximum local search iterations.
            seed: Seed of the random generator (reproducible results).
            jitter: Amplitude of the random tie-break noise.
        """
        self._graph = graph
        self._nb_drones = nb_drones
        self._time_limit = time_limit
        self._max_iterations = max_iterations
        self._seed = seed
        self._jitter = jitter
        shortest = graph.distances_to_end().get(graph.start.name)
        if shortest is None:
            raise SchedulingError(
                "no path between start_hub and end_hub "
                "(blocked zones or disconnected network)"
            )
        horizon = shortest + 2 * nb_drones + len(graph.zones) + 2
        self._planner = SpaceTimePlanner(graph, horizon)

    def lower_bound(self) -> int:
        """Return a valid lower bound of the number of turns.

        It combines the shortest path cost with the rate at which drones
        can leave the start hub and enter the end hub.
        """
        graph = self._graph
        out_rate = sum(
            min(conn.max_link_capacity, zone.capacity)
            for zone, conn in graph.neighbors(graph.start.name)
        )
        in_rate = sum(
            min(conn.max_link_capacity, zone.capacity)
            for zone, conn in graph.neighbors(graph.end.name)
        )
        rate = max(1, min(out_rate, in_rate))
        waves = math.ceil(self._nb_drones / rate)
        return self._planner.shortest_cost + waves - 1

    def solve(self) -> Schedule:
        """Compute the schedule.

        Raises:
            SchedulingError: If some drone cannot reach the end.
        """
        started = time.monotonic()
        rng = random.Random(self._seed)
        table = Reservations()
        routes = self._build(table, None)
        if routes is None:
            raise SchedulingError("could not route every drone to the end")
        current = Score.of(routes)
        bound = self.lower_bound()
        stagnation = 0
        for _ in range(self._max_iterations):
            if current.makespan <= bound:
                break
            if time.monotonic() - started > self._time_limit:
                break
            if stagnation >= self.RESTART_AFTER:
                stagnation = 0
                fresh = Reservations()
                rebuilt = self._build(fresh, rng)
                if rebuilt is not None and Score.of(rebuilt) <= current:
                    routes, table = rebuilt, fresh
                    current = Score.of(rebuilt)
                continue
            outcome = self._perturb(routes, table, rng, current)
            if outcome is not None and outcome < current:
                current = outcome
                stagnation = 0
            else:
                stagnation += 1
        return Schedule(routes)

    # ----------------------------------------------------------- helpers
    def _build(
        self, table: Reservations, rng: Optional[random.Random]
    ) -> Optional[list[Route]]:
        """Plan all the drones one after another into ``table``."""
        routes: list[Route] = []
        for drone_id in range(1, self._nb_drones + 1):
            route = self._planner.plan(drone_id, table, rng, self._jitter)
            if route is None:
                return None
            table.reserve(route)
            routes.append(route)
        return routes

    def _perturb(
        self,
        routes: list[Route],
        table: Reservations,
        rng: random.Random,
        current: Score,
    ) -> Optional[Score]:
        """Replan a few drones; keep the result if it is not worse.

        Returns:
            The new score when the change was kept, otherwise None.
        """
        count = len(routes)
        size = rng.randint(1, min(count, self.MAX_VICTIMS))
        victims = set(rng.sample(range(count), size))
        if rng.random() < 0.6:
            worst = max(route.arrival for route in routes)
            slowest = [i for i, r in enumerate(routes) if r.arrival == worst]
            victims.add(rng.choice(slowest))
        order = sorted(victims)
        rng.shuffle(order)
        old = {i: routes[i] for i in order}
        for index in order:
            table.release(routes[index])
        fresh: dict[int, Route] = {}
        for index in order:
            route = self._planner.plan(
                routes[index].drone_id, table, rng, self._jitter
            )
            if route is None:
                break
            table.reserve(route)
            fresh[index] = route
        if len(fresh) == len(order):
            trial = [fresh.get(i, routes[i]) for i in range(count)]
            score = Score.of(trial)
            if score <= current:
                routes[:] = trial
                return score
        for route in fresh.values():
            table.release(route)
        for route in old.values():
            table.reserve(route)
        return None
