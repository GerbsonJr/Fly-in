"""Command line interface of the Fly-in simulator."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, Sequence

from fly_in.routing.space_time import SchedulingError
from fly_in.core.settings import ASSETS_DIR
from fly_in.network.topology import Network
from fly_in.core.timetable import Schedule
from fly_in.loading.map_reader import MapReader, ParseError
from fly_in.display.console import ConsoleRenderer
from fly_in.display.errors import DisplayError
from fly_in.routing.fleet_planner import FleetPlanner
from fly_in.playback.replay import Replay
from fly_in.checking.output_checker import OutputChecker, CheckError


class Application:
    """Reads a map, schedules the drones and shows the simulation."""

    def __init__(self) -> None:
        """Build the argument parser."""
        self._arg_parser = self._build_arg_parser()

    @staticmethod
    def _build_arg_parser() -> argparse.ArgumentParser:
        """Return the argument parser."""
        parser = argparse.ArgumentParser(
            prog="fly-in",
            usage="python3 main.py <map> [options]",
            description="Route a fleet of drones from start to end.",
        )
        parser.add_argument("map", help="path of the map file")
        parser.add_argument(
            "--color", choices=("auto", "always", "never"), default="auto",
            help="colored output (default: auto, only on a terminal)",
        )
        parser.add_argument(
            "--visual", action="store_true",
            help="also print the map legend and the state after each turn",
        )
        parser.add_argument(
            "--gui", action="store_true",
            help="always open the window (error if it cannot be opened)",
        )
        parser.add_argument(
            "--no-gui", action="store_true",
            help="text output only, never open the window",
        )
        parser.add_argument(
            "--stats", action="store_true",
            help="print the secondary metrics on stderr",
        )
        parser.add_argument(
            "--time-limit", type=float, default=2.0,
            help="seconds of optimisation after the first solution",
        )
        parser.add_argument(
            "--iterations", type=int, default=5000,
            help="maximum number of optimisation iterations",
        )
        parser.add_argument(
            "--seed", type=int, default=0,
            help="random seed (same seed, same result)",
        )
        return parser

    @staticmethod
    def _use_color(mode: str) -> bool:
        """Decide whether to emit ANSI colors."""
        if mode == "always":
            return True
        if mode == "never" or "NO_COLOR" in os.environ:
            return False
        return sys.stdout.isatty()

    @staticmethod
    def _open_gui(graph: Network, schedule: Schedule, nb_drones: int) -> None:
        """Open the optional pygame window (pygame must be installed)."""
        try:
            from fly_in.display.window import WindowRenderer
        except ImportError as exc:
            raise DisplayError(
                "pygame is not installed (run: pip install pygame)"
            ) from exc
        WindowRenderer(graph, schedule, nb_drones, ASSETS_DIR).run()

    def _show_window(
        self,
        args: argparse.Namespace,
        graph: Network,
        schedule: Schedule,
        nb_drones: int,
    ) -> None:
        """Open the window by default when running in a terminal.

        With ``--gui`` a failure is an error. Otherwise (automatic mode)
        the text output has already been printed, so a missing pygame or
        display only produces a warning.
        """
        if args.no_gui or not (args.gui or sys.stdout.isatty()):
            return
        try:
            self._open_gui(graph, schedule, nb_drones)
        except DisplayError as exc:
            if args.gui:
                raise
            sys.stderr.write(f"Warning: no window shown ({exc})\n")

    def run(self, argv: Optional[Sequence[str]] = None) -> int:
        """Run the program and return the process exit code."""
        args = self._arg_parser.parse_args(argv)
        try:
            data = MapReader().parse_file(args.map)
            scheduler = FleetPlanner(
                data.graph,
                data.nb_drones,
                time_limit=args.time_limit,
                max_iterations=args.iterations,
                seed=args.seed,
            )
            schedule = scheduler.solve()
            OutputChecker(data.graph, data.nb_drones).validate(
                schedule.to_lines()
            )
            renderer = ConsoleRenderer(
                data.graph, self._use_color(args.color)
            )
            out = sys.stdout
            if args.visual:
                out.write(renderer.render_legend(data.nb_drones) + "\n\n")
            for snapshot in Replay(data.graph, schedule).snapshots():
                out.write(renderer.format_turn(snapshot) + "\n")
                if args.visual:
                    out.write(
                        renderer.render_board(snapshot, data.nb_drones)
                        + "\n"
                    )
            out.flush()
            if args.stats:
                sys.stderr.write(
                    renderer.render_stats(
                        schedule.metrics(), scheduler.lower_bound()
                    ) + "\n"
                )
            self._show_window(args, data.graph, schedule, data.nb_drones)
        except (
            ParseError, SchedulingError, CheckError, DisplayError
        ) as exc:
            sys.stderr.write(f"Error: {exc}\n")
            return 1
        except BrokenPipeError:
            return 0
        except KeyboardInterrupt:
            sys.stderr.write("Interrupted\n")
            return 130
        except Exception as exc:  # last resort: never crash with a trace
            sys.stderr.write(f"Unexpected error: {exc}\n")
            return 2
        return 0
