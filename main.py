"""Menjalankan HC, SA, dan GA dari terminal serta menyimpan hasil ke output."""

import math
import random
from datetime import datetime
from inspect import Parameter, signature
from pathlib import Path
from zoneinfo import ZoneInfo

from src.algorithm.hill_climbing import hill_climbing
from src.algorithm.simulated_annealing import simulated_annealing
from src.algorithm.genetic_algorithm import run_genetic_algorithm
from src.init.constraints import is_valid_state
from src.init.initialization import generate_initial_state
from src.init.objective import calculate_objective
from src.result_io import (
    dataset_digest, load_json, make_models, normalize_result,
    save_checkpoint, save_run, write_json,
)

ROOT = Path(__file__).resolve().parent

# ================= PENGATURAN PROGRAM =================
# Pilihan: "hc", "sa", "ga", "all" (ketiganya), atau "both" (HC + GA).
ALGORITHM = "all"

# Nama dataset di folder data: "small", "medium", atau "large".
DATASET = "medium"

# Tiga seed berbeda untuk tiga pengulangan pada setiap konfigurasi.
SEEDS = [42, 43, 44]

# True untuk membuka jendela grafik setelah semua run selesai.
# PNG tetap disimpan ke output meskipun nilainya False.
SHOW_PLOT = False
# ======================================================


# Folder hasil untuk setiap algoritma.
OUTPUT_FOLDERS = {"HC": "hill_climbing", "SA": "simulated_annealing", "GA": "genetic_algorithm"}


# Fungsi pengatur percobaan.
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


def get_default_parameters(algorithm):
    """Ambil nilai bawaan dari definisi fungsi algoritma."""
    functions = {
        "HC": hill_climbing,
        "SA": simulated_annealing,
        "GA": run_genetic_algorithm,
    }
    if algorithm not in functions:
        raise ValueError("Algoritma tidak dikenal: " + str(algorithm))

    parameters = {}
    for name, parameter in signature(functions[algorithm]).parameters.items():
        # Data, RNG, dan seed disediakan oleh pengatur eksperimen.
        if name not in ("rng", "seed", "initial") and parameter.default is not Parameter.empty:
            parameters[name] = parameter.default
    return parameters


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


def execute_experiment(dataset, algorithm, seeds, parameters=None, output_root=None, on_update=None):
    """Jalankan eksperimen; gunakan default algoritma jika parameter tidak diberikan."""
    # Sumber nilai bawaan tetap ada di fungsi masing-masing algoritma.
    settings = get_default_parameters(algorithm)
    settings.update(parameters or {})

    if algorithm == "GA":
        # Tiga variasi untuk setiap kelompok sesuai Cakupan tugas besar.
        settings.setdefault("generation_values", default_variations(settings["generations"]))
        settings.setdefault("population_values", default_variations(settings["population_size"]))

    parameters = settings
    if output_root is None:
        output_root = ROOT / "output"
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


def load_dataset(filename):
    """Baca data kapal dan kendaraan dari JSON."""
    return make_models(load_json(filename))


def print_state(title, vehicles, positions, ship):
    """Tampilkan seluruh kendaraan, termasuk yang tidak dimuat."""
    print("\n" + title)
    weight = 0
    for vehicle, position in zip(vehicles, positions):
        if position is None:
            print(f"{vehicle.id}: tidak dimuat")
        else:
            weight += vehicle.weight
            print(f"{vehicle.id}: ({position.x}, {position.y}), "
                  f"orientasi={position.orientation.value}")
    print("Objective:", calculate_objective(vehicles, positions))
    print(f"Total berat: {weight} / {ship.max_capacity}")
    print("Valid:", is_valid_state(vehicles, positions, ship))


def describe_result(algorithm, result, vehicles):
    """Ambil state awal, hasil, objective, dan durasi sesuai algoritma."""
    if algorithm in ("hc", "sa"):
        return (result["initial_state"], result["final_state"],
                result["final_objective"], result["duration"])
    initial = max(result["initial_population"],
                  key=lambda state: calculate_objective(vehicles, state))
    return initial, result["best_individual"], result["best_objective"], result["duration_seconds"]


def print_result(algorithm, result, vehicles, ship, experiment):
    """Tampilkan hasil run dan statistik khusus masing-masing algoritma."""
    initial, final, value, duration = describe_result(algorithm, result, vehicles)
    print(f"\n{algorithm.upper()} - RUN {experiment} - SEED {result['seed']}")
    if algorithm == "ga":
        print_state("TERBAIK POPULASI AWAL", vehicles, initial, ship)
        print_state("TERBAIK SEPANJANG PENCARIAN", vehicles, final, ship)
        print("Kelompok:", result.get("group", ""))
        print("Jumlah populasi:", result["population_size"])
        print("Peluang mutasi:", result["mutation_rate"])
        print("Maksimum populasi terakhir:", result["history"][-1]["maximum"])
    else:
        print_state("STATE AWAL", vehicles, initial, ship)
        print_state("STATE AKHIR", vehicles, final, ship)
        print("Alasan berhenti:", result["stop_reason"])
        if algorithm == "hc":
            print("Batas sideways:", result["parameters"]["max_sideways"])
            print("Total sideways:", result["total_sideways"])
        else:
            print_state("STATE TERBAIK SA", vehicles, result["best_state"], ship)
            print("Objective terbaik:", result["best_objective"])
            print("Frekuensi local optimum:", result["local_optimum_count"])
            print("Langkah menurun diterima:", result["worse_accepted"])
            print("Kandidat ditolak:", result["rejected_moves"])
            print("Gagal mencari tetangga:", result["failed_neighbor"])
            print("Parameter suhu:", result["parameters"])
    print("Objective hasil:", value)
    print("Jumlah iterasi:", result["iterations"])
    print(f"Durasi: {duration:.4f} detik")


def plot_objective(results):
    """Opsional: buka jendela grafik; PNG sudah dibuat saat hasil disimpan."""
    import matplotlib.pyplot as plt

    for algorithm in ("hc", "sa"):
        records = [r for r in results if r["algorithm"] == algorithm]
        if not records:
            continue
        fig, ax = plt.subplots(figsize=(10, 4))
        for result in records:
            ax.plot(range(len(result["history"])), result["history"],
                    label=f"Seed {result['seed']}")
        ax.set(title=f"{algorithm.upper()}: Objective terhadap Iterasi",
               xlabel="Iterasi (0 = state awal)", ylabel="Shipping fee (juta rupiah)")
        ax.grid(alpha=.3)
        ax.legend()
        fig.tight_layout()
        if algorithm == "sa":
            fig, ax = plt.subplots(figsize=(10, 4))
            for result in records:
                values = [float("nan") if p is None else p for p in result["probs"]]
                ax.plot(range(1, len(values) + 1), values, label=f"Seed {result['seed']}")
            ax.set(title="SA: Probabilitas Penerimaan", xlabel="Iterasi",
                   ylabel="p = min(1, exp(delta / T))", ylim=(-.03, 1.03))
            ax.grid(alpha=.3)
            ax.legend()
            fig.tight_layout()

    configurations = {}
    for result in results:
        if result["algorithm"] == "ga":
            key = (result.get("group", ""), result["population_size"], result["iterations"])
            configurations.setdefault(key, []).append(result)
    for (group, population, generations), records in configurations.items():
        fig, axes = plt.subplots(1, len(records), figsize=(5 * len(records), 4), squeeze=False)
        for ax, result in zip(axes[0], records):
            history = result["history"]
            x = [row["iteration"] for row in history]
            ax.plot(x, [row["maximum"] for row in history], label="Maksimum")
            ax.plot(x, [row["average"] for row in history], label="Rata-rata")
            ax.set(title=f"Seed {result['seed']}", xlabel="Generasi", ylabel="Shipping fee")
            ax.grid(alpha=.3)
            ax.legend()
        fig.suptitle(f"GA {group}: populasi {population}, generasi {generations}")
        fig.tight_layout()
    plt.show()


def main():
    """Jalankan eksperimen; setiap run langsung disimpan beserta grafik PNG."""
    dataset_path = ROOT / "data" / f"{DATASET}.json"
    dataset = load_json(dataset_path)
    vehicles, ship = make_models(dataset)
    if ALGORITHM == "all":
        algorithms = ["HC", "SA", "GA"]
    elif ALGORITHM == "both":
        algorithms = ["HC", "GA"]
    else:
        algorithms = [ALGORITHM.upper()]
    results = []
    print("Dataset:", dataset_path.name)
    print("Seeds:", SEEDS)
    for algorithm in algorithms:
        printed_count = 0

        def update(bundle, message):
            nonlocal printed_count
            print(message, flush=True)
            if len(bundle["runs"]) > printed_count:
                record = bundle["runs"][-1]
                result = dict(record["raw"], algorithm=algorithm.lower())
                print_result(algorithm.lower(), result, vehicles, ship, len(bundle["runs"]))
                printed_count = len(bundle["runs"])

        bundle = execute_experiment(
            dataset, algorithm, SEEDS, output_root=ROOT / "output", on_update=update)
        results.extend(dict(record["raw"], algorithm=algorithm.lower())
                       for record in bundle["runs"])
        print(f"\n{algorithm}: {len(bundle['runs'])}/{bundle['expected_runs']} run tersimpan.")
        print("Folder:", bundle["folder"])

    print("\nRINGKASAN SELURUH RUN")
    for result in results:
        initial, _, value, duration = describe_result(result["algorithm"], result, vehicles)
        print(f"{result['algorithm'].upper()} | Seed {result['seed']} | "
              f"Awal: {calculate_objective(vehicles, initial):g} | Hasil: {value:g} | "
              f"Iterasi: {result['iterations']} | Durasi: {duration:.4f} s")
    print("\nDurasi HC di luar inisialisasi. SA dan GA mencakup inisialisasi internal.")
    print("Durasi tidak mencakup penulisan berkas dan pembuatan PNG.")
    if SHOW_PLOT:
        plot_objective(results)
    return results


if __name__ == "__main__":
    main()
