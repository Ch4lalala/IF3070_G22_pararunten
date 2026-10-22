import random
import math
import time
from time import perf_counter

from src.init.models import Position, Orientation
from src.init.neighbors import move, rotate, swap
from src.init.constraints import is_valid_state
from src.init.objective import calculate_objective
from src.init.initialization import generate_initial_state


def simulated_annealing(vehicles, ship, T0: float=100, alpha=0.999, T_min=0.1, max_iter=5000, initial=None, seed=11):
    if T0 <= 0 or not 0 < alpha < 1 or T_min <= 0:
        raise ValueError("suhu tidak valid")

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

    rejected_moves = 0
    worse_accepted = 0
    failed_neighbor = 0
    iterations = 0

    for iteration in range(1, max_iter + 1):
        temperature = T0 * alpha ** iteration
        if temperature < T_min:
            break
        if not vehicles:
            break

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
            history.append(current_value)
            iterations = iteration
            continue

        new_value = calculate_objective(vehicles, candidate)
        delta = new_value - current_value

        probability = 1.0 if delta >= 0 else math.exp(delta / temperature)
        probs.append(probability)

        if delta >= 0 or rng.random() < probability:
            current = candidate
            current_value = new_value

            if delta < 0:
                worse_accepted += 1

            if current_value > best_value:
                best, best_value = list(current), current_value
        else:
            rejected_moves += 1

        history.append(current_value)
        iterations = iteration

    duration = perf_counter() - start_time

    return {
        "initial_state": initial_state,
        "initial_value": calculate_objective(vehicles, initial_state),
        "final_state": list(current),
        "final_value": current_value,
        "best_state": best,
        "best_value": best_value,
        "history": history,
        "probs": probs,
        "iterations": iterations,
        "duration": duration,
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
