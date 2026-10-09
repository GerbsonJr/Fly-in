"""Colored terminal rendering of the simulation."""

from __future__ import annotations

from typing import Optional

from fly_in.core.settings import ANSI_CODES, ANSI_RESET, UNLIMITED
from fly_in.network.topology import Network
from fly_in.core.plan import Move
from fly_in.core.timetable import Metrics
from fly_in.core.zones import Zone
from fly_in.playback.replay import TurnSnapshot


class ConsoleRenderer:
    """Formats simulation data, optionally with ANSI colors."""

    def __init__(self, graph: Network, use_color: bool) -> None:
        """Create a renderer.

        Args:
            graph: The network (used to find the color of each zone).
            use_color: Emit ANSI escape codes when True.
        """
        self._graph = graph
        self._use_color = use_color

    def paint(self, text: str, color: Optional[str]) -> str:
        """Color ``text``; unknown or missing colors leave it unchanged."""
        if not self._use_color or color is None:
            return text
        code = ANSI_CODES.get(color.lower())
        if code is None:
            return text
        return f"\033[{code}m{text}{ANSI_RESET}"

    def format_move(self, move: Move) -> str:
        """Return ``D<ID>-<target>`` painted with the destination color."""
        zone = self._graph.zone(move.zone)
        return self.paint(str(move), zone.color)

    def format_turn(self, snapshot: TurnSnapshot) -> str:
        """Return the output line of a turn."""
        return " ".join(self.format_move(m) for m in snapshot.moves)

    def render_legend(self, nb_drones: int) -> str:
        """Return a description of the map (zones and connections)."""
        lines = [f"Map: {nb_drones} drone(s)"]
        for zone in self._graph.zones:
            lines.append("  " + self._describe_zone(zone))
        for conn in self._graph.connections:
            if conn.max_link_capacity > 1:
                lines.append(
                    f"  link {conn.name} (capacity {conn.max_link_capacity})"
                )
        return "\n".join(lines)

    def render_board(self, snapshot: TurnSnapshot, nb_drones: int) -> str:
        """Return the state of zones and connections after a turn."""
        parts: list[str] = []
        for name, drones in snapshot.occupancy.items():
            zone = self._graph.zone(name)
            ids = ",".join(f"D{d}" for d in sorted(drones))
            parts.append(self.paint(f"{name}[{ids}]", zone.color))
        for name, drones in snapshot.in_flight.items():
            ids = ",".join(f"D{d}" for d in sorted(drones))
            parts.append(f"~{name}[{ids}]")
        where = "  ".join(parts) if parts else "-"
        return (
            f"    state: {where}\n"
            f"    delivered: {snapshot.delivered}/{nb_drones}"
        )

    @staticmethod
    def render_stats(metrics: Metrics, lower_bound: int) -> str:
        """Return the secondary metrics of the schedule."""
        return (
            f"Turns: {metrics.turns} (lower bound: {lower_bound})\n"
            f"Drones: {metrics.nb_drones}\n"
            f"Average turns per drone: {metrics.avg_turns_per_drone:.2f}\n"
            f"Total path cost: {metrics.total_path_cost}\n"
            f"Average moves per turn: {metrics.avg_moves_per_turn:.2f}\n"
            f"Max moves in a turn: {metrics.max_moves_in_a_turn}"
        )

    def _describe_zone(self, zone: Zone) -> str:
        """Return a one line description of a zone."""
        role = "start" if zone.is_start else "end" if zone.is_end else "hub"
        capacity = (
            "unlimited" if zone.capacity >= UNLIMITED else str(zone.capacity)
        )
        text = (
            f"{role:<5} {zone.name} ({zone.x},{zone.y}) "
            f"{zone.zone_type.value}, capacity {capacity}"
        )
        return self.paint(text, zone.color)
