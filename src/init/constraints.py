from .models import Dimension, Vehicle, Ship, Position, Orientation
from collections.abc import Sequence

def direction_of_car(vehicle: Vehicle, position: Position) -> Dimension:
    """Mendapatkan dimensi kendaraan berdasarkan orientasi posisinya"""
    if position.orientation == Orientation.VERTICAL:
        return Dimension(w = vehicle.dimensions.l, l = vehicle.dimensions.w)

    return vehicle.dimensions

def is_overlapping(vehicle1: Vehicle, position1: Position, vehicle2: Vehicle, position2: Position) -> bool:
    """Mengecek apakah dua kendaraan saling bertumpuk"""
    dim1 = direction_of_car(vehicle1, position1)
    dim2 = direction_of_car(vehicle2, position2)

    if (position1.x + dim1.w <= position2.x or
        position2.x + dim2.w <= position1.x or
        position1.y + dim1.l <= position2.y or
        position2.y + dim2.l <= position1.y):
        return False

    return True

def is_in_ship (vehicle: Vehicle, position: Position, ship: Ship) -> bool:
    """Mengecek apakah kendaraan berada di dalam kapal"""
    dim = direction_of_car(vehicle, position)

    if (position.x < 0 or
        position.y < 0 or
        position.x + dim.w > ship.dimensions.w or
        position.y + dim.l > ship.dimensions.l):
        return False

    return True

def is_overweight(vehicles: Sequence[Vehicle], ship: Ship) -> bool:
    """Mengecek apakah total berat kendaraan melebihi kapasitas kapal"""
    total_weight = sum(vehicle.weight for vehicle in vehicles)

    if total_weight > ship.max_capacity:
        return True

    return False

def is_valid_state(vehicles: Sequence[Vehicle], positions: Sequence[Position | None], ship: Ship) -> bool:
    """Mengecek apakah susunan kendaraan valid."""
    if len(vehicles) != len(positions):
        return False

    ids = [vehicle.id for vehicle in vehicles]

    if len(ids) != len(set(ids)):
        return False

    for position in positions:
        if position is not None:
            if type(position.x) is not int or type(position.y) is not int:
                return False

    loaded_vehicles = []

    for i in range(len(vehicles)):
        if positions[i] is None:
            continue

        loaded_vehicles.append(vehicles[i])

        if not is_in_ship(vehicles[i], positions[i], ship):
            return False

        for j in range(i + 1, len(vehicles)):
            if positions[j] is None:
                continue

            if is_overlapping(
                vehicles[i], positions[i],
                vehicles[j], positions[j],
            ):
                return False

    if is_overweight(loaded_vehicles, ship):
        return False

    return True