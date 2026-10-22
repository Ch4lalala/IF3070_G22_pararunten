import matplotlib.pyplot as plt
import json
import random
from pathlib import Path

from src.algorithm.hill_climbing import hill_climbing
from src.init.models import Dimension, Vehicle, Ship
from src.init.initialization import generate_initial_state
from src.init.constraints import is_valid_state
from src.init.objective import calculate_objective


def load_dataset(filename):
    """Membaca JSON menjadi objek kendaraan dan kapal."""
    with open(filename, "r", encoding="utf-8-sig") as file:
        data = json.load(file)

    ship_data = data["ship"]
    ship = Ship(
        dimensions=Dimension(
            w=ship_data["dimensions"]["w"],
            l=ship_data["dimensions"]["l"]
        ),
        max_capacity=ship_data["max_capacity"]
    )

    vehicles = []
    for item in data["vehicles"]:
        vehicle = Vehicle(
            id=item["id"],
            dimensions=Dimension(
                w=item["dimensions"]["w"],
                l=item["dimensions"]["l"]
            ),
            shipping_fee=item["shipping_fee"],
            weight=item["weight"],
            eta=item["eta"]
        )
        vehicles.append(vehicle)

    return vehicles, ship


def print_state(title, vehicles, positions, ship):
    """Menampilkan penempatan kendaraan dan ringkasan state."""
    print("\n" + title)
    total_weight = 0

    for i in range(len(vehicles)):
        vehicle = vehicles[i]
        position = positions[i]

        if position is None:
            print(f"{vehicle.id}: tidak dimuat")
        else:
            total_weight += vehicle.weight
            print(
                f"{vehicle.id}: ({position.x}, {position.y}), "
                f"orientasi={position.orientation.value}"
            )

    print("Objective:", calculate_objective(vehicles, positions))
    print(f"Total berat: {total_weight} / {ship.max_capacity}")
    print("Valid:", is_valid_state(vehicles, positions, ship))

def plot_objective(results):
    """Menampilkan grafik perkembangan objective dari tiga percobaan."""

    plt.figure(figsize=(10, 5))

    for nomor, result in enumerate(results, start=1):
        # History berisi objective awal dan setelah setiap langkah.
        history = result["history"]

        # Iterasi 0 menunjukkan nilai objective pada state awal.
        iterations = range(len(history))

        # Setiap percobaan ditampilkan sebagai satu garis.
        plt.plot(
            iterations,
            history,
            label=f"Percobaan {nomor} (seed {result['seed']})"
        )

    plt.title("Hill-Climbing: Objective terhadap Iterasi")
    plt.xlabel("Iterasi")
    plt.ylabel("Total Shipping Fee (juta rupiah)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

def main():
    dataset = Path(__file__).resolve().parent / "data" / "medium.json"
    vehicles, ship = load_dataset(dataset)

    seeds = [42, 43, 44]
    max_sideways = 100
    results = []

    for experiment, seed in enumerate(seeds, start=1):
        # Buat RNG dan initial state baru untuk setiap percobaan.
        rng = random.Random(seed)
        positions = generate_initial_state(vehicles, ship, rng)
        original_positions = list(positions)

        assert is_valid_state(
            vehicles, positions, ship
        ), "State awal tidak valid."

        result = hill_climbing(
            vehicles, positions, ship, rng, max_sideways=max_sideways
        )

        # Periksa hasil setiap percobaan.
        assert positions == original_positions, "State awal ikut berubah."

        assert is_valid_state(
            vehicles, result["final_state"], ship
        ), "State akhir tidak valid."

        assert result["final_objective"] == calculate_objective(
            vehicles, result["final_state"]
        ), "Objective akhir tidak sesuai."

        history = result["history"]

        assert history[0] == calculate_objective(
            vehicles, original_positions
        ), "History awal tidak sesuai."

        assert history[-1] == result["final_objective"], \
            "History akhir tidak sesuai."

        assert len(history) == result["iterations"] + 1, \
            "Jumlah history tidak sesuai."

        for i in range(1, len(history)):
            assert history[i] >= history[i - 1], "Objective HC menurun."

        # Simpan seed bersama hasilnya untuk laporan dan grafik.
        result["seed"] = seed
        results.append(result)

        print(f"\nPERCOBAAN {experiment} — SEED {seed}")
        print_state("STATE AWAL", vehicles, positions, ship)
        print_state("STATE AKHIR", vehicles, result["final_state"], ship)

        print("Jumlah langkah:", result["iterations"])
        print("Total sideways:", result["total_sideways"])
        print(f"Durasi: {result['duration']:.4f} detik")
        print("Alasan berhenti:", result["stop_reason"])

    print("\nRINGKASAN TIGA PERCOBAAN")

    for result in results:
        print(
            f"Seed {result['seed']} | "
            f"Awal: {result['history'][0]} | "
            f"Akhir: {result['final_objective']} | "
            f"Langkah: {result['iterations']} | "
            f"Waktu: {result['duration']:.4f} detik"
        )
    
    plot_objective(results)

    return results


if __name__ == "__main__":
    main()