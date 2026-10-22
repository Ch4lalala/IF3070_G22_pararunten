from src.init.models import Position, Orientation
from src.init.neighbors import move, rotate, swap
from src.init.constraints import direction_of_car, is_valid_state
from time import perf_counter
from src.init.objective import calculate_objective


def get_neighbors(vehicles, positions, ship):
    """Menghasilkan daftar susunan tetangga yang berubah dan valid."""
    if not is_valid_state(vehicles, positions, ship):
        raise ValueError("State awal tidak valid.")

    positions = list(positions)
    neighbors = []

    for i in range(len(vehicles)):
        vehicle = vehicles[i]
        position = positions[i]

        # Kendaraan di luar dapat dimasukkan dengan kedua orientasi.
        # Kendaraan di kapal dipindahkan dengan orientasi yang sama.
        if position is None:
            orientations = list(Orientation)

            # Untuk persegi, kedua orientasi memiliki bentuk yang sama.
            if vehicle.dimensions.w == vehicle.dimensions.l:
                orientations = [Orientation.HORIZONTAL]
        else:
            orientations = [position.orientation]

        # 1. MOVE: mencoba semua koordinat yang muat di dalam kapal.
        for orientation in orientations:
            sample_position = Position(0, 0, orientation)
            dimensions = direction_of_car(vehicle, sample_position)

            # Batas koordinat agar badan kendaraan tetap dalam kapal.
            max_x = ship.dimensions.w - dimensions.w
            max_y = ship.dimensions.l - dimensions.l

            if max_x < 0 or max_y < 0:
                continue

            for x in range(max_x + 1):
                for y in range(max_y + 1):
                    new_position = Position(x, y, orientation)
                    candidate = move(positions, i, new_position)

                    if candidate != positions and is_valid_state(
                        vehicles, candidate, ship
                    ):
                        neighbors.append(candidate)

        if position is not None:
            # MOVE keluar kapal: posisi kendaraan menjadi None.
            candidate = move(positions, i, None)

            if candidate != positions and is_valid_state(
                vehicles, candidate, ship
            ):
                neighbors.append(candidate)

            # 2. ROTATE: hanya kendaraan di kapal dan bukan persegi.
            if vehicle.dimensions.w != vehicle.dimensions.l:
                candidate = rotate(positions, i)

                if candidate != positions and is_valid_state(
                    vehicles, candidate, ship
                ):
                    neighbors.append(candidate)

    # 3. SWAP: coba setiap pasangan kendaraan sekali.
    for i in range(len(vehicles)):
        for j in range(i + 1, len(vehicles)):
            candidate = swap(positions, i, j)

            if candidate != positions and is_valid_state(
                vehicles, candidate, ship
            ):
                neighbors.append(candidate)

    return neighbors

def hill_climbing(vehicles, positions, ship, rng, max_sideways=100):
    """Hill-Climbing with Sideways Move; batas sideways berturut-turut."""
    if not is_valid_state(vehicles, positions, ship):
        raise ValueError("State awal tidak valid.")

    if type(max_sideways) is not int or max_sideways < 0:
        raise ValueError("max_sideways harus integer >= 0.")

    start_time = perf_counter()

    initial_positions = list(positions)
    current = list(positions)
    current_value = calculate_objective(vehicles, current)

    sideways_count = 0  # Sideways berturut-turut.
    total_sideways = 0  # Semua sideways selama pencarian.
    iterations = 0     # Jumlah perpindahan yang diterima.
    history = [current_value]  # Nilai awal pada iterasi 0.

    while True:
        neighbors = get_neighbors(vehicles, current, ship)

        if len(neighbors) == 0:
            stop_reason = "no_valid_neighbor"
            break

        # Cari semua kandidat dengan nilai objective tertinggi.
        best_value = calculate_objective(vehicles, neighbors[0])
        best_neighbors = [neighbors[0]]

        for candidate in neighbors[1:]:
            value = calculate_objective(vehicles, candidate)

            if value > best_value:
                best_value = value
                best_neighbors = [candidate]

            elif value == best_value:
                best_neighbors.append(candidate)

        # Hill climbing tidak menerima penurunan nilai.
        if best_value < current_value:
            stop_reason = "local_optimum"
            break

        if best_value == current_value:
            # Kandidat sama nilainya: gunakan jatah sideways.
            if sideways_count >= max_sideways:
                stop_reason = "sideways_limit"
                break

            sideways_count += 1
            total_sideways += 1

        else:
            # Ada peningkatan: reset hitungan sideways berturut-turut.
            sideways_count = 0

        # Pilih acak jika beberapa kandidat memiliki nilai terbaik sama.
        current = rng.choice(best_neighbors)
        current_value = best_value

        iterations += 1
        history.append(current_value)

        # Hentikan setelah batas sideways tercapai.
        if sideways_count > 0 and sideways_count >= max_sideways:
            stop_reason = "sideways_limit"
            break

    duration = perf_counter() - start_time

    return {
        "initial_state": initial_positions,
        "final_state": current,
        "final_objective": current_value,
        "history": history,
        "iterations": iterations,
        "total_sideways": total_sideways,
        "duration": duration,
        "parameters": {"max_sideways": max_sideways},
        "stop_reason": stop_reason,
    }