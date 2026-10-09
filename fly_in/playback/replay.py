"""Turn by turn replay of a schedule, used for the visual output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from fly_in.network.topology import Network
from fly_in.core.plan import Move
from fly_in.core.timetable import Schedule


@dataclass(frozen=True)
class TurnSnapshot:
    """State of the fleet right after one turn.

    Attributes:
        turn: Turn number (starting at 1).
        moves: Movements performed during the turn.
        occupancy: Zone name -> drones inside it (delivered excluded).
        in_flight: Connection name -> drones currently on it.
        delivered: Number of drones that reached the end zone.
        delivered_ids: Identifiers of the delivered drones.
    """

    turn: int
    moves: tuple[Move, ...]
    occupancy: dict[str, list[int]]
    in_flight: dict[str, list[int]]
    delivered: int
    delivered_ids: tuple[int, ...] = ()


class Replay:
    """Replays a schedule and yields one snapshot per turn."""

    def __init__(self, graph: Network, schedule: Schedule) -> None:
        """Store the network and the schedule to replay."""
        self._graph = graph
        self._schedule = schedule

    def initial_snapshot(self) -> TurnSnapshot:
        """Return the state before the first turn (all drones at start)."""
        drones = list(range(1, len(self._schedule.routes) + 1))
        return TurnSnapshot(
            0, (), {self._graph.start.name: drones}, {}, 0, ()
        )

    def snapshots(self) -> Iterator[TurnSnapshot]:
        """Yield the state after every turn, in order."""
        end = self._graph.end.name
        start = self._graph.start.name
        nb_drones = len(self._schedule.routes)
        zone_of: dict[int, Optional[str]] = {
            drone: start for drone in range(1, nb_drones + 1)
        }
        flight_of: dict[int, str] = {}
        delivered_ids: list[int] = []
        for turn, moves in enumerate(self._schedule.moves_by_turn(), 1):
            for move in moves:
                if move.in_flight:
                    zone_of[move.drone_id] = None
                    flight_of[move.drone_id] = move.token
                    continue
                flight_of.pop(move.drone_id, None)
                if move.zone == end:
                    del zone_of[move.drone_id]
                    delivered_ids.append(move.drone_id)
                else:
                    zone_of[move.drone_id] = move.zone
            occupancy: dict[str, list[int]] = {}
            for drone, zone in zone_of.items():
                if zone is not None:
                    occupancy.setdefault(zone, []).append(drone)
            in_flight: dict[str, list[int]] = {}
            for drone, conn_name in flight_of.items():
                in_flight.setdefault(conn_name, []).append(drone)
            yield TurnSnapshot(
                turn,
                tuple(moves),
                occupancy,
                in_flight,
                len(delivered_ids),
                tuple(delivered_ids),
            )
