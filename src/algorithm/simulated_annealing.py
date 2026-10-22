import random
import math
from time import perf_counter

from src.init.models import Position, Orientation
from src.init.operations import move, rotate, swap
from src.init.constraints import direction_of_car, is_valid_state
from src.init.objective import calculate_objective
from src.init.initialization import generate_initial_state


def is_local_optimum(vehicles, positions, ship):
    """True jika tidak ada satu operasi valid yang meningkatkan objective."""
    # Memindahkan atau merotasi kendaraan di kapal tidak mengubah shipping fee.
    # Periksa move yang bisa menaikkan nilai: memasukkan atau mengeluarkan mobil.
    for i, vehicle in enumerate(vehicles):
        if positions[i] is not None:
            # Pengeluaran hanya meningkatkan objective jika tarifnya negatif.
            if vehicle.shipping_fee < 0:
                candidate = move(positions, i, None)
                if is_valid_state(vehicles, candidate, ship):
                    return False
            continue

        if vehicle.shipping_fee <= 0:
            continue

        orientations = list(Orientation)
        if vehicle.dimensions.w == vehicle.dimensions.l:
            orientations = [Orientation.HORIZONTAL]

        for orientation in orientations:
            dimensions = direction_of_car(vehicle, Position(0, 0, orientation))
            max_x = ship.dimensions.w - dimensions.w
            max_y = ship.dimensions.l - dimensions.l

            for x in range(max_x + 1):
                for y in range(max_y + 1):
                    candidate = move(positions, i, Position(x, y, orientation))
                    if is_valid_state(vehicles, candidate, ship):
                        return False

    # Swap dapat menaikkan nilai jika kendaraan dari luar lebih menguntungkan.
    for i in range(len(vehicles)):
        for j in range(i + 1, len(vehicles)):
            if (positions[i] is None) == (positions[j] is None):
                continue

            outside = i if positions[i] is None else j
            inside = j if positions[i] is None else i
            if vehicles[outside].shipping_fee <= vehicles[inside].shipping_fee:
                continue

            candidate = swap(positions, i, j)
            if is_valid_state(vehicles, candidate, ship):
                return False

    return True


def simulated_annealing(
    vehicles, ship, T0: float = 100, alpha=0.999, T_min=0.1,
    max_iter=5000, initial=None, seed=11,
):
    """Menjalankan SA serta mencatat objective, probabilitas, dan local optimum."""
    if T0 <= 0 or not 0 < alpha < 1 or T_min <= 0:
        raise ValueError("suhu tidak valid")
    if type(max_iter) is not int or max_iter < 0:
        raise ValueError("max_iter harus integer >= 0.")

    rng = random.Random(seed)
    start_time = perf_counter()

    current = (
        generate_initial_state(vehicles, ship, rng)
        if initial is None else list(initial)
    )

    if not is_valid_state(vehicles, current, ship):
        raise ValueError("state awal tidak valid")

    initial_state = list(current)
    current_value = calculate_objective(vehicles, current)
    best, best_value = list(current), current_value
    history, probs = [current_value], []
    temperatures = []  # Suhu untuk setiap iterasi, mulai iterasi 1.
    deltas = []        # Objective kandidat dikurangi objective sebelum keputusan.

    # State awal ikut dihitung jika sudah berada pada local optimum.
    in_local_optimum = bool(vehicles) and is_local_optimum(vehicles, current, ship)
    local_optimum_count = int(in_local_optimum)
    local_optimum_history = [in_local_optimum]  # Sejajar dengan history.

    rejected_moves = 0
    worse_accepted = 0
    failed_neighbor = 0
    iterations = 0
    stop_reason = "iteration_limit" if vehicles else "no_vehicles"

    for iteration in range(1, max_iter + 1):
        if not vehicles:
            break

        temperature = T0 * alpha ** iteration
        if temperature < T_min:
            stop_reason = "temperature_limit"
            break

        temperatures.append(temperature)
        candidate = None

        for _ in range(100):
            i = rng.randrange(len(vehicles))
            action = rng.choice(["move", "rotate", "swap"])

            if action == "move":
                if current[i] is None:
                    position = Position(
                        rng.randrange(ship.dimensions.w),
                        rng.randrange(ship.dimensions.l),
                        rng.choice(list(Orientation)),
                    )
                    neighbor = move(current, i, position)
                elif rng.random() < 0.15:
                    neighbor = move(current, i, None)
                else:
                    position = Position(
                        rng.randrange(ship.dimensions.w),
                        rng.randrange(ship.dimensions.l),
                        current[i].orientation,
                    )
                    neighbor = move(current, i, position)

            elif action == "rotate":
                neighbor = rotate(current, i)

            elif len(vehicles) > 1:
                j = rng.randrange(len(vehicles) - 1)
                if j >= i:
                    j += 1
                neighbor = swap(current, i, j)

            else:
                continue

            if neighbor != current and is_valid_state(
                vehicles, neighbor, ship
            ):
                candidate = neighbor
                break

        if candidate is None:
            failed_neighbor += 1
            probs.append(None)
            deltas.append(None)  # Tidak ada kandidat untuk dihitung.
            history.append(current_value)
            local_optimum_history.append(in_local_optimum)
            iterations = iteration
            continue

        new_value = calculate_objective(vehicles, candidate)
        delta = new_value - current_value
        deltas.append(delta)

        probability = 1.0 if delta >= 0 else math.exp(delta / temperature)
        probs.append(probability)

        if delta >= 0 or rng.random() < probability:
            current = candidate
            current_value = new_value

            if delta < 0:
                worse_accepted += 1

            if current_value > best_value:
                best, best_value = list(current), current_value

            # Periksa ulang hanya setelah state berubah.
            was_local_optimum = in_local_optimum
            in_local_optimum = is_local_optimum(vehicles, current, ship)
            if in_local_optimum and not was_local_optimum:
                local_optimum_count += 1
        else:
            rejected_moves += 1

        history.append(current_value)
        local_optimum_history.append(in_local_optimum)
        iterations = iteration

    duration = perf_counter() - start_time

    return {
        "initial_state": initial_state,
        "initial_objective": calculate_objective(vehicles, initial_state),
        "final_state": list(current),
        "final_objective": current_value,
        "best_state": best,
        "best_objective": best_value,
        "history": history,
        "probs": probs,
        "temperatures": temperatures,
        "deltas": deltas,
        "local_optimum_count": local_optimum_count,
        "local_optimum_history": local_optimum_history,
        "local_optimum_definition": (
            "Tidak ada satu move, rotate, atau swap valid dengan objective "
            "lebih tinggi. Hitung saat masuk kondisi ini, termasuk state awal; "
            "bertahan pada kondisi yang sama tidak menambah hitungan."
        ),
        "iterations": iterations,
        "duration": duration,
        "stop_reason": stop_reason,
        "seed": seed,
        "parameters": {
            "T0": T0,
            "alpha": alpha,
            "T_min": T_min,
            "max_iter": max_iter,
            "seed": seed,
        },
        "failed_neighbor": failed_neighbor,
        "rejected_moves": rejected_moves,
        "worse_accepted": worse_accepted,
    }