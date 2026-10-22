import csv
import json
import random
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..algorithms.genetic_algorithm import run_genetic_algorithm
from ..init.models import Dimension, Ship, Vehicle


def load_dataset(path):
    """Membaca data kapal dan kendaraan dari JSON."""
    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    ship = Ship(
        dimensions=Dimension(**data["ship"]["dimensions"]),
        max_capacity=data["ship"]["max_capacity"],
    )
    vehicles = []
    for item in data["vehicles"]:
        vehicle = Vehicle(
            id=item["id"],
            dimensions=Dimension(**item["dimensions"]),
            shipping_fee=item["shipping_fee"],
            weight=item["weight"],
            eta=item["eta"],
        )
        vehicles.append(vehicle)

    return vehicles, ship, data


def json_value(value):
    """Mengubah objek model menjadi data yang bisa disimpan dalam JSON."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError("Objek tidak bisa disimpan sebagai JSON.")


def plot_history(history, path):
    """Membuat dua garis: maksimum dan rata-rata setiap generasi."""
    iterations = [row["iteration"] for row in history]
    maximum = [row["maximum"] for row in history]
    average = [row["average"] for row in history]

    plt.figure(figsize=(8, 4))
    plt.plot(iterations, maximum, label="Maksimum")
    plt.plot(iterations, average, label="Rata-rata")
    plt.xlabel("Iterasi (generasi)")
    plt.ylabel("Nilai objective")
    plt.title("Perkembangan Objective Genetic Algorithm")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def save_result(result, folder):
    """Menyimpan hasil satu run dalam JSON, CSV, dan PNG."""
    folder.mkdir(parents=True, exist_ok=False)

    with (folder / "run.json").open("w", encoding="utf-8") as file:
        json.dump(result, file, default=json_value, indent=2, allow_nan=False)

    with (folder / "history.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["iteration", "maximum", "average"])
        writer.writeheader()
        writer.writerows(result["history"])

    plot_history(result["history"], folder / "objective.png")


def run_experiments(dataset_path="data/small.json", output_dir="output/genetic_algorithm"):
    vehicles, ship, dataset = load_dataset(dataset_path)

    # (kelompok, jumlah populasi, jumlah iterasi)
    configurations = [
        ("A", 20, 50),
        ("A", 20, 100),
        ("A", 20, 200),
        ("B", 10, 100),
        ("B", 20, 100),
        ("B", 40, 100),
    ]
    seeds = [11, 22, 33]
    mutation_rate = 0.1

    # Folder baru untuk setiap sesi agar hasil lama tidak tertimpa.
    session = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = Path(output_dir) / session
    folder.mkdir(parents=True, exist_ok=False)
    with (folder / "dataset.json").open("w", encoding="utf-8") as file:
        json.dump(dataset, file, indent=2, allow_nan=False)

    summary = []
    for group, population, iterations in configurations:
        for seed in seeds:
            run_id = f"{group}_pop-{population}_iter-{iterations}_seed-{seed}"
            print("Menjalankan:", run_id, flush=True)

            result = run_genetic_algorithm(
                vehicles=vehicles,
                ship=ship,
                population_size=population,
                generations=iterations,
                mutation_rate=mutation_rate,
                rng=random.Random(seed),
            )
            result["seed"] = seed
            result["group"] = group
            result["run_id"] = run_id
            save_result(result, folder / run_id)

            summary.append([
                group, population, iterations, seed, mutation_rate,
                result["best_objective"], result["duration_seconds"],
            ])

    with (folder / "summary.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "group", "population_size", "iterations", "seed", "mutation_rate",
            "objective_final", "duration_seconds",
        ])
        writer.writerows(summary)

    print("Selesai. Hasil tersimpan di:", folder)
    return folder


if __name__ == "__main__":
    run_experiments()