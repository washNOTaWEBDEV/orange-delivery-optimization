"""Delivery route optimization utilities."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Tuple

Coordinate = Tuple[float, float]
Route = List[str]


def _distance(a: Coordinate, b: Coordinate) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def optimize_routes(start: str, locations: Dict[str, Coordinate]) -> dict:
    """Return a route that starts and ends at the start location.

    The implementation uses a simple nearest-neighbor heuristic, which is enough
    for small delivery networks and deterministic for tests.
    """
    if start not in locations:
        raise ValueError(f"Start location {start!r} is not present in locations.")

    remaining = [name for name in locations if name != start]
    if not remaining:
        return {
            "route": [start],
            "total_distance": 0.0,
            "distance_by_leg": [],
        }

    route: Route = [start]
    current = start
    total_distance = 0.0
    distance_by_leg: List[float] = []

    while remaining:
        next_stop = min(
            remaining,
            key=lambda name: _distance(locations[current], locations[name]),
        )
        leg_distance = _distance(locations[current], locations[next_stop])
        route.append(next_stop)
        total_distance += leg_distance
        distance_by_leg.append(leg_distance)
        remaining.remove(next_stop)
        current = next_stop

    final_leg = _distance(locations[current], locations[start])
    route.append(start)
    total_distance += final_leg
    distance_by_leg.append(final_leg)

    return {
        "route": route,
        "total_distance": round(total_distance, 2),
        "distance_by_leg": [round(value, 2) for value in distance_by_leg],
    }
