import random
from collections.abc import Sequence
from .models import Vehicle, Position, Ship, Orientation
from .constraints import is_valid_state


def generate_initial_state(vehicles: Sequence[Vehicle], ship: Ship, rng: random.Random, max_attempts: int = 50) -> list[Position | None]:
    """Membuat susunan awal acak yang valid"""
    positions = [None] * len(vehicles)

    indices = list(range(len(vehicles)))
    rng.shuffle(indices)

    for i in indices:
        for _ in range(max_attempts):
            position = Position(
                x=rng.randrange(ship.dimensions.w),
                y=rng.randrange(ship.dimensions.l),
                orientation=rng.choice(list(Orientation)),
            )

            positions[i] = position

            if is_valid_state(vehicles, positions, ship):
                break

            positions[i] = None

    return positions