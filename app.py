"""Layar utama kapal; laporan khusus algoritma tersedia setelah pencarian."""

import random
from html import escape
from pathlib import Path

import streamlit as st

from src.algorithm.genetic_algorithm import generate_population
from src.init.initialization import generate_initial_state
from src.init.objective import calculate_objective
from src.result_io import (
    load_json, make_models, state_summary, summary_rows,
    list_sessions, load_session, session_label,
)
from src.visualization.ship_scene import ship_scene
from src.visualization.reports import result_panel
from src.experiments import (
    default_variations, execute_experiment, parse_variations,
)

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Pararunten | Penataan Kapal", page_icon="🚢",
                   layout="wide", initial_sidebar_state="collapsed")


def show_svg(markup):
    """Merender SVG buatan aplikasi; st.html menyaring tag SVG pada versi ini."""
    # Markup dibuat oleh ship_scene, bukan HTML dari input pengguna.
    # Teks kendaraan sudah di-escape oleh pembuat gambar.
    st.markdown(markup, unsafe_allow_html=True)


def clear_workspace():
    """Menghapus hasil lama ketika dataset, algoritma, atau parameter diubah."""
    for key in ["archive_bundle", "work_bundle", "initial_preview", "preview_key"]:
        st.session_state.pop(key, None)
    st.session_state["active_run"] = 0


def regenerate():
    """Menggunakan seed berikutnya supaya tombol Generate memberi susunan baru."""
    st.session_state["seed"] = st.session_state.get("seed", 42) + 1
    clear_workspace()


@st.cache_data(show_spinner=False)
def read_archive(folder, version):
    """Cache arsip agar perubahan pilihan tampilan tidak membaca ulang semua file."""
    return load_session(folder)


def menus():
    """Memilih arsip HC/GA dan parameter eksperimen sesuai Cakupan."""
    brand, settings, archives, details = st.columns([5, 1.3, 1.1, 1.1])
    with brand:
        st.html('<div class="top-brand">PARARUNTEN<span>IF3070 · KELOMPOK 22</span></div>')
    with archives:
        with st.popover("Arsip", use_container_width=True):
            st.markdown("#### Hasil eksperimen HC / GA")
            folders = list_sessions(ROOT)
            if folders:
                folder = st.selectbox("Sesi tersimpan", folders, format_func=session_label)
                if st.button("Buka sesi", use_container_width=True):
                    try:
                        paths = [folder / "dataset.json"] + sorted(folder.glob("*/run.json"))
                        if (folder / "session.json").exists():
                            paths.append(folder / "session.json")
                        version = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths)
                        bundle = read_archive(str(folder), version)
                        clear_workspace()
                        st.session_state["archive_bundle"] = bundle
                        raw = bundle["runs"][0]["raw"]
                        controls = bundle.get("parameters", {})
                        is_ga = bundle["algorithm"] == "GA"
                        st.session_state["algorithm"] = "Genetic Algorithm" if is_ga else "Hill-Climbing"
                        st.session_state["seed"] = bundle.get("seeds", [raw["seed"]])[0]
                        if is_ga:
                            population = controls.get("population_size", raw["population_size"])
                            b_run = next((r for r in bundle["runs"] if r["group"] == "B"), bundle["runs"][0])
                            generations = controls.get("generations", b_run["iterations"])
                            st.session_state["population_size"] = population
                            st.session_state["generations"] = generations
                            values_g = controls.get("generation_values") or sorted({
                                r["iterations"] for r in bundle["runs"] if r["group"] == "A"})
                            values_p = controls.get("population_values") or sorted({
                                r["raw"]["population_size"] for r in bundle["runs"] if r["group"] == "B"})
                            if len(values_g) == 3:
                                st.session_state[f"generation_values_{generations}"] = ", ".join(map(str, values_g))
                            if len(values_p) == 3:
                                st.session_state[f"population_values_{population}"] = ", ".join(map(str, values_p))
                        else:
                            st.session_state["max_sideways"] = raw["parameters"]["max_sideways"]
                        name = bundle["dataset"].get("dataset_id")
                        if name in ["small", "medium", "large"]:
                            st.session_state["dataset_name"] = name
                    except (ValueError, KeyError, TypeError, OSError) as error:
                        st.error(f"Arsip belum bisa dibuka: {error}")
                st.caption("Hasil dibaca dari file, tanpa mengulang pencarian.")
            else:
                st.caption("Belum ada hasil tersimpan. Klik Mulai untuk membuat sesi.")
    with settings:
        with st.popover("Pengaturan", use_container_width=True):
            st.markdown("#### Eksperimen tugas besar")
            st.selectbox("Dataset", ["small", "medium", "large"], key="dataset_name",
                         on_change=clear_workspace)
            st.number_input("Seed awal", min_value=0, value=42, step=1, key="seed",
                            on_change=clear_workspace)
            is_ga = st.session_state.get("algorithm") == "Genetic Algorithm"
            if not is_ga:
                st.info("Sekali Mulai menjalankan HC sebanyak 3 kali.")
                st.number_input("Maksimum sideways berturut-turut", 0, 10000, 100, 10,
                                key="max_sideways", on_change=clear_workspace)
            else:
                st.info("Sekali Mulai menjalankan GA sebanyak 18 kali: 9 run A + 9 run B.")
                population = st.number_input("Populasi kontrol · kelompok A", 1, 500, 20, 1,
                                             key="population_size", on_change=clear_workspace)
                generations = st.number_input("Generasi kontrol · kelompok B", 1, 5000, 100, 10,
                                              key="generations", on_change=clear_workspace)
                st.text_input("3 variasi generasi · kelompok A",
                              ", ".join(map(str, default_variations(generations))),
                              key=f"generation_values_{generations}", on_change=clear_workspace)
                st.text_input("3 variasi populasi · kelompok B",
                              ", ".join(map(str, default_variations(population))),
                              key=f"population_values_{population}", on_change=clear_workspace)
                st.caption("Peluang mutasi eksperimen baru dipertahankan 0.1. "
                           "Hanya populasi dan generasi yang divariasikan.")
            st.caption("Setiap konfigurasi memakai tiga seed berbeda: S, S+1, S+2. "
                       "Semua hasil otomatis disimpan setelah masing-masing run selesai.")
    return details


def configuration():
    """Nilai kontrol; daftar variasi baru divalidasi ketika Mulai ditekan."""
    state = st.session_state
    algorithm = "GA" if state.get("algorithm") == "Genetic Algorithm" else "HC"
    population, generations = state.get("population_size", 20), state.get("generations", 100)
    params = {
        "max_sideways": state.get("max_sideways", 100),
        "population_size": population, "generations": generations,
        "mutation_rate": .1,
        "generation_values": state.get(f"generation_values_{generations}",
                                       ", ".join(map(str, default_variations(generations)))),
        "population_values": state.get(f"population_values_{population}",
                                       ", ".join(map(str, default_variations(population)))),
    }
    return algorithm, state.get("seed", 42), params


def make_preview(dataset, algorithm, seed, parameters):
    """Membuat state awal deterministik yang sama dengan awal algoritmanya."""
    vehicles, ship = make_models(dataset)
    signature = (dataset.get("dataset_id"), algorithm, seed, parameters["population_size"])
    if st.session_state.get("preview_key") != signature:
        rng = random.Random(seed)
        if algorithm == "GA":
            population = generate_population(vehicles, ship, parameters["population_size"], rng)
            positions = max(population, key=lambda s: calculate_objective(vehicles, s))
        else:
            positions = generate_initial_state(vehicles, ship, rng)
        st.session_state["initial_preview"] = positions
        st.session_state["preview_key"] = signature
    return st.session_state["initial_preview"]


def search(dataset, algorithm, seed, parameters, progress_area):
    """Menjalankan Cakupan, mencatat file, dan memperbarui tabel setiap run selesai."""
    params = parameters.copy()
    if algorithm == "GA":
        params["generation_values"] = parse_variations(params["generation_values"], "Variasi generasi")
        params["population_values"] = parse_variations(params["population_values"], "Variasi populasi")
    else:
        params.pop("generation_values", None)
        params.pop("population_values", None)
    # Arsip lama tetap di disk; klik Mulai selalu membuat sesi baru.
    st.session_state.pop("archive_bundle", None)
    with progress_area.container():
        st.html('<div id="proses-pencarian"></div>')
        with st.status("Menjalankan eksperimen", expanded=True) as status:
            progress = st.progress(0, text="Menyiapkan percobaan…")
            message = st.empty()
            table = st.empty()

            def update(bundle, text):
                st.session_state["work_bundle"] = bundle
                count, total = len(bundle["runs"]), bundle["expected_runs"]
                progress.progress(count / total, text=f"{count}/{total} percobaan selesai dan dicatat")
                message.caption(text)
                if bundle["runs"]:
                    table.dataframe(summary_rows(bundle["runs"]), hide_index=True,
                                    use_container_width=True)

            try:
                bundle = execute_experiment(
                    dataset, algorithm, [seed, seed + 1, seed + 2], params,
                    ROOT / "output", on_update=update,
                )
                # Baca hasil akhir dari berkas yang sudah tersimpan di output.
                bundle = load_session(bundle["folder"])
                st.session_state["work_bundle"] = bundle
                status.update(label=f"Selesai · {len(bundle['runs'])} hasil tersimpan",
                              state="complete", expanded=False)
            except BaseException:
                status.update(label="Sesi belum lengkap; hasil yang selesai tetap tersimpan",
                              state="error", expanded=True)
                raise
    return bundle


def detail_menu(column, bundle, run, vehicles, ship, initial):
    """Inventaris tetap bisa dibuka tanpa menggeser tampilan kedua kapal."""
    with column:
        with st.popover("Detail", use_container_width=True):
            st.markdown("#### Data kendaraan")
            positions = run["final_state"] if run else initial
            rows = [{
                "ID": v.id, "Status": "Dimuat" if p is not None else "Di luar",
                "Ukuran asli": f"{v.dimensions.w} × {v.dimensions.l}",
                "Tarif (jt)": v.shipping_fee, "Berat": v.weight, "ETA": v.eta,
                "Posisi": f"({p.x}, {p.y})" if p is not None else "—",
                "Orientasi": p.orientation.value if p is not None else "—",
            } for v, p in zip(vehicles, positions)]
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.caption("Sorot mobil untuk detailnya. Semua kendaraan yang tidak dimuat "
                       "ada di parkiran; skala parkiran terpisah dari grid geladak.")
            if run:
                st.caption("Laporan, grafik, populasi GA, dan unduhan tersedia "
                           "pada panel hasil di bawah tampilan kapal.")


def main():
    """Kapal memenuhi layar awal, progres dan laporan berada di bawahnya."""
    css = (ROOT / "src" / "visualization" / "style.css").read_text(encoding="utf-8")
    st.html("<style>" + css + "</style>")
    detail_column = menus()
    with st.container(key="workspace"):
        left, center, right = st.columns([4.5, 1.65, 4.5], gap="medium")
    # Placeholder berada setelah workspace, bukan di kolom kontrol yang sempit.
    progress_area = st.empty()
    with center:
        st.html('<div class="control-spacer"></div>')
        st.selectbox("Pilih Algoritma", ["Hill-Climbing", "Genetic Algorithm"],
                     key="algorithm", on_change=clear_workspace,
                     label_visibility="collapsed")
        algorithm, seed, parameters = configuration()
        total = 3 if algorithm == "HC" else 18
        st.caption(f"Mulai = {total} percobaan")
        start = st.button("Mulai", type="primary", use_container_width=True)
        bundle = st.session_state.get("archive_bundle") or st.session_state.get("work_bundle")
        dataset = bundle["dataset"] if bundle else load_json(
            ROOT / "data" / f"{st.session_state.get('dataset_name', 'small')}.json")
        if start:
            running_link = st.empty()
            running_link.markdown('<a class="results-link" href="#proses-pencarian">Lihat progres ↓</a>',
                                  unsafe_allow_html=True)
            try:
                bundle = search(dataset, algorithm, seed, parameters, progress_area)
                st.session_state["active_run"] = 0
            except Exception as error:
                st.error(f"Eksperimen belum selesai: {error}")
                bundle = st.session_state.get("work_bundle")
            finally:
                progress_area.empty()
                running_link.empty()
        index = 0
        if bundle and bundle["runs"]:
            index = min(st.session_state.get("active_run", 0), len(bundle["runs"]) - 1)
            if st.session_state.get("active_run") != index:
                st.session_state["active_run"] = index
        run = bundle["runs"][index] if bundle and bundle["runs"] else None
        vehicles, ship = make_models(dataset)
        initial = run["initial_state"] if run else make_preview(dataset, algorithm, seed, parameters)
        dataset_name = escape(str(dataset.get("dataset_id", "dataset")))
        shown_seed = run["seed"] if run else seed
        st.html(f'<div class="control-info">{dataset_name.upper()}<br>'
                f'{ship.dimensions.w} × {ship.dimensions.l} grid<br>Seed {shown_seed}</div>')
        if run:
            st.html('<a class="results-link" href="#hasil-pencarian">Lihat hasil ↓</a>')
            expected = bundle.get("expected_runs", 3 if run["algorithm"] == "HC" else 18)
            st.caption(f"{len(bundle['runs'])}/{expected} run tersimpan")
    with left:
        st.html('<h2 class="state-title">INITIAL STATE</h2>')
        show_svg(ship_scene(vehicles, initial, ship))
        st.button("Generate Initial State", on_click=regenerate,
                  use_container_width=True, key="generate")
        summary = state_summary(vehicles, initial, ship)
        st.html(f'<div class="state-caption">Rp {summary["objective"]:g} jt · '
                f'{summary["loaded"]} dimuat · {summary["outside"]} di luar</div>')
    with right:
        st.html('<h2 class="state-title">FINAL STATE</h2>')
        show_svg(ship_scene(vehicles, run["final_state"] if run else None, ship))
        if run:
            summary = state_summary(vehicles, run["final_state"], ship)
            text = (f'{"Susunan valid" if summary["valid"] else "Susunan tidak valid"} · '
                    f'geladak terpakai {summary["utilization"]:.1f}%')
        else:
            text = "Hasil akan muncul setelah pencarian selesai"
        st.html(f'<div class="final-caption">{text}</div>')
    detail_menu(detail_column, bundle, run, vehicles, ship, initial)
    if run is not None:
        result_panel(bundle, run, vehicles, ship, index)


if __name__ == "__main__":
    main()
