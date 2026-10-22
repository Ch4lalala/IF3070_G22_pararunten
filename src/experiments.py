"""Menjalankan algoritma dan eksperimen tanpa bergantung pada dashboard."""

import random
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.algorithm.hill_climbing import hill_climbing
from src.algorithm.simulated_annealing import simulated_annealing
from src.algorithm.genetic_algorithm import run_genetic_algorithm
from src.init.constraints import is_valid_state
from src.init.initialization import generate_initial_state
from src.init.objective import calculate_objective
from src.result_io import (
    dataset_digest, make_models, normalize_result, save_checkpoint, save_run,
    write_json,
)

# Folder penyimpanan hasil untuk masing-masing algoritma.
OUTPUT_FOLDERS = {"HC": "hill_climbing", "SA": "simulated_annealing", "GA": "genetic_algorithm"}

def parse_variations(text, label):
    """Membaca tepat tiga integer berbeda dan positif dari pengaturan GA."""
    try:
        values = [int(item.strip()) for item in text.split(",")]
    except ValueError as error:
        raise ValueError(f"{label} harus berupa integer, dipisahkan koma.") from error
    if len(values) != 3 or len(set(values)) != 3 or any(value < 1 for value in values):
        raise ValueError(f"{label} harus memuat tiga nilai berbeda, minimal 1.")
    return values

def default_variations(control):
    """Membuat tiga variasi awal yang tetap berbeda untuk nilai kontrol kecil."""
    values = [max(1, control // 2), control, control * 2]
    return values if len(set(values)) == 3 else [1, 2, 3]

def build_plan(algorithm, seeds, parameters):
    """HC = tiga run; GA = dua kelompok × tiga konfigurasi × tiga seed."""
    if len(seeds) != 3 or len(set(seeds)) != 3 or any(s < 0 for s in seeds):
        raise ValueError("Eksperimen membutuhkan tepat tiga seed berbeda, minimal 0.")
    if algorithm == "HC":
        if type(parameters["max_sideways"]) is not int or parameters["max_sideways"] < 0:
            raise ValueError("Maksimum sideways harus integer minimal 0.")
        configs = [("", dict(parameters))]
    elif algorithm == "SA":
        T0, alpha, T_min = (parameters[key] for key in ("T0", "alpha", "T_min"))
        if not all(math.isfinite(value) for value in (T0, alpha, T_min)):
            raise ValueError("Parameter suhu harus bilangan berhingga.")
        if T0 <= 0 or not 0 < alpha < 1 or T_min <= 0:
            raise ValueError("T0 dan T_min harus positif; alpha harus antara 0 dan 1.")
        if type(parameters["max_iter"]) is not int or parameters["max_iter"] < 0:
            raise ValueError("Batas iterasi SA harus integer minimal 0.")
        configs = [("", dict(parameters))]
    elif algorithm == "GA":
        population = parameters["population_size"]
        generations = parameters["generations"]
        if type(population) is not int or population < 1 or type(generations) is not int or generations < 1:
            raise ValueError("Kontrol populasi dan generasi harus integer positif.")
        if not 0 <= parameters["mutation_rate"] <= 1:
            raise ValueError("Peluang mutasi harus antara 0 dan 1.")
        generation_values = parameters["generation_values"]
        population_values = parameters["population_values"]
        for values, label in [(generation_values, "Variasi generasi"),
                              (population_values, "Variasi populasi")]:
            if len(values) != 3 or len(set(values)) != 3 or any(type(v) is not int or v < 1 for v in values):
                raise ValueError(f"{label} harus tiga integer positif berbeda.")
        configs = [("A", dict(parameters, generations=g)) for g in generation_values]
        configs += [("B", dict(parameters, population_size=p)) for p in population_values]
    else:
        raise ValueError("Algoritma ini belum tersedia.")
    jobs = []
    for group, params in configs:
        for seed in seeds:
            if algorithm == "GA":
                run_id = (f"{group}_pop-{params['population_size']}_"
                          f"iter-{params['generations']}_seed-{seed}")
            else:
                run_id = f"{algorithm}_seed-{seed}"
            jobs.append({"group": group, "seed": seed, "parameters": params.copy(),
                         "run_id": run_id})
    return jobs

def run_search(algorithm, dataset, seed, parameters, group=""):
    """Menjalankan satu pencarian dengan RNG tersendiri untuk seed tersebut."""
    vehicles, ship = make_models(dataset)
    rng = random.Random(seed)
    if algorithm == "HC":
        positions = generate_initial_state(vehicles, ship, rng)
        result = hill_climbing(vehicles, positions, ship, rng,
                               max_sideways=parameters["max_sideways"])
    elif algorithm == "SA":
        result = simulated_annealing(
            vehicles, ship, T0=parameters["T0"], alpha=parameters["alpha"],
            T_min=parameters["T_min"], max_iter=parameters["max_iter"], seed=seed,
        )
    elif algorithm == "GA":
        result = run_genetic_algorithm(
            vehicles, ship, parameters["population_size"],
            parameters["generations"], parameters["mutation_rate"], rng,
        )
    else:
        raise ValueError("Algoritma tidak dikenal: " + str(algorithm))
    result["seed"] = seed
    result["group"] = group
    record = normalize_result(algorithm, result, vehicles)
    if not all(is_valid_state(vehicles, record[field], ship)
               for field in ["initial_state", "final_state"]):
        raise ValueError("Algoritma menghasilkan state awal/akhir tidak valid.")
    if calculate_objective(vehicles, record["final_state"]) != record["objective"]:
        raise ValueError("Objective hasil tidak cocok dengan state yang disimpan.")
    if len(record["history"]) != record["iterations"] + 1:
        raise ValueError("Jumlah history tidak cocok dengan jumlah iterasi.")
    if algorithm == "SA":
        for key in ("probs", "temperatures", "deltas"):
            if len(result[key]) != result["iterations"]:
                raise ValueError("Panjang riwayat SA tidak sesuai: " + key)
        if len(result["local_optimum_history"]) != len(result["history"]):
            raise ValueError("Riwayat local optimum tidak sesuai dengan iterasi.")
        if (not is_valid_state(vehicles, result["best_state"], ship) or
                calculate_objective(vehicles, result["best_state"]) != result["best_objective"]):
            raise ValueError("Solusi terbaik SA tidak cocok dengan nilainya.")
    return record

def execute_experiment(dataset, algorithm, seeds, parameters, output_root, on_update=None):
    """Menjalankan seluruh rencana; setiap hasil langsung dicatat ke disk."""
    jobs = build_plan(algorithm, seeds, parameters)
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    source = f"{algorithm.lower()}_" + now.strftime("%Y%m%d_%H%M%S_%f")
    folder = Path(output_root) / OUTPUT_FOLDERS[algorithm] / source
    folder.mkdir(parents=True, exist_ok=False)
    bundle = {
        "dataset": dataset, "algorithm": algorithm, "source": source,
        "folder": str(folder.resolve()), "created_at": now.isoformat(),
        "dataset_digest": dataset_digest(dataset), "runs": [], "plan": jobs,
        "expected_runs": len(jobs), "status": "running",
        "parameters": dict(parameters), "seeds": list(seeds),
    }
    write_json(folder / "dataset.json", dataset)
    save_checkpoint(bundle)

    def notify(message):
        if on_update is not None:
            on_update(bundle, message)

    try:
        notify("Sesi dibuat. Menyiapkan percobaan pertama.")
        for number, job in enumerate(jobs, 1):
            notify(f"Menjalankan {number}/{len(jobs)} · {job['run_id']}")
            record = run_search(algorithm, dataset, job["seed"], job["parameters"], job["group"])
            record["run_id"] = job["run_id"]
            record["raw"]["run_id"] = job["run_id"]
            record["raw"]["algorithm"] = algorithm
            save_run(record, folder / job["run_id"])
            bundle["runs"].append(record)
            save_checkpoint(bundle)
            notify(f"Tersimpan {number}/{len(jobs)} · {job['run_id']}")
        bundle["status"] = "complete"
        save_checkpoint(bundle)
        notify(f"Selesai. {len(jobs)} percobaan sudah tersimpan.")
    except BaseException as error:
        # Termasuk interupsi: hasil run yang sudah selesai tetap tersedia.
        bundle["status"] = "failed"
        bundle["error"] = str(error) or type(error).__name__
        save_checkpoint(bundle)
        raise
    return bundle
