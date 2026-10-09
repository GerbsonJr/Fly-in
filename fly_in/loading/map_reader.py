"""Parser for the map files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fly_in.core.settings import (
    ALLOWED_CONN_TAGS,
    ALLOWED_HUB_TAGS,
    ZONE_PREFIXES,
)
from fly_in.network.topology import Network, NetworkError
from fly_in.core.links import Connection
from fly_in.core.zones import Zone, ZoneType


class ParseError(Exception):
    """Invalid map file; the message includes the line and the cause."""

    def __init__(self, message: str, line_no: Optional[int] = None) -> None:
        """Store the cause and, when known, the faulty line number."""
        self.line_no = line_no
        self.reason = message
        prefix = f"line {line_no}: " if line_no is not None else ""
        super().__init__(f"{prefix}{message}")


@dataclass
class MapData:
    """Result of parsing a map: number of drones and the network."""

    nb_drones: int
    graph: Network


class MapReader:
    """Reads and validates a map written in the Fly-in format."""

    def parse_file(self, path: str) -> MapData:
        """Parse a map file.

        Raises:
            ParseError: If the file is unreadable or invalid.
        """
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise ParseError(f"cannot read '{path}': {exc}") from exc
        return self.parse_text(text)

    def parse_text(self, text: str) -> MapData:
        """Parse the content of a map.

        Raises:
            ParseError: With the line number and the cause of the problem.
        """
        nb_drones: Optional[int] = None
        graph = Network()
        for line_no, raw in enumerate(text.splitlines(), start=1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if nb_drones is None:
                nb_drones = self._parse_nb_drones(line, line_no)
                continue
            prefix, sep, rest = line.partition(":")
            prefix = prefix.strip()
            if not sep:
                raise ParseError(f"unrecognized line '{line}'", line_no)
            try:
                if prefix in ZONE_PREFIXES:
                    graph.add_zone(self._parse_zone(prefix, rest, line_no))
                elif prefix == "connection":
                    graph.add_connection(
                        self._parse_connection(rest, line_no)
                    )
                elif prefix == "nb_drones":
                    raise ParseError("nb_drones defined twice", line_no)
                else:
                    raise ParseError(f"unknown keyword '{prefix}'", line_no)
            except NetworkError as exc:
                raise ParseError(str(exc), line_no) from exc
        if nb_drones is None:
            raise ParseError("empty file: nb_drones is missing")
        try:
            graph.start
            graph.end
        except NetworkError as exc:
            raise ParseError(str(exc)) from exc
        return MapData(nb_drones, graph)

    # ---------------------------------------------------------- helpers
    @staticmethod
    def _parse_nb_drones(line: str, line_no: int) -> int:
        """Parse the mandatory first line ``nb_drones: <n>``."""
        key, sep, value = line.partition(":")
        if key.strip() != "nb_drones" or not sep:
            raise ParseError(
                "the first line must be 'nb_drones: <positive_integer>'",
                line_no,
            )
        value = value.strip()
        if not value.isdigit() or int(value) <= 0:
            raise ParseError(
                f"nb_drones must be a positive integer, got '{value}'",
                line_no,
            )
        return int(value)

    @staticmethod
    def _split_metadata(
        text: str, allowed: tuple[str, ...], line_no: int
    ) -> tuple[str, dict[str, str]]:
        """Split ``main [k=v k=v]`` into the main part and its metadata."""
        text = text.strip()
        if "[" not in text and "]" not in text:
            return text, {}
        start = text.find("[")
        if start == -1 or not text.endswith("]"):
            raise ParseError("malformed metadata block", line_no)
        inner = text[start + 1:-1]
        if "[" in inner or "]" in inner:
            raise ParseError("malformed metadata block", line_no)
        meta: dict[str, str] = {}
        for token in inner.split():
            key, sep, value = token.partition("=")
            if not sep or not key or not value:
                raise ParseError(
                    f"invalid metadata '{token}' (expected key=value)",
                    line_no,
                )
            if key not in allowed:
                raise ParseError(f"unknown metadata key '{key}'", line_no)
            if key in meta:
                raise ParseError(f"duplicated metadata key '{key}'", line_no)
            meta[key] = value
        return text[:start].strip(), meta

    @staticmethod
    def _parse_capacity(key: str, value: str, line_no: int) -> int:
        """Parse a strictly positive integer capacity."""
        if not value.isdigit() or int(value) <= 0:
            raise ParseError(
                f"{key} must be a positive integer, got '{value}'", line_no
            )
        return int(value)

    def _parse_zone(self, prefix: str, rest: str, line_no: int) -> Zone:
        """Build a Zone from a start_hub / end_hub / hub line."""
        main, meta = self._split_metadata(rest, ALLOWED_HUB_TAGS, line_no)
        tokens = main.split()
        if len(tokens) != 3:
            raise ParseError(
                f"expected '{prefix}: <name> <x> <y> [metadata]'", line_no
            )
        name, raw_x, raw_y = tokens
        if "-" in name:
            raise ParseError(
                f"zone name '{name}' cannot contain dashes", line_no
            )
        try:
            x, y = int(raw_x), int(raw_y)
        except ValueError:
            raise ParseError(
                f"coordinates must be integers, got '{raw_x} {raw_y}'",
                line_no,
            ) from None
        zone_type = ZoneType.NORMAL
        if "zone" in meta:
            try:
                zone_type = ZoneType.from_string(meta["zone"])
            except ValueError as exc:
                raise ParseError(str(exc), line_no) from exc
        is_hub = prefix != "hub"
        if is_hub and zone_type is ZoneType.BLOCKED:
            raise ParseError(f"{prefix} cannot be a blocked zone", line_no)
        max_drones = 1
        if "max_drones" in meta:
            max_drones = self._parse_capacity(
                "max_drones", meta["max_drones"], line_no
            )
        return Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=meta.get("color"),
            max_drones=max_drones,
            is_start=prefix == "start_hub",
            is_end=prefix == "end_hub",
        )

    def _parse_connection(self, rest: str, line_no: int) -> Connection:
        """Build a Connection from a ``connection:`` line."""
        main, meta = self._split_metadata(rest, ALLOWED_CONN_TAGS, line_no)
        if len(main.split()) != 1 or main.count("-") != 1:
            raise ParseError(
                "expected 'connection: <zone1>-<zone2> [metadata]' "
                "(zone names cannot contain dashes or spaces)",
                line_no,
            )
        zone_a, zone_b = main.split("-")
        if not zone_a or not zone_b:
            raise ParseError("connection with an empty zone name", line_no)
        capacity = 1
        if "max_link_capacity" in meta:
            capacity = self._parse_capacity(
                "max_link_capacity", meta["max_link_capacity"], line_no
            )
        return Connection(zone_a, zone_b, capacity)
