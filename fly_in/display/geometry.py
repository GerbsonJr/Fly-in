"""Pygame free geometry and timeline helpers used by the GUI."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fly_in.network.topology import Network
from fly_in.core.timetable import Schedule
from fly_in.playback.replay import Replay, TurnSnapshot


@dataclass(frozen=True)
class Pose:
    """Where a drone is, in world coordinates, at the end of a turn.

    Attributes:
        x: World x coordinate (zone, or middle of a connection).
        y: World y coordinate.
        slot: Index of the drone among those sharing the same place.
        count: Number of drones sharing the same place.
        delivered: True once the drone reached the end zone.
    """

    x: float
    y: float
    slot: int = 0
    count: int = 1
    delivered: bool = False


class Layout:
    """Fits the world coordinates of the map into a screen rectangle."""

    def __init__(
        self, graph: Network, width: int, height: int, margin: int
    ) -> None:
        """Compute the scale and offsets (y axis points up)."""
        xs = [zone.x for zone in graph.zones]
        ys = [zone.y for zone in graph.zones]
        self._min_x, self._max_y = min(xs), max(ys)
        span_x = max(max(xs) - self._min_x, 1)
        span_y = max(self._max_y - min(ys), 1)
        avail_w = width - 2 * margin
        avail_h = height - 2 * margin
        self._scale = min(avail_w / span_x, avail_h / span_y)
        self._off_x = margin + (avail_w - (max(xs) - self._min_x)
                                * self._scale) / 2
        self._off_y = margin + (avail_h - (self._max_y - min(ys))
                                * self._scale) / 2

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        """Convert world coordinates into screen pixels."""
        return (
            self._off_x + (x - self._min_x) * self._scale,
            self._off_y + (self._max_y - y) * self._scale,
        )

    @staticmethod
    def slot_offset(slot: int, count: int) -> tuple[float, float]:
        """Return the pixel offset of a drone sharing a place with others."""
        if count <= 1:
            return (0.0, 0.0)
        radius = min(30.0, 10.0 + 2.5 * count)
        angle = 2 * math.pi * slot / count - math.pi / 2
        return (radius * math.cos(angle), radius * math.sin(angle))


class FleetTimeline:
    """Pose of every drone after each turn (index 0 is before turn 1)."""

    def __init__(self, graph: Network, schedule: Schedule) -> None:
        """Replay the schedule and store all the poses."""
        self._graph = graph
        simulation = Replay(graph, schedule)
        self._poses: list[dict[int, Pose]] = [
            self._poses_of(simulation.initial_snapshot())
        ]
        for snapshot in simulation.snapshots():
            self._poses.append(self._poses_of(snapshot))

    @property
    def turns(self) -> int:
        """Return the number of simulation turns."""
        return len(self._poses) - 1

    def poses(self, turn: int) -> dict[int, Pose]:
        """Return the poses after ``turn`` (clamped to the valid range)."""
        return self._poses[max(0, min(turn, self.turns))]

    def _poses_of(self, snapshot: TurnSnapshot) -> dict[int, Pose]:
        """Convert a snapshot into poses."""
        graph = self._graph
        poses: dict[int, Pose] = {}
        for name, drones in snapshot.occupancy.items():
            zone = graph.zone(name)
            ordered = sorted(drones)
            for slot, drone in enumerate(ordered):
                poses[drone] = Pose(zone.x, zone.y, slot, len(ordered))
        for conn_name, drones in snapshot.in_flight.items():
            origin, _, target = conn_name.partition("-")
            zone_a, zone_b = graph.zone(origin), graph.zone(target)
            mid_x = (zone_a.x + zone_b.x) / 2
            mid_y = (zone_a.y + zone_b.y) / 2
            ordered = sorted(drones)
            for slot, drone in enumerate(ordered):
                poses[drone] = Pose(mid_x, mid_y, slot, len(ordered))
        end = graph.end
        arrived = sorted(snapshot.delivered_ids)
        for slot, drone in enumerate(arrived):
            poses[drone] = Pose(end.x, end.y, slot, len(arrived), True)
        return poses
