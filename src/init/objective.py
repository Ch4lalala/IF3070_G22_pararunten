from collections.abc import Sequence
from .models import Vehicle, Position

def calculate_objective(vehicles: Sequence[Vehicle], positions: Sequence[Position | None]) -> float:
    """Menghitung nilai objektif dari susunan kendaraan"""
    if len(vehicles) != len(positions):
        raise ValueError("Jumlah kendaraan dan posisi harus sama")

    total_shipping_fee = 0.0

    for i in range(len(vehicles)):
        if positions[i] is not None:
            total_shipping_fee += vehicles[i].shipping_fee

    return total_shipping_fee