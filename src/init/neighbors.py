from collections.abc import Sequence
from .models import Position, Orientation

def move(positions: Sequence[Position | None], index: int, new_position: Position | None) -> list[Position | None]:
    """Memindahkan, memasukkan, atau mengeluarkan kendaraan"""
    new_positions = list(positions)
    new_positions[index] = new_position

    return new_positions


def rotate(positions: Sequence[Position | None], index: int) -> list[Position | None]:
    """Merotasi kendaraan tanpa mengubah koordinatnya"""
    new_positions = list(positions)
    position = positions[index]

    if position is None:
        return new_positions

    if position.orientation == Orientation.HORIZONTAL:
        orientation = Orientation.VERTICAL
    else:
        orientation = Orientation.HORIZONTAL

    new_positions[index] = Position(
        x=position.x,
        y=position.y,
        orientation=orientation,
    )

    return new_positions


def swap(positions: Sequence[Position | None], index_a: int, index_b: int) -> list[Position | None]:
    """Menukar penempatan dua kendaraan, termasuk orientasinya"""
    new_positions = list(positions)

    new_positions[index_a], new_positions[index_b] = (
        new_positions[index_b],
        new_positions[index_a],
    )

    return new_positions