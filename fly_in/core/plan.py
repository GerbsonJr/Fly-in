"""Moves and routes of single drones."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Move:
    """One drone movement printed on one simulation turn.

    Attributes:
        turn: Turn number (starting at 1).
        drone_id: Drone identifier (starting at 1).
        token: Printed target: a zone name, or a connection name while the
            drone is in flight towards a restricted zone.
        zone: Destination zone of the movement.
        in_flight: True when the drone is on a connection.
    """

    turn: int
    drone_id: int
    token: str
    zone: str
    in_flight: bool = False

    def __str__(self) -> str:
        """Return the movement as ``D<ID>-<target>``."""
        return f"D{self.drone_id}-{self.token}"


@dataclass
class Route:
    """The complete space-time path of one drone.

    Attributes:
        drone_id: Drone identifier.
        arrival: Turn at which the drone reaches the end zone.
        moves: Movements, ordered by turn.
        zone_stays: ``(zone, turn)`` pairs: the drone is in that zone
            right after that turn.
        link_uses: ``(connection key, turn)`` pairs: the drone is using
            that connection during that turn.
    """

    drone_id: int
    arrival: int
    moves: list[Move] = field(default_factory=list)
    zone_stays: list[tuple[str, int]] = field(default_factory=list)
    link_uses: list[tuple[tuple[str, str], int]] = field(
        default_factory=list
    )
