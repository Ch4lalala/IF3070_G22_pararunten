from ..init.constraints import is_valid_state
from ..init.objective import calculate_objective
from ..init.initialization import generate_initial_state
from ..init.models import Position, Orientation
from ..init.neighbors import move, rotate, swap
from time import perf_counter

def generate_genome(vehicles, ship, rng):
    """Membuat satu individu berupa susunan kendaraan yang valid."""
    return generate_initial_state(vehicles, ship, rng)

def generate_population(vehicles, ship, population_size, rng):
    """Membuat kumpulan individu awal."""
    return [
        generate_genome(vehicles, ship, rng)
        for _ in range(population_size)
    ]

def fitness(vehicles, individual):
    """Menghitung fitness individu yang sudah valid."""
    return calculate_objective(vehicles, individual)

def select_parent(population, fitness_values, rng):
    """Roulette wheel: fitness lebih tinggi memberi peluang lebih besar."""
    if max(fitness_values) == 0:
        return rng.choice(population)
    return rng.choices(population, weights=fitness_values, k=1)[0]

def crossover(parent_a, parent_b, rng):
    """Satu child dari satu titik potong; parent tidak diubah."""
    if len(parent_a) < 2:
        return list(parent_a)
    cut = rng.randrange(1, len(parent_a))
    return parent_a[:cut] + parent_b[cut:]

def mutate(individual, ship, rng):
    """Mencoba satu perubahan acak pada individu."""
    if not individual:
        return list(individual)

    index = rng.randrange(len(individual))
    mutation_type = rng.choice(["move", "remove", "rotate", "swap"])

    if mutation_type == "move":
        new_position = Position(
            x=rng.randrange(ship.dimensions.w),
            y=rng.randrange(ship.dimensions.l),
            orientation=rng.choice(list(Orientation)),
        )
        return move(individual, index, new_position)

    elif mutation_type == "remove":
        return move(individual, index, None)

    elif mutation_type == "rotate":
        return rotate(individual, index)

    elif len(individual) >= 2:
        index_a, index_b = rng.sample(range(len(individual)), 2)
        return swap(individual, index_a, index_b)

    return list(individual)

def run_genetic_algorithm(
    vehicles,
    ship,
    population_size,
    generations,
    mutation_rate,
    rng,
):
    """Menjalankan GA dan mencatat hasil pencarian."""
    if type(population_size) is not int or population_size < 1:
        raise ValueError("Jumlah populasi harus integer minimal 1.")

    if type(generations) is not int or generations < 0:
        raise ValueError("Jumlah generasi harus integer minimal 0.")

    if not 0 <= mutation_rate <= 1:
        raise ValueError("Mutation rate harus antara 0 dan 1.")

    # Durasi mencakup inisialisasi populasi dan seluruh generasi.
    start = perf_counter()

    population = generate_population(
        vehicles, ship, population_size, rng
    )

    # Position harus memakai frozen=True.
    initial_population = [
        individual.copy() for individual in population
    ]

    fitness_values = [
        fitness(vehicles, individual)
        for individual in population
    ]

    # Simpan salinan solusi terbaik sejak populasi awal.
    best_index = fitness_values.index(max(fitness_values))
    best_individual = population[best_index].copy()
    best_objective = fitness_values[best_index]

    # Iterasi 0 adalah populasi awal.
    history = [{
        "iteration": 0,
        "maximum": max(fitness_values),
        "average": sum(fitness_values) / population_size,
    }]

    for generation in range(1, generations + 1):
        new_population = []

        for _ in range(population_size):
            parent_a = select_parent(population, fitness_values, rng)
            parent_b = select_parent(population, fitness_values, rng)

            child = crossover(parent_a, parent_b, rng)

            if rng.random() < mutation_rate:
                child = mutate(child, ship, rng)

            if not is_valid_state(vehicles, child, ship):
                child = generate_genome(vehicles, ship, rng)

            new_population.append(child)

        population = new_population

        fitness_values = [
            fitness(vehicles, individual)
            for individual in population
        ]

        best_index = fitness_values.index(max(fitness_values))
        if fitness_values[best_index] > best_objective:
            best_individual = population[best_index].copy()
            best_objective = fitness_values[best_index]

        history.append({
            "iteration": generation,
            "maximum": max(fitness_values),
            "average": sum(fitness_values) / population_size,
        })

    duration = perf_counter() - start

    return {
        "initial_population": initial_population,
        "final_population": population,
        "best_individual": best_individual,
        "best_objective": best_objective,
        "history": history,
        "population_size": population_size,
        "iterations": generations,
        "mutation_rate": mutation_rate,
        "duration_seconds": duration,
    }
