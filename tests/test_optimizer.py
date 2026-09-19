from orange_delivery_optimization import optimize_routes


def test_optimize_routes_returns_valid_loop():
    locations = {
        "warehouse": (0, 0),
        "north": (1, 2),
        "midtown": (3, 1),
        "harbor": (2, 4),
        "south": (0, 3),
    }

    result = optimize_routes("warehouse", locations)

    assert result["route"][0] == "warehouse"
    assert result["route"][-1] == "warehouse"
    assert len(result["route"]) == len(locations) + 1
    assert set(result["route"][1:-1]) == set(locations) - {"warehouse"}
    assert result["total_distance"] > 0
    assert result["distance_by_leg"]
