"""Pengujian HC, SA, dan GA tanpa dashboard atau library grafik."""

import importlib
import json
import math
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import Mock, patch

from src.algorithm.hill_climbing import get_neighbors, hill_climbing
from src.algorithm.simulated_annealing import is_local_optimum, simulated_annealing
from src.algorithm.genetic_algorithm import (
    crossover, mutate, run_genetic_algorithm, select_parent,
)
from src.init.models import Dimension, Orientation, Position, Ship, Vehicle
from src.init.initialization import generate_initial_state
from src.init.operations import move, rotate, swap

ROOT = Path(__file__).resolve().parents[1]
H = Orientation.HORIZONTAL
V = Orientation.VERTICAL


def objective(vehicles, positions):
    """Hitung ulang secara terpisah dari fungsi objective milik program."""
    return sum(v.shipping_fee for v, p in zip(vehicles, positions) if p is not None)


def valid_state(vehicles, positions, ship):
    """Periksa setiap sel grid agar tidak hanya mengandalkan validator program."""
    if len(vehicles) != len(positions):
        return False
    occupied = set()
    weight = 0
    for vehicle, position in zip(vehicles, positions):
        if position is None:
            continue
        if type(position.x) is not int or type(position.y) is not int:
            return False
        if position.orientation not in (H, V):
            return False
        w, length = vehicle.dimensions.w, vehicle.dimensions.l
        if position.orientation == V:
            w, length = length, w
        for x in range(position.x, position.x + w):
            for y in range(position.y, position.y + length):
                cell = (x, y)
                if not (0 <= x < ship.dimensions.w and 0 <= y < ship.dimensions.l):
                    return False
                if cell in occupied:
                    return False
                occupied.add(cell)
        weight += vehicle.weight
    return weight <= ship.max_capacity


def load_small():
    """Baca dataset asli tanpa mengimpor modul visualisasi."""
    data = json.loads((ROOT / "data/small.json").read_text(encoding="utf-8-sig"))
    ship = Ship(Dimension(**data["ship"]["dimensions"]), data["ship"]["max_capacity"])
    vehicles = [
        Vehicle(item["id"], Dimension(**item["dimensions"]),
                item["shipping_fee"], item["weight"], item["eta"])
        for item in data["vehicles"]
    ]
    return vehicles, ship


def vehicle(identifier, fee=10, w=1, length=1, weight=1):
    return Vehicle(identifier, Dimension(w, length), fee, weight, 1)


class AlgorithmTests(unittest.TestCase):
    def check_state(self, vehicles, state, ship):
        self.assertTrue(valid_state(vehicles, state, ship), "Susunan tidak valid.")

    def check_hc(self, vehicles, ship, result):
        self.check_state(vehicles, result["initial_state"], ship)
        self.check_state(vehicles, result["final_state"], ship)
        self.assertEqual(result["final_objective"], objective(vehicles, result["final_state"]))
        self.assertEqual(result["history"][0], objective(vehicles, result["initial_state"]))
        self.assertEqual(result["history"][-1], result["final_objective"])
        self.assertEqual(len(result["history"]), result["iterations"] + 1)
        self.assertTrue(all(a <= b for a, b in zip(result["history"], result["history"][1:])))
        equal_steps = sum(a == b for a, b in zip(result["history"], result["history"][1:]))
        self.assertEqual(result["total_sideways"], equal_steps)
        self.assertTrue(math.isfinite(result["duration"]) and result["duration"] >= 0)

    def check_sa(self, vehicles, ship, result):
        for name in ("initial_state", "final_state", "best_state"):
            self.check_state(vehicles, result[name], ship)
        for prefix in ("initial", "final", "best"):
            self.assertEqual(result[prefix + "_objective"],
                             objective(vehicles, result[prefix + "_state"]))
        history = result["history"]
        self.assertEqual(len(history), result["iterations"] + 1)
        self.assertEqual(history[0], result["initial_objective"])
        self.assertEqual(history[-1], result["final_objective"])
        self.assertEqual(max(history), result["best_objective"])
        for field in ("probs", "temperatures", "deltas"):
            self.assertEqual(len(result[field]), result["iterations"])

        rejected = worse = failed = 0
        for i, (probability, delta, temperature) in enumerate(zip(
                result["probs"], result["deltas"], result["temperatures"])):
            self.assertGreater(temperature, 0)
            self.assertAlmostEqual(temperature,
                                   result["parameters"]["T0"] * result["parameters"]["alpha"] ** (i + 1))
            if probability is None:
                failed += 1
                self.assertIsNone(delta)
                self.assertEqual(history[i + 1], history[i])
                continue
            expected = 1.0 if delta >= 0 else math.exp(delta / temperature)
            self.assertAlmostEqual(probability, expected)
            self.assertTrue(0 <= probability <= 1)
            if delta >= 0:
                self.assertAlmostEqual(history[i + 1] - history[i], delta)
            elif history[i + 1] < history[i]:
                worse += 1
                self.assertAlmostEqual(history[i + 1] - history[i], delta)
            else:
                rejected += 1
                self.assertEqual(history[i + 1], history[i])
        self.assertEqual(failed, result["failed_neighbor"])
        self.assertEqual(rejected, result["rejected_moves"])
        self.assertEqual(worse, result["worse_accepted"])
        flags = result["local_optimum_history"]
        self.assertEqual(len(flags), len(history))
        entries = int(flags[0]) + sum(not a and b for a, b in zip(flags, flags[1:]))
        self.assertEqual(result["local_optimum_count"], entries)
        if vehicles:
            self.assertEqual(flags[-1], is_local_optimum(vehicles, result["final_state"], ship))
        self.assertTrue(math.isfinite(result["duration"]) and result["duration"] >= 0)

    def check_ga(self, vehicles, ship, result):
        size = result["population_size"]
        for name in ("initial_population", "final_population"):
            self.assertEqual(len(result[name]), size)
            for state in result[name]:
                self.check_state(vehicles, state, ship)
        self.check_state(vehicles, result["best_individual"], ship)
        self.assertEqual(result["best_objective"], objective(vehicles, result["best_individual"]))
        history = result["history"]
        self.assertEqual(len(history), result["iterations"] + 1)
        self.assertEqual([row["iteration"] for row in history], list(range(len(history))))
        self.assertEqual(result["best_objective"], max(row["maximum"] for row in history))
        for row in history:
            self.assertLessEqual(row["average"], row["maximum"])
        for index, name in ((0, "initial_population"), (-1, "final_population")):
            values = [objective(vehicles, state) for state in result[name]]
            self.assertEqual(history[index]["maximum"], max(values))
            self.assertAlmostEqual(history[index]["average"], sum(values) / size)
        self.assertTrue(math.isfinite(result["duration_seconds"]) and result["duration_seconds"] >= 0)

    def test_terminal_import_without_dashboard(self):
        """Runner terminal bisa dimuat tanpa Streamlit atau Plotly."""
        importlib.import_module("main")
        self.assertNotIn("streamlit", sys.modules)
        self.assertNotIn("plotly", sys.modules)

    def test_initialization_three_seeds(self):
        vehicles, ship = load_small()
        for seed in (42, 43, 44):
            with self.subTest(seed=seed):
                state = generate_initial_state(vehicles, ship, random.Random(seed))
                self.check_state(vehicles, state, ship)
                self.assertIsNone(state[6])  # V007 terlalu besar.
                self.assertIsNone(state[7])  # V008 terlalu berat.

    def test_hc_neighbors_valid_and_original_unchanged(self):
        vehicles = [vehicle("A", 10, 2, 1), vehicle("B", 20, 1, 2)]
        ship = Ship(Dimension(3, 3), 2)
        initial = [Position(0, 0, H), None]
        neighbors = get_neighbors(vehicles, initial, ship)
        self.assertEqual(initial, [Position(0, 0, H), None])
        self.assertTrue(neighbors)
        for state in neighbors:
            self.assertNotEqual(state, initial)
            self.check_state(vehicles, state, ship)
            self.assertGreaterEqual(sum(p is not None for p in state), 1)
        self.assertIn([Position(0, 0, V), None], neighbors)  # Rotate.
        self.assertIn([None, Position(0, 0, H)], neighbors)  # Swap dengan luar.
        self.assertIn([Position(1, 0, H), None], neighbors)  # Move.

    def test_hc_small_three_seeds(self):
        vehicles, ship = load_small()
        for seed in (42, 43, 44):
            with self.subTest(seed=seed):
                rng = random.Random(seed)
                initial = generate_initial_state(vehicles, ship, rng)
                original = initial.copy()
                result = hill_climbing(vehicles=vehicles, ship=ship, rng=rng,
                                       max_sideways=5, initial=initial)
                self.assertEqual(initial, original)
                self.check_hc(vehicles, ship, result)

    def test_hc_sideways_limit_and_zero(self):
        vehicles = [vehicle("A")]
        ship = Ship(Dimension(2, 1), 1)
        for limit in (0, 3):
            with self.subTest(limit=limit):
                result = hill_climbing(vehicles=vehicles, ship=ship,
                                       rng=random.Random(42), max_sideways=limit,
                                       initial=[Position(0, 0, H)])
                self.assertEqual(result["iterations"], limit)
                self.assertEqual(result["total_sideways"], limit)
                self.assertEqual(result["stop_reason"], "sideways_limit")
                self.check_hc(vehicles, ship, result)

    def test_terminal_hc_initializes_once_and_uses_current_signature(self):
        """Runner HC membuat initial state sekali, di dalam timer algoritma."""
        runner = importlib.import_module("main")
        dataset = json.loads((ROOT / "data/small.json").read_text(encoding="utf-8-sig"))
        vehicles, ship = load_small()
        with patch("src.algorithm.hill_climbing.generate_initial_state",
                   wraps=generate_initial_state) as initialize:
            record = runner.run_search("HC", dataset, 42, {"max_sideways": 2})
        initialize.assert_called_once()
        expected = generate_initial_state(vehicles, ship, random.Random(42))
        self.assertEqual(record["initial_state"], expected)
        self.assertEqual(record["raw"]["duration_scope"], "initialization_and_search")
        self.assertEqual(record["raw"]["sideways_limit_scope"], "consecutive")
        self.check_hc(vehicles, ship, record["raw"])

    def test_hc_sideways_resets_after_improvement(self):
        vehicles = [vehicle("A", 10), vehicle("B", 20)]
        ship = Ship(Dimension(4, 1), 2)
        states = [
            [Position(0, 0, H), None],
            [Position(1, 0, H), None],
            [Position(1, 0, H), Position(2, 0, H)],
            [Position(0, 0, H), Position(2, 0, H)],
            [Position(0, 0, H), Position(3, 0, H)],
        ]
        with patch("src.algorithm.hill_climbing.get_neighbors",
                   side_effect=[[state] for state in states[1:]]):
            result = hill_climbing(vehicles=vehicles, ship=ship, rng=random.Random(42),
                                   max_sideways=2, initial=states[0])
        self.assertEqual(result["history"], [10, 10, 30, 30, 30])
        self.assertEqual(result["total_sideways"], 3)
        self.assertEqual(result["sideways_limit_scope"], "consecutive")
        self.check_hc(vehicles, ship, result)

    def test_hc_rejects_lower_objective(self):
        vehicles = [vehicle("A", 10), vehicle("B", 20)]
        ship = Ship(Dimension(1, 1), 1)
        initial = [None, Position(0, 0, H)]
        lower = [Position(0, 0, H), None]
        with patch("src.algorithm.hill_climbing.get_neighbors", return_value=[lower]):
            result = hill_climbing(vehicles=vehicles, ship=ship,
                                   rng=random.Random(42), initial=initial)
        self.assertEqual(result["final_state"], initial)
        self.assertEqual(result["iterations"], 0)
        self.assertEqual(result["stop_reason"], "local_optimum")

    def test_hc_empty_and_oversized(self):
        ship = Ship(Dimension(1, 1), 1)
        for vehicles in ([], [vehicle("A", w=2, length=2)]):
            with self.subTest(vehicles=vehicles):
                result = hill_climbing(vehicles=vehicles, ship=ship,
                                       rng=random.Random(42), initial=[None] * len(vehicles))
                self.assertEqual(result["stop_reason"], "no_valid_neighbor")
                self.check_hc(vehicles, ship, result)

    def test_sa_small_three_seeds(self):
        vehicles, ship = load_small()
        for seed in (42, 43, 44):
            with self.subTest(seed=seed):
                result = simulated_annealing(vehicles, ship, max_iter=60, seed=seed)
                self.check_sa(vehicles, ship, result)
                self.assertIsNone(result["final_state"][6])
                self.assertIsNone(result["final_state"][7])

    def test_sa_can_accept_worse_and_counts_local_optimum_entries(self):
        vehicles = [vehicle("A", 10, 1, 2)]
        ship = Ship(Dimension(1, 2), 1)
        initial = [Position(0, 0, H)]
        rng = Mock()
        rng.randrange.return_value = 0
        rng.choice.side_effect = lambda values: values[0]
        rng.random.return_value = 0.0
        with patch("src.algorithm.simulated_annealing.random.Random", return_value=rng):
            result = simulated_annealing(vehicles, ship, initial=initial, max_iter=3)
        self.assertEqual(result["history"], [10, 0, 10, 0])
        self.assertEqual(result["worse_accepted"], 2)
        self.assertEqual(result["local_optimum_history"], [True, False, True, False])
        self.assertEqual(result["local_optimum_count"], 2)
        self.assertEqual(initial, [Position(0, 0, H)])
        self.check_sa(vehicles, ship, result)

    def test_sa_can_reject_worse(self):
        vehicles = [vehicle("A", 10, 1, 2)]
        ship = Ship(Dimension(1, 2), 1)
        rng = Mock()
        rng.randrange.return_value = 0
        rng.choice.side_effect = lambda values: values[0]
        rng.random.side_effect = [0.0, 0.999]  # Pilih remove, lalu tolak kandidat.
        with patch("src.algorithm.simulated_annealing.random.Random", return_value=rng):
            result = simulated_annealing(vehicles, ship, initial=[Position(0, 0, H)],
                                         T0=1, alpha=0.5, max_iter=1)
        self.assertEqual(result["history"], [10, 10])
        self.assertEqual(result["rejected_moves"], 1)
        self.assertEqual(result["local_optimum_count"], 1)
        self.check_sa(vehicles, ship, result)

    def test_sa_stop_reasons(self):
        vehicles = [vehicle("A")]
        ship = Ship(Dimension(1, 1), 1)
        cases = [
            (vehicles, {"max_iter": 0}, "iteration_limit"),
            (vehicles, {"T0": 1, "alpha": 0.5, "T_min": 0.6}, "temperature_limit"),
            ([], {}, "no_vehicles"),
        ]
        for items, parameters, reason in cases:
            with self.subTest(reason=reason):
                result = simulated_annealing(items, ship, **parameters)
                self.assertEqual(result["iterations"], 0)
                self.assertEqual(result["stop_reason"], reason)
                self.check_sa(items, ship, result)

    def test_sa_failed_neighbor_is_not_counted_as_new_local_optimum(self):
        vehicles = [vehicle("A", w=2, length=2)]
        ship = Ship(Dimension(1, 1), 1)
        result = simulated_annealing(vehicles, ship, max_iter=4)
        self.assertEqual(result["probs"], [None] * 4)
        self.assertEqual(result["failed_neighbor"], 4)
        self.assertEqual(result["local_optimum_count"], 1)
        self.check_sa(vehicles, ship, result)

    def test_sa_invalid_inputs(self):
        vehicles = [vehicle("A")]
        ship = Ship(Dimension(1, 1), 1)
        for parameters in ({"T0": 0}, {"alpha": 1}, {"T_min": 0},
                           {"max_iter": -1}, {"max_iter": 1.5},
                           {"initial": [Position(1, 0, H)]}):
            with self.subTest(parameters=parameters):
                with self.assertRaises(ValueError):
                    simulated_annealing(vehicles, ship, **parameters)

    def test_local_optimum_matches_exhaustive_neighbors(self):
        """Bandingkan pemeriksa cepat dengan seluruh operasi pada kasus kecil."""
        from itertools import product
        ship = Ship(Dimension(2, 2), 2)
        positions = [None] + [Position(x, y, o) for x in range(2)
                             for y in range(2) for o in (H, V)]
        for fees in ((10, 20), (-10, 20)):
            vehicles = [vehicle("A", fees[0]), vehicle("B", fees[1], 1, 2)]
            for entries in product(positions, repeat=2):
                state = list(entries)
                if not valid_state(vehicles, state, ship):
                    continue
                neighbors = []
                for i, position in enumerate(state):
                    orientations = (H, V) if position is None else (position.orientation,)
                    neighbors.append(move(state, i, None))
                    neighbors.append(rotate(state, i))
                    for x in range(2):
                        for y in range(2):
                            for orientation in orientations:
                                neighbors.append(move(state, i, Position(x, y, orientation)))
                neighbors.append(swap(state, 0, 1))
                better_exists = any(valid_state(vehicles, n, ship) and
                                    objective(vehicles, n) > objective(vehicles, state)
                                    for n in neighbors)
                with self.subTest(fees=fees, state=state):
                    self.assertEqual(is_local_optimum(vehicles, state, ship), not better_exists)

    def test_ga_matrix_six_configurations_three_seeds(self):
        """18 run singkat: A mengubah generasi, B mengubah jumlah populasi."""
        vehicles, ship = load_small()
        configurations = [("A", 4, g) for g in (2, 4, 6)]
        configurations += [("B", p, 4) for p in (2, 4, 6)]
        for group, population, generations in configurations:
            for seed in (42, 43, 44):
                with self.subTest(group=group, population=population,
                                  generations=generations, seed=seed):
                    result = run_genetic_algorithm(vehicles, ship, population, generations,
                                                   0.1, random.Random(seed))
                    self.check_ga(vehicles, ship, result)
                    self.assertIsNone(result["best_individual"][6])
                    self.assertIsNone(result["best_individual"][7])

    def test_ga_zero_generations_and_full_mutation(self):
        vehicles, ship = load_small()
        for generations, mutation in ((0, 0), (3, 1)):
            with self.subTest(generations=generations, mutation=mutation):
                result = run_genetic_algorithm(vehicles, ship, 3, generations,
                                               mutation, random.Random(42))
                self.check_ga(vehicles, ship, result)

    def test_ga_empty_vehicles_and_zero_fitness(self):
        ship = Ship(Dimension(2, 2), 2)
        for vehicles in ([], [vehicle("A", 0)]):
            with self.subTest(vehicles=vehicles):
                result = run_genetic_algorithm(vehicles, ship, 3, 3, 1, random.Random(42))
                self.assertEqual(result["best_objective"], 0)
                self.check_ga(vehicles, ship, result)
        parents = [[None], [Position(0, 0, H)]]
        self.assertIn(select_parent(parents, [0, 0], random.Random(42)), parents)

    def test_ga_crossover_and_mutation_do_not_change_parents(self):
        ship = Ship(Dimension(2, 2), 2)
        a = [Position(0, 0, H), None]
        b = [None, Position(1, 1, V)]
        original_a, original_b = a.copy(), b.copy()
        child = crossover(a, b, random.Random(42))
        self.assertEqual(len(child), len(a))
        self.assertIsNot(child, a)
        for seed in range(12):
            mutate(a, ship, random.Random(seed))  # Mutasi mentah boleh belum valid.
        self.assertEqual(a, original_a)
        self.assertEqual(b, original_b)
        self.assertEqual(crossover([], [], random.Random(42)), [])

    def test_ga_invalid_parameters(self):
        ship = Ship(Dimension(1, 1), 1)
        for population, generations, mutation in ((0, 1, 0.1), (1, -1, 0.1),
                                                   (1, 1, -0.1), (1, 1, 1.1)):
            with self.subTest(parameters=(population, generations, mutation)):
                with self.assertRaises(ValueError):
                    run_genetic_algorithm([], ship, population, generations,
                                          mutation, random.Random(42))

    def test_same_seed_repeats_results_for_all_algorithms(self):
        vehicles = [vehicle("A", 10), vehicle("B", 20)]
        ship = Ship(Dimension(2, 2), 2)
        runners = {
            "HC": (lambda: hill_climbing(vehicles=vehicles, ship=ship,
                                         rng=random.Random(42), max_sideways=3,
                                         initial=[None, None]), "duration"),
            "SA": (lambda: simulated_annealing(vehicles, ship, seed=42, max_iter=20), "duration"),
            "GA": (lambda: run_genetic_algorithm(vehicles, ship, 3, 4, 0.1,
                                                 random.Random(42)), "duration_seconds"),
        }
        for name, (run, duration_key) in runners.items():
            with self.subTest(algorithm=name):
                first, second = run(), run()
                first.pop(duration_key)
                second.pop(duration_key)
                self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)

