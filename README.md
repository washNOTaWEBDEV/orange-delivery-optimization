# Orange Delivery Optimization

A small Python project for planning efficient delivery routes for an orange-themed delivery operation.

## Features

- Computes the cheapest valid route through a set of delivery stops
- Supports a warehouse start/end point
- Exposes a simple CLI and Python API
- Includes a lightweight pytest suite

## Quick start

```bash
python -m pip install -e .
python -m orange_delivery_optimization --help
```

## Example

```python
from orange_delivery_optimization import optimize_routes

stops = {
    "warehouse": (0, 0),
    "north": (1, 2),
    "midtown": (3, 1),
    "harbor": (2, 4),
}

result = optimize_routes("warehouse", stops)
print(result["route"])
print(result["total_distance"])
```
