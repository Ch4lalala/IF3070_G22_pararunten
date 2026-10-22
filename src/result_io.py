"""Membaca dan menyimpan hasil eksperimen, CSV, dan grafik PNG."""

import csv
import hashlib
import io
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path

from src.init.constraints import is_valid_state
from src.init.models import Dimension, Orientation, Position, Ship, Vehicle
from src.init.objective import calculate_objective

def load_json(path):
    """Membaca JSON, termasuk berkas dengan penanda encoding UTF-8 BOM."""
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def make_models(dataset):
    """Mengubah snapshot dataset menjadi model kapal dan kendaraan."""
    ship_data = dataset["ship"]
    ship = Ship(Dimension(**ship_data["dimensions"]), ship_data["max_capacity"])
    vehicles = [Vehicle(
        id=item["id"], dimensions=Dimension(**item["dimensions"]),
        shipping_fee=item["shipping_fee"], weight=item["weight"], eta=item["eta"],
    ) for item in dataset["vehicles"]]
    return vehicles, ship

def read_positions(positions):
    """Membaca Position dari JSON; None tetap berarti tidak dimuat."""
    return [None if item is None else Position(
        x=item["x"], y=item["y"], orientation=Orientation(item["orientation"]),
    ) for item in positions]

def json_default(value):
    """Membantu JSON menyimpan dataclass dan Enum milik model."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Tipe {type(value).__name__} tidak dapat disimpan.")

def export_json(bundle):
    """Menyertakan dataset dan hasil lengkap untuk unduhan eksperimen."""
    return json.dumps(bundle, default=json_default, ensure_ascii=False,
                      indent=2, allow_nan=False)

def state_summary(vehicles, positions, ship):
    """Menghitung ringkasan dari state yang benar-benar ditampilkan."""
    loaded = [v for v, p in zip(vehicles, positions) if p is not None]
    area = sum(v.dimensions.w * v.dimensions.l for v in loaded)
    return {
        "objective": calculate_objective(vehicles, positions),
        "weight": sum(v.weight for v in loaded),
        "loaded": len(loaded), "outside": len(vehicles) - len(loaded),
        "area": area, "utilization": area / (ship.dimensions.w * ship.dimensions.l) * 100,
        "valid": is_valid_state(vehicles, positions, ship),
    }

def normalize_result(algorithm, result, vehicles):
    """Menyeragamkan nama field untuk tampilan tanpa mengubah algoritma."""
    if algorithm == "GA":
        # GA tidak mempunyai satu state awal: gunakan individu awal terbaik.
        initial = max(result["initial_population"],
                      key=lambda s: calculate_objective(vehicles, s))
        final = result["best_individual"]
        duration = result["duration_seconds"]
        objective = result["best_objective"]
    else:
        initial = result["initial_state"]
        final = result["final_state"]
        duration = result["duration"]
        objective = result["final_objective"]
    return {
        "algorithm": algorithm, "seed": result.get("seed", 0),
        "group": result.get("group", ""),
        "initial_state": initial, "final_state": final,
        "objective": objective, "duration": duration,
        "iterations": result["iterations"], "history": result["history"],
        "raw": result,
    }

def load_ga_session(folder):
    """Membaca sesi GA memakai snapshot dataset yang tersimpan di sesi itu."""
    folder = Path(folder)
    dataset = load_json(folder / "dataset.json")
    vehicles, ship = make_models(dataset)
    runs = []
    for path in sorted(folder.glob("*/run.json")):
        result = load_json(path)
        for key in ["initial_population", "final_population"]:
            result[key] = [read_positions(s) for s in result[key]]
        result["best_individual"] = read_positions(result["best_individual"])
        record = normalize_result("GA", result, vehicles)
        states = result["initial_population"] + result["final_population"] + [record["final_state"]]
        if not all(is_valid_state(vehicles, s, ship) for s in states):
            raise ValueError(f"Ada state tidak valid pada {path.parent.name}.")
        if calculate_objective(vehicles, record["final_state"]) != record["objective"]:
            raise ValueError(f"Objective tidak cocok pada {path.parent.name}.")
        runs.append(record)
    if not runs:
        raise ValueError("Sesi ini belum memiliki run.json lengkap.")
    return {"dataset": dataset, "runs": runs, "source": folder.name}

def result_label(run, number):
    """Membuat label pemilih percobaan, termasuk parameter GA."""
    label = f"{number + 1:02d} · seed {run['seed']}"
    if run["algorithm"] == "GA":
        raw = run["raw"]
        label += f" · P{raw['population_size']} / G{raw['iterations']}"
        if run["group"]:
            label += f" · {run['group']}"
    return label

def summary_rows(runs):
    """Membuat tabel sesuai field yang diwajibkan untuk algoritma setiap run."""
    rows = []
    for number, run in enumerate(runs, 1):
        raw = run["raw"]
        is_ga = run["algorithm"] == "GA"
        initial_value = run["history"][0]["maximum"] if is_ga else run["history"][0]
        row = {
            "Percobaan": number, "Run ID": run.get("run_id", raw.get("run_id", "")),
            "Algoritma": run["algorithm"], "Seed": run["seed"],
            "Objective awal": initial_value, "Objective hasil": run["objective"],
            "Jumlah iterasi": run["iterations"], "Durasi (detik)": round(run["duration"], 4),
            # Arsip HC lama hanya mengukur pencarian, tanpa inisialisasi.
            "Cakupan durasi": raw.get("duration_scope",
                "search_only" if run["algorithm"] == "HC" else "initialization_and_search"),
        }
        if is_ga:
            row.update({
                "Kelompok": run["group"] or "Uji",
                "Jumlah populasi": raw["population_size"],
                "Peluang mutasi": raw["mutation_rate"],
                "Maksimum populasi akhir": run["history"][-1]["maximum"],
                "Rata-rata populasi akhir": round(run["history"][-1]["average"], 2),
            })
        elif run["algorithm"] == "SA":
            row.update({
                "Suhu awal": raw["parameters"]["T0"],
                "Alpha": raw["parameters"]["alpha"],
                "Suhu minimum": raw["parameters"]["T_min"],
                "Batas iterasi": raw["parameters"]["max_iter"],
                "Objective terbaik": raw["best_objective"],
                "Frekuensi local optimum": raw["local_optimum_count"],
                "Langkah menurun diterima": raw["worse_accepted"],
                "Kandidat ditolak": raw["rejected_moves"],
                "Gagal mencari tetangga": raw["failed_neighbor"],
                "Alasan berhenti": raw["stop_reason"],
            })
        else:
            row.update({
                "Maksimum sideways": raw["parameters"]["max_sideways"],
                "Total sideways": raw["total_sideways"],
                "Alasan berhenti": raw["stop_reason"],
            })
        rows.append(row)
    return rows

def dataset_digest(dataset):
    """Mencegah membandingkan hasil dari data kendaraan atau kapal yang berbeda."""
    content = json.dumps(dataset, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def write_json(path, value):
    """Menyelesaikan berkas sementara dahulu sebelum mengganti checkpoint."""
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, default=json_default, ensure_ascii=False, indent=2,
                   allow_nan=False), encoding="utf-8",
    )
    temporary.replace(path)

def csv_text(rows):
    """Membuat CSV untuk tabel ringkasan dan unduhan."""
    buffer = io.StringIO(newline="")
    fields = list(rows[0]) if rows else ["Percobaan", "Algoritma", "Seed", "Objective hasil"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()

def save_checkpoint(bundle):
    """Menyimpan status sesi dan tabel setelah setiap run, termasuk saat gagal."""
    folder = Path(bundle["folder"])
    metadata = {key: bundle[key] for key in [
        "source", "algorithm", "created_at", "status", "expected_runs",
        "plan", "dataset_digest", "parameters", "seeds",
    ]}
    metadata["schema_version"] = 1
    metadata["completed_runs"] = len(bundle["runs"])
    if bundle.get("error"):
        metadata["error"] = bundle["error"]
    write_json(folder / "session.json", metadata)
    rows = summary_rows(bundle["runs"])
    summary_path = folder / "summary.csv"
    content = csv_text(rows).encode("utf-8-sig")
    # Perubahan status sesi saja tidak perlu menulis ulang CSV yang sama.
    if not summary_path.exists() or summary_path.read_bytes() != content:
        temporary = folder / "summary.csv.tmp"
        temporary.write_bytes(content)
        temporary.replace(summary_path)

def save_plot(runs, folder):
    """Buat plot satu run atau gabungkan beberapa run untuk perbandingan."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    if not runs:
        return []
    folder = Path(folder)
    algorithm = runs[0]["algorithm"]
    colors = ["#2166AC", "#D55E00", "#26845B"]
    styles = ["-", "--", ":"]
    paths = []

    if algorithm in ("HC", "SA"):
        figure = Figure(figsize=(10, 5))
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        for i, run in enumerate(runs):
            history = run["history"]
            color = colors[i % len(colors)]
            ax.plot(range(len(history)), history, color=color,
                    linestyle=styles[i % len(styles)], linewidth=1.8,
                    label=f"Percobaan {i + 1} (seed {run['seed']})")
            ax.plot(len(history) - 1, history[-1], "o", color=color, markersize=4)
        ax.set_title(f"{algorithm}: Objective dari {len(runs)} Percobaan")
        ax.set_xlabel("Iterasi (0 = state awal)")
        ax.set_ylabel("Shipping fee (juta rupiah)")
        ax.grid(alpha=.3)
        ax.legend()
        figure.tight_layout()
        path = folder / "objective.png"
        figure.savefig(path, dpi=150)
        figure.clear()
        paths.append(path)

        if algorithm == "SA":
            figure = Figure(figsize=(10, 5))
            FigureCanvasAgg(figure)
            ax = figure.subplots()
            for i, run in enumerate(runs):
                # Data tanpa kandidat diberi celah, bukan diubah menjadi nol.
                values = [float("nan") if p is None else p for p in run["raw"]["probs"]]
                ax.plot(range(1, len(values) + 1), values,
                        color=colors[i % len(colors)],
                        linestyle=styles[i % len(styles)], linewidth=1.2, alpha=.85,
                        label=f"Percobaan {i + 1} (seed {run['seed']})")
            ax.set_title(f"SA: Probabilitas Penerimaan dari {len(runs)} Percobaan")
            ax.set_xlabel("Iterasi")
            ax.set_ylabel("p = min(1, exp(delta / T))")
            ax.set_ylim(-.03, 1.03)
            ax.grid(alpha=.3)
            ax.legend()
            if not any(run["raw"]["probs"] for run in runs):
                ax.text(.5, .5, "Tidak ada iterasi", ha="center", transform=ax.transAxes)
            figure.tight_layout()
            path = folder / "probability.png"
            figure.savefig(path, dpi=150)
            figure.clear()
            paths.append(path)

    elif algorithm == "GA":
        # Kelompok A/B dan konfigurasi yang berbeda mempunyai grafik terpisah.
        configurations = {}
        for run in runs:
            raw = run["raw"]
            key = (run.get("group", "") or "GA", raw["population_size"], raw["iterations"])
            configurations.setdefault(key, []).append(run)

        for (group, population, generations), records in configurations.items():
            figure = Figure(figsize=(12, 5))
            FigureCanvasAgg(figure)
            axes = figure.subplots(1, 2)
            for i, run in enumerate(records):
                history = run["history"]
                x = [row["iteration"] for row in history]
                for ax, field in zip(axes, ("maximum", "average")):
                    ax.plot(x, [row[field] for row in history],
                            color=colors[i % len(colors)],
                            linestyle=styles[i % len(styles)], linewidth=1.8,
                            label=f"Percobaan {i + 1} (seed {run['seed']})")
            for ax, title in zip(axes, ("Maksimum Objective", "Rata-rata Populasi")):
                ax.set_title(title)
                ax.set_xlabel("Generasi (0 = populasi awal)")
                ax.set_ylabel("Shipping fee (juta rupiah)")
                ax.grid(alpha=.3)
                ax.legend(fontsize=9)
            figure.suptitle(f"GA {group}: populasi {population}, generasi {generations} "
                           f"({len(records)} percobaan)")
            figure.tight_layout()
            # Satu run memakai nama yang sama dengan HC/SA.
            filename = ("objective.png" if len(runs) == 1 else
                        f"objective_{group}_pop-{population}_iter-{generations}.png")
            path = folder / filename
            figure.savefig(path, dpi=150)
            figure.clear()
            paths.append(path)
    else:
        raise ValueError("Algoritma tidak dikenal: " + str(algorithm))
    return paths

def save_run(record, folder):
    """Simpan JSON, CSV, dan plot setiap run; grafik gabungan dibuat di akhir sesi."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    write_json(folder / "run.json", record["raw"])
    if record["algorithm"] in ("HC", "SA"):
        rows = [{"iteration": i, "objective": value}
                for i, value in enumerate(record["history"])]
    else:
        rows = record["history"]
    (folder / "history.csv").write_text(csv_text(rows), encoding="utf-8-sig", newline="")

    if record["algorithm"] == "SA":
        raw = record["raw"]
        rows = [{
            "iteration": i + 1,
            "temperature": raw["temperatures"][i],
            "delta": raw["deltas"][i],
            "acceptance_probability": raw["probs"][i],
            "local_optimum": raw["local_optimum_history"][i + 1],
        } for i in range(record["iterations"])]
        # Tuliskan header juga jika algoritma berhenti sebelum iterasi pertama.
        if rows:
            text = csv_text(rows)
        else:
            text = "iteration,temperature,delta,acceptance_probability,local_optimum\r\n"
        (folder / "probabilities.csv").write_text(text, encoding="utf-8-sig", newline="")

    # Plot tersendiri untuk run ini, selain plot gabungan pada folder sesi.
    save_plot([record], folder)


def list_sessions(project_root):
    """Mencari arsip HC, SA, dan GA yang sudah memiliki hasil run."""
    project_root = Path(project_root)
    folders = []
    for name in ["hill_climbing", "simulated_annealing", "genetic_algorithm"]:
        for folder in (project_root / "output" / name).glob("*"):
            if folder.is_dir() and (folder / "dataset.json").exists() and any(folder.glob("*/run.json")):
                folders.append(folder)
    return sorted(folders, key=lambda p: p.stat().st_mtime_ns, reverse=True)

def session_label(folder):
    """Menjelaskan algoritma dan kelengkapan sesi di pemilih arsip."""
    folder = Path(folder)
    path = folder / "session.json"
    if path.exists():
        metadata = load_json(path)
        count = metadata["completed_runs"]
        expected = metadata["expected_runs"]
        status = "lengkap" if metadata["status"] == "complete" else "belum lengkap"
        return f"{metadata['algorithm']} · {count}/{expected} run · {status} · {folder.name}"
    return f"GA · {len(list(folder.glob('*/run.json')))} run · {folder.name}"

def load_session(folder):
    """Memulihkan objek Position dan seluruh hasil dari snapshot sesi tersimpan."""
    folder = Path(folder)
    dataset = load_json(folder / "dataset.json")
    vehicles, ship = make_models(dataset)
    metadata = load_json(folder / "session.json") if (folder / "session.json").exists() else {}
    runs = []
    jobs = metadata.get("plan", [])
    paths = [folder / job["run_id"] / "run.json" for job in jobs] if jobs else sorted(folder.glob("*/run.json"))
    for path in paths:
        if not path.exists():
            continue
        raw = load_json(path)
        algorithm = metadata.get("algorithm") or raw.get("algorithm") or (
            "GA" if "initial_population" in raw else "SA" if "probs" in raw else "HC")
        if algorithm == "GA":
            for field in ["initial_population", "final_population"]:
                raw[field] = [read_positions(state) for state in raw[field]]
            raw["best_individual"] = read_positions(raw["best_individual"])
            states = raw["initial_population"] + raw["final_population"] + [raw["best_individual"]]
        else:
            raw["initial_state"] = read_positions(raw["initial_state"])
            raw["final_state"] = read_positions(raw["final_state"])
            states = [raw["initial_state"], raw["final_state"]]
            if algorithm == "SA":
                raw["best_state"] = read_positions(raw["best_state"])
                states.append(raw["best_state"])
        if not all(is_valid_state(vehicles, state, ship) for state in states):
            raise ValueError(f"State tidak valid pada {path.parent.name}.")
        record = normalize_result(algorithm, raw, vehicles)
        if calculate_objective(vehicles, record["final_state"]) != record["objective"]:
            raise ValueError(f"Objective tidak cocok pada {path.parent.name}.")
        record["run_id"] = path.parent.name
        runs.append(record)
    if not runs:
        raise ValueError("Sesi belum memiliki run yang selesai.")
    expected = metadata.get("expected_runs", 18 if runs[0]["algorithm"] == "GA" else 3)
    status = metadata.get("status", "complete" if len(runs) == expected else "incomplete")
    if status == "complete" and len(runs) != expected:
        status = "incomplete"
    return {
        **metadata, "dataset": dataset, "runs": runs, "source": folder.name,
        "folder": str(folder.resolve()), "algorithm": runs[0]["algorithm"],
        "expected_runs": expected, "status": status,
    }

def comparison_rows(project_root, dataset):
    """Membaca ringkasan sesi lengkap pada dataset sama, tanpa memuat populasi lagi."""
    digest = dataset_digest(dataset)
    records = []
    for folder in list_sessions(project_root):
        metadata_path, summary_path = folder / "session.json", folder / "summary.csv"
        if not metadata_path.exists() or not summary_path.exists():
            continue
        metadata = load_json(metadata_path)
        if metadata.get("dataset_digest") != digest or metadata["status"] != "complete":
            continue
        with summary_path.open(encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                records.append({
                    "Sesi": folder.name, "Algoritma": row["Algoritma"],
                    "Seed": int(row["Seed"]), "Kelompok": row.get("Kelompok", ""),
                    "Populasi": row.get("Jumlah populasi", ""),
                    "Generasi": row["Jumlah iterasi"] if row["Algoritma"] == "GA" else "",
                    "Objective": float(row["Objective hasil"]),
                    "Durasi (s)": float(row["Durasi (detik)"]),
                    "Cakupan durasi": row.get("Cakupan durasi") or (
                        "search_only" if row["Algoritma"] == "HC"
                        else "initialization_and_search"),
                })
    return records
