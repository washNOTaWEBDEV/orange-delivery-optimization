"""CLI entry point for orange delivery optimization."""

from __future__ import annotations

import argparse

from .optimizer import optimize_routes


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan an efficient orange delivery route.")
    parser.add_argument("--start", default="warehouse", help="Start and end location name.")
    parser.add_argument(
        "--locations",
        nargs="*",
        default=[
            "warehouse=0,0",
            "north=1,2",
            "midtown=3,1",
            "harbor=2,4",
            "south=0,3",
        ],
        help="Location entries in NAME=X,Y format.",
    )
    args = parser.parse_args()

    locations = {}
    for entry in args.locations:
        name, coords = entry.split("=", 1)
        x_str, y_str = coords.split(",", 1)
        locations[name] = (float(x_str), float(y_str))

    result = optimize_routes(args.start, locations)
    print(f"Route: {' -> '.join(result['route'])}")
    print(f"Total distance: {result['total_distance']}")
    print(f"Leg distances: {result['distance_by_leg']}")


if __name__ == "__main__":
    main()
