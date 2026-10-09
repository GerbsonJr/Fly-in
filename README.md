*This project has been created as part of the 42 curriculum by <login>.*

# Fly-in

## Description

Fly-in routes a fleet of drones from a `start_hub` to an `end_hub` through a
network of zones, in as few simulation turns as possible. It respects zone
capacities (`max_drones`), connection capacities (`max_link_capacity`) and the
zone types: `normal`, `priority` (preferred), `restricted` (2 turns) and
`blocked`.

Python 3.10+, no graph library, fully object oriented, type hinted (mypy) and
flake8 clean. Colored terminal output plus an animated pygame window.

## Instructions

```
make install                                  # flake8, mypy, pygame
make run MAP=maps/hard/01_maze_nightmare.txt       # text + window
make run-text MAP=maps/hard/01_maze_nightmare.txt  # text only
make debug MAP=maps/easy/01_linear_path.txt   # pdb
make lint                                     # flake8 + mypy
make lint-strict                              # flake8 + mypy --strict
make clean
```

Or directly: `python3 main.py <map> [options]`

| option | meaning |
| --- | --- |
| `--color auto/always/never` | ANSI colors (auto = only on a terminal) |
| `--visual` | map legend and zone state after every turn (terminal) |
| `--gui` | always open the window (error if it cannot be opened) |
| `--no-gui` | text output only |
| `--stats` | secondary metrics on stderr |
| `--time-limit S` | seconds of optimisation after the first solution (2) |
| `--iterations N` | maximum optimisation iterations (5000) |
| `--seed N` | random seed, same seed = same output (0) |

stdout only has the simulation lines (plus the `--visual` extras): one line per
turn, `D<ID>-<zone>` or `D<ID>-<connection>` while a drone is in flight towards
a restricted zone. Use `--color never` to pipe it.

The window opens by itself after the text output when running in a
terminal (not when the output is piped) and the animation starts alone. If
pygame or the display is missing, a warning is shown and the text output is
still produced.

Window keys: LEFT / RIGHT step, SPACE pause / play, R replay, ESC quit.

## Project structure

```
main.py                          entry point
assets/                          drone_icon.png, grid_backdrop.png (window)
maps/                            easy / medium / hard / challenger / invalid
fly_in/cli.py                    Application (arguments, flow, errors)
fly_in/core/settings.py          shared constants (UNLIMITED, tags, colors)
fly_in/core/zones.py             ZoneType, Zone
fly_in/core/links.py             Connection
fly_in/core/plan.py              Move, Route
fly_in/core/timetable.py         Schedule, Metrics
fly_in/network/topology.py       Network (adjacency, Dijkstra distances)
fly_in/network/reservations.py   Reservations (zone / link usage per turn)
fly_in/loading/map_reader.py     MapReader, ParseError (line + cause)
fly_in/routing/space_time.py     SpaceTimePlanner (A* over zone and turn)
fly_in/routing/fleet_planner.py  FleetPlanner (greedy plan + local search)
fly_in/checking/output_checker.py  OutputChecker (re-checks the output)
fly_in/playback/replay.py        Replay (turn snapshots)
fly_in/display/console.py        ConsoleRenderer (colors, board, stats)
fly_in/display/window.py         WindowRenderer (pygame)
fly_in/display/geometry.py       Layout, FleetTimeline (no pygame)
.flake8, mypy.ini, Makefile, .gitignore
```

## Rules as implemented

* Zone occupancy is measured right after each turn: drones leaving a zone free
  its capacity for drones entering during the same turn.
* A move to a restricted zone takes 2 turns. Turn 1 prints the connection in
  the direction of travel (`D1-roof1-roof2`), turn 2 prints the zone
  (`D1-roof2`). The drone cannot wait on the connection.
* A connection is counted for every turn a drone uses it (both turns of a
  restricted move), in both directions, so two drones never swap through a
  capacity 1 link.
* `start_hub` and `end_hub` have no capacity limit (`max_drones` there is
  accepted and ignored). Delivered drones are no longer tracked.
* Blocked zones are never entered. Between routes with the same arrival turn,
  the one through more priority zones is preferred.

## Algorithm

1. **Space-time A\*** (`SpaceTimePlanner`): states are `(zone, turn)`;
   transitions are wait, move (1 turn) and move to a restricted zone (2 turns).
   A move is allowed only if the `Reservations` has room in the target zone
   and on the link for each turn. The heuristic is the capacity-free shortest
   cost to the end (admissible and consistent), so the first arrival popped is
   the earliest. Ties: more priority zones, fewer waits outside the start hub.
2. **Greedy fleet plan** (`FleetPlanner`): drones 1..N are planned one after
   another, each reserving its zones and links. Drones spread over disjoint
   paths and wait when everything is full. No deadlock is possible, every
   route is a complete conflict-free space-time path.
3. **Local search**: a few drones (the slowest one with probability 0.6) are
   released and replanned in random order with random tie-break noise; the
   change is kept when `(makespan, drones at makespan, sum of arrivals)` does
   not get worse. After 150 failures a full randomised rebuild is tried. It
   stops on the time/iteration limit or when the makespan equals a proven lower
   bound (shortest cost + drones / start-out rate, same for the end).
4. **Validation**: `OutputChecker` re-reads the printed lines and checks every
   rule of the subject independently of the planner. The program refuses to
   print an invalid simulation.

The result is a heuristic: very good in practice, proven optimal when `--stats`
shows turns equal to the lower bound.

### Results on the provided maps

| map | drones | turns | target |
| --- | --- | --- | --- |
| easy / linear path | 2 | 4 | <= 6 |
| easy / simple fork | 4 | 4 | <= 8 |
| easy / basic capacity | 4 | 4 | <= 6 |
| medium / dead end trap | 5 | 8 | <= 12 |
| medium / circular loop | 6 | 15 | <= 15 |
| medium / priority puzzle | 5 | 7 | <= 12 |
| hard / maze nightmare | 8 | 13 | <= 30 |
| hard / capacity hell | 12 | 16 | <= 35 |
| hard / ultimate challenge | 15 | 26 | <= 45 |
| challenger / impossible dream | 25 | 43 | record 45 |

### Complexity

* Parser O(lines). Distances O((V + E) log V).
* One drone: A\* visits at most V x H states (H = horizon, about shortest cost
  + 2N + V), deg(v) transitions each: O(V H d log(V H)). In practice only the
  states with `turn + h` not above the arrival turn are visited.
* Greedy phase O(N V H d log(V H)); the optimisation phase is bounded by
  `--time-limit` / `--iterations`.
* Memory O(V H) per search (freed afterwards) plus the reservation table, O(total
  path length). Paths are not cached: each drone is planned against the live
  reservations, which is what keeps them conflict-free.

## Resources

* D. Silver, *Cooperative Pathfinding* (space-time A\* with a reservation
  table), AIIDE 2005.
* Python documentation: `heapq`, `dataclasses`, `unittest`, `argparse`.
* PEP 8, PEP 257, PEP 484; mypy and pygame documentation.

## AI usage

<!-- Adapt this section so it is true for you before submitting. -->
An AI assistant (Claude) was used to design the architecture and to write the
code, the tests and this README. Everything was reviewed, run on all the
provided maps and tested, and is explained during the peer review.
