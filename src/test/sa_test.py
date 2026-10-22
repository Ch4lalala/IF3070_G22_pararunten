import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.algorithms.simulated_annealing import simulated_annealing
from src.init.models import Dimension, Ship, Vehicle


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUTPUT = ROOT / "outputs" / "sa"
SEEDS = [11, 22, 33]


def load_dataset(path):
    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    ship = Ship(
        dimensions=Dimension(**data["ship"]["dimensions"]),
        max_capacity=data["ship"]["max_capacity"],
    )
    vehicles = [
        Vehicle(
            id=v["id"],
            dimensions=Dimension(**v["dimensions"]),
            shipping_fee=v["shipping_fee"],
            weight=v["weight"],
            eta=v["eta"],
        )
        for v in data["vehicles"]
    ]
    return vehicles, ship


def save_state(path, vehicles, positions, value):
    with open(path, "w", encoding="utf-8") as file:
        file.write(f"Objective value: {value}\n\n")
        for vehicle, position in zip(vehicles, positions):
            file.write(f"{vehicle.id}: {position}\n")


def save_plots(result, folder):
    plt.figure(figsize=(8, 4))
    plt.plot(result["history"])
    plt.xlabel("Iteration")
    plt.ylabel("Objective Value")
    plt.title("Objective Value vs Iteration")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(folder / "objective_plot.png", dpi=150)
    plt.close()

    probabilities = [
        (i, p)
        for i, p in enumerate(result["probs"], start=1)
        if p is not None
    ]

    plt.figure(figsize=(8, 4))
    if probabilities:
        x, y = zip(*probabilities)
        plt.plot(x, y, ".", markersize=3)

    plt.xlabel("Iteration")
    plt.ylabel("Acceptance Probability")
    plt.title("Acceptance Probability vs Iteration")
    plt.ylim(-0.05, 1.05)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(folder / "probability_plot.png", dpi=150)
    plt.close()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = []

    for dataset_path in sorted(DATA.glob("*.json")):
        if dataset_path.stem not in ["small", "medium", "large"]:
            continue

        vehicles, ship = load_dataset(dataset_path)

        for seed in SEEDS:
            folder = OUTPUT / dataset_path.stem / f"run_{seed}"
            folder.mkdir(parents=True, exist_ok=True)

            result = simulated_annealing(
                vehicles,
                ship,
                T0=100.0,
                alpha=0.999,
                T_min=0.1,
                max_iter=5000,
                seed=seed,
            )

            save_state(
                folder / "initial_state.txt",
                vehicles,
                result["initial_state"],
                result["initial_value"],
            )
            save_state(
                folder / "final_state.txt",
                vehicles,
                result["final_state"],
                result["final_value"],
            )
            save_plots(result, folder)

            summary.append({
                "case": dataset_path.stem,
                "seed": seed,
                "initial_value": result["initial_value"],
                "final_value": result["final_value"],
                "best_value": result["best_value"],
                "iterations": result["iterations"],
                "duration_seconds": round(result["duration"], 4),
                "failed_neighbor": result["failed_neighbor"],
                "rejected_moves": result["rejected_moves"],
                "worse_accepted": result["worse_accepted"],
            })

            print(
                f"{dataset_path.stem} | seed={seed} | "
                f"initial={result['initial_value']} | "
                f"final={result['final_value']} | "
                f"best={result['best_value']} | "
                f"time={result['duration']:.2f}s"
            )

    with (OUTPUT / "summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=summary[0].keys())
        writer.writeheader()
        writer.writerows(summary)

    print(f"\nResults saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
