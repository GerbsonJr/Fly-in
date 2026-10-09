"""Optional pygame window that animates the simulation (``--gui``)."""

from __future__ import annotations

import os
from typing import Optional

import pygame

from fly_in.core.settings import RGB_COLORS
from fly_in.network.topology import Network
from fly_in.core.timetable import Schedule
from fly_in.core.zones import Zone, ZoneType
from fly_in.display.errors import DisplayError
from fly_in.display.geometry import FleetTimeline, Layout

Color = tuple[int, int, int]


class WindowRenderer:
    """Draws the network and the drones, one turn at a time.

    The animation starts by itself. Keys: RIGHT / LEFT step forward /
    backward, SPACE pauses or resumes, R replays, ESC or Q quits.
    """

    WIDTH = 1100
    HEIGHT = 720
    MARGIN = 110
    ANIM_MS = 380
    AUTO_MS = 700
    DEFAULT_COLOR: Color = (90, 95, 120)

    def __init__(
        self,
        graph: Network,
        schedule: Schedule,
        nb_drones: int,
        assets_dir: str,
    ) -> None:
        """Prepare the timeline; the window is created in :meth:`run`."""
        self._graph = graph
        self._nb_drones = nb_drones
        self._assets_dir = assets_dir
        self._lines = schedule.to_lines()
        self._timeline = FleetTimeline(graph, schedule)
        self._layout = Layout(graph, self.WIDTH, self.HEIGHT, self.MARGIN)
        self._turn = 0
        self._previous = 0
        self._auto = True
        self._anim_start = 0
        self._last_step = 0
        self._screen: Optional[pygame.Surface] = None
        self._background: Optional[pygame.Surface] = None
        self._drone_icon: Optional[pygame.Surface] = None
        self._font: Optional[pygame.font.Font] = None
        self._small: Optional[pygame.font.Font] = None

    # ------------------------------------------------------------ public
    def run(self) -> None:
        """Open the window and run the event loop until it is closed."""
        try:
            pygame.init()
            self._setup()
            self._loop()
        except pygame.error as exc:
            raise DisplayError(f"cannot open the window: {exc}") from exc
        finally:
            pygame.quit()

    # ----------------------------------------------------------- helpers
    def _setup(self) -> None:
        """Create the window, the fonts and load the assets."""
        self._screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Fly-in - drone simulation")
        self._font = pygame.font.Font(None, 26)
        self._small = pygame.font.Font(None, 20)
        self._background = self._load("grid_backdrop.png", self.WIDTH,
                                      self.HEIGHT)
        self._drone_icon = self._load("drone_icon.png", 38, 38)
        self._last_step = pygame.time.get_ticks()

    def _load(self, name: str, width: int, height: int
              ) -> Optional[pygame.Surface]:
        """Load and scale an asset; return None when it is unavailable."""
        path = os.path.join(self._assets_dir, name)
        try:
            image = pygame.image.load(path).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None
        return pygame.transform.smoothscale(image, (width, height))

    def _loop(self) -> None:
        """Handle events and draw frames."""
        clock = pygame.time.Clock()
        running = True
        while running:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._on_key(event.key, now) and running
            if self._auto and now - self._last_step > self.AUTO_MS:
                if self._turn < self._timeline.turns:
                    self._step(1, now)
                else:
                    self._auto = False
            progress = min(1.0, (now - self._anim_start) / self.ANIM_MS)
            self._draw(progress)
            clock.tick(60)

    def _on_key(self, key: int, now: int) -> bool:
        """Handle a key press; return False to quit."""
        if key in (pygame.K_ESCAPE, pygame.K_q):
            return False
        if key == pygame.K_RIGHT:
            self._step(1, now)
        elif key == pygame.K_LEFT:
            self._step(-1, now)
        elif key == pygame.K_SPACE:
            self._auto = not self._auto
            self._last_step = now
        elif key == pygame.K_r:
            self._turn = self._previous = 0
            self._auto = True
            self._anim_start = now
        return True

    def _step(self, delta: int, now: int) -> None:
        """Move to another turn and restart the animation."""
        target = max(0, min(self._turn + delta, self._timeline.turns))
        if target != self._turn:
            self._previous = self._turn
            self._turn = target
            self._anim_start = now
        self._last_step = now

    def _color_of(self, zone: Zone) -> Color:
        """Return the fill color of a zone."""
        if zone.color is None:
            return self.DEFAULT_COLOR
        return RGB_COLORS.get(zone.color.lower(), self.DEFAULT_COLOR)

    def _zone_radius(self, zone: Zone) -> int:
        """Return the drawing radius of a zone (bigger = more capacity)."""
        if zone.is_start or zone.is_end:
            return 30
        return 16 + 3 * min(zone.max_drones, 5)

    # ----------------------------------------------------------- drawing
    def _draw(self, progress: float) -> None:
        """Draw one complete frame."""
        screen = self._screen
        if screen is None:
            return
        if self._background is not None:
            screen.blit(self._background, (0, 0))
        else:
            screen.fill((18, 22, 38))
        self._draw_connections(screen)
        self._draw_zones(screen)
        self._draw_drones(screen, progress)
        self._draw_hud(screen)
        pygame.display.flip()

    def _draw_connections(self, screen: pygame.Surface) -> None:
        """Draw the links; thicker lines mean more capacity."""
        for conn in self._graph.connections:
            zone_a = self._graph.zone(conn.zone_a)
            zone_b = self._graph.zone(conn.zone_b)
            point_a = self._layout.to_screen(zone_a.x, zone_a.y)
            point_b = self._layout.to_screen(zone_b.x, zone_b.y)
            blocked = (zone_a.zone_type is ZoneType.BLOCKED
                       or zone_b.zone_type is ZoneType.BLOCKED)
            color: Color = (70, 70, 80) if blocked else (150, 155, 175)
            width = 2 + min(conn.max_link_capacity, 6)
            pygame.draw.line(screen, color, point_a, point_b, width)
            if conn.max_link_capacity > 1 and self._small is not None:
                label = self._small.render(
                    str(conn.max_link_capacity), True, (255, 255, 255)
                )
                mid = ((point_a[0] + point_b[0]) / 2,
                       (point_a[1] + point_b[1]) / 2)
                screen.blit(label, (mid[0] + 4, mid[1] - 18))

    def _draw_zones(self, screen: pygame.Surface) -> None:
        """Draw the zones with a border that shows their type."""
        borders: dict[ZoneType, Color] = {
            ZoneType.NORMAL: (235, 235, 235),
            ZoneType.PRIORITY: (80, 240, 240),
            ZoneType.RESTRICTED: (255, 70, 70),
            ZoneType.BLOCKED: (15, 15, 15),
        }
        for zone in self._graph.zones:
            x, y = self._layout.to_screen(zone.x, zone.y)
            center = (int(x), int(y))
            radius = self._zone_radius(zone)
            pygame.draw.circle(screen, self._color_of(zone), center, radius)
            pygame.draw.circle(screen, borders[zone.zone_type], center,
                               radius, 4)
            if zone.zone_type is ZoneType.BLOCKED:
                pygame.draw.line(screen, (255, 255, 255),
                                 (center[0] - radius // 2,
                                  center[1] - radius // 2),
                                 (center[0] + radius // 2,
                                  center[1] + radius // 2), 3)
                pygame.draw.line(screen, (255, 255, 255),
                                 (center[0] - radius // 2,
                                  center[1] + radius // 2),
                                 (center[0] + radius // 2,
                                  center[1] - radius // 2), 3)
            if self._small is not None:
                label = self._small.render(zone.name, True, (255, 255, 255))
                screen.blit(label, (center[0] - label.get_width() // 2,
                                    center[1] + radius + 4))

    def _screen_pos(self, pose_x: float, pose_y: float, slot: int,
                    count: int) -> tuple[float, float]:
        """Return the pixel position of a pose, with the sharing offset."""
        base_x, base_y = self._layout.to_screen(pose_x, pose_y)
        off_x, off_y = Layout.slot_offset(slot, count)
        return (base_x + off_x, base_y + off_y)

    def _draw_drones(self, screen: pygame.Surface, progress: float) -> None:
        """Draw the drones, sliding from their previous position."""
        before = self._timeline.poses(self._previous)
        after = self._timeline.poses(self._turn)
        for drone, pose in after.items():
            if pose.delivered:
                continue
            end = self._screen_pos(pose.x, pose.y, pose.slot, pose.count)
            old = before.get(drone)
            if old is None or old.delivered:
                pos = end
            else:
                start = self._screen_pos(old.x, old.y, old.slot, old.count)
                pos = (start[0] + (end[0] - start[0]) * progress,
                       start[1] + (end[1] - start[1]) * progress)
            center = (int(pos[0]), int(pos[1]))
            if self._drone_icon is not None:
                rect = self._drone_icon.get_rect(center=center)
                screen.blit(self._drone_icon, rect)
            else:
                pygame.draw.circle(screen, (255, 255, 255), center, 9)
                pygame.draw.circle(screen, (20, 20, 20), center, 9, 2)
            if self._small is not None:
                tag = self._small.render(str(drone), True, (255, 255, 120))
                screen.blit(tag, (center[0] + 10, center[1] - 24))

    def _draw_hud(self, screen: pygame.Surface) -> None:
        """Draw the turn counter, the moves of the turn and the help."""
        if self._font is None or self._small is None:
            return
        delivered = len(
            [p for p in self._timeline.poses(self._turn).values()
             if p.delivered]
        )
        mode = "AUTO" if self._auto else "MANUAL"
        title = self._font.render(
            f"Turn {self._turn}/{self._timeline.turns}   "
            f"delivered {delivered}/{self._nb_drones}   [{mode}]",
            True, (255, 255, 255),
        )
        screen.blit(title, (20, 16))
        if 1 <= self._turn <= len(self._lines):
            moves = self._small.render(
                self._lines[self._turn - 1][:150], True, (200, 230, 255)
            )
            screen.blit(moves, (20, self.HEIGHT - 52))
        help_text = self._small.render(
            "LEFT/RIGHT: step   SPACE: pause/play   R: replay   ESC: quit",
            True, (170, 170, 190),
        )
        screen.blit(help_text, (20, self.HEIGHT - 28))
