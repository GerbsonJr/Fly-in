"""The schedule of the whole fleet and its metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from fly_in.core.plan import Move, Route


@dataclass(frozen=True)
class Metrics:
    """Optional evaluation metrics of a schedule."""

    turns: int
    nb_drones: int
    avg_turns_per_drone: float
    total_path_cost: int
    avg_moves_per_turn: float
    max_moves_in_a_turn: int


class Schedule:
    """The routes of all drones, grouped by simulation turn."""

    def __init__(self, routes: Sequence[Route]) -> None:
        """Store the routes ordered by drone id."""
        self._routes = sorted(routes, key=lambda route: route.drone_id)

    @property
    def routes(self) -> list[Route]:
        """Return the routes ordered by drone id."""
        return list(self._routes)

    @property
    def turns(self) -> int:
        """Return the number of simulation turns."""
        if not self._routes:
            return 0
        return max(route.arrival for route in self._routes)

    def moves_by_turn(self) -> list[list[Move]]:
        """Return the movements of each turn (index 0 is turn 1)."""
        table: list[list[Move]] = [[] for _ in range(self.turns)]
        for route in self._routes:
            for move in route.moves:
                table[move.turn - 1].append(move)
        for row in table:
            row.sort(key=lambda move: move.drone_id)
        return table

    def to_lines(self) -> list[str]:
        """Return the simulation output, one line per turn."""
        return [
            " ".join(str(move) for move in row)
            for row in self.moves_by_turn()
        ]

    def metrics(self) -> Metrics:
        """Compute the secondary evaluation metrics."""
        rows = self.moves_by_turn()
        total_moves = sum(len(row) for row in rows)
        turns = self.turns
        count = len(self._routes)
        return Metrics(
            turns=turns,
            nb_drones=count,
            avg_turns_per_drone=(
                sum(route.arrival for route in self._routes) / count
                if count else 0.0
            ),
            total_path_cost=total_moves,
            avg_moves_per_turn=total_moves / turns if turns else 0.0,
            max_moves_in_a_turn=max((len(row) for row in rows), default=0),
        )
