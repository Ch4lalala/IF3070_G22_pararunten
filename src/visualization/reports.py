"""Hasil eksperimen yang diwajibkan untuk HC, SA, dan GA."""

from html import escape
import streamlit as st

from src.result_io import result_label, state_summary
from src.visualization.charts import all_histories_chart, ga_configuration_chart, sa_exponential_chart
from src.visualization.ship_scene import ship_scene


def draw_chart(figure, key):
    """Menampilkan grafik hasil eksperimen."""
    figure.update_layout(height=420, margin=dict(l=45, r=25, t=45, b=85))
    st.plotly_chart(figure, use_container_width=True, theme=None, key=key,
                   config={"displaylogo": False, "displayModeBar": False})


def cards(items, class_name):
    """Kartu ringkasan objective, durasi, dan hasil khusus algoritma."""
    markup = f'<div class="{class_name}">'
    for label, value, note in items:
        markup += (f'<div class="result-card"><span>{escape(str(label))}</span>'
                   f'<strong>{escape(str(value))}</strong><small>{escape(str(note))}</small></div>')
    st.html(markup + "</div>")


def required_summary_rows(runs):
    """Kolom tabel hanya memuat hasil yang digunakan dalam cakupan tugas."""
    rows = []
    for number, run in enumerate(runs, 1):
        raw = run["raw"]
        initial = run["history"][0]["maximum"] if run["algorithm"] == "GA" else run["history"][0]
        row = {"Percobaan": number, "Seed": run["seed"], "Objective awal": initial,
               "Objective akhir": run["objective"], "Durasi (detik)": round(run["duration"], 4)}
        if run["algorithm"] == "HC":
            row.update({"Jumlah iterasi": run["iterations"],
                        "Maksimum sideways": raw["parameters"]["max_sideways"]})
        elif run["algorithm"] == "SA":
            row["Frekuensi local optimum"] = raw["local_optimum_count"]
        else:
            row.update({"Kelompok": run["group"], "Jumlah populasi": raw["population_size"],
                        "Jumlah iterasi": run["iterations"]})
        rows.append(row)
    return rows


def state_rows(vehicles, positions):
    """Seluruh kendaraan dimuat maupun di luar, sesuai state terpilih."""
    return [{"ID": vehicle.id, "Status": "Dimuat" if position is not None else "Di luar",
             "Ukuran asli": f"{vehicle.dimensions.w} x {vehicle.dimensions.l}",
             "x": position.x if position is not None else None,
             "y": position.y if position is not None else None,
             "Orientasi": position.orientation.value if position is not None else "-",
             "Shipping fee": vehicle.shipping_fee, "Berat": vehicle.weight, "ETA": vehicle.eta}
            for vehicle, position in zip(vehicles, positions)]


def show_states(run, vehicles, ship):
    """Rincian penempatan awal dan hasil selain gambar kapal utama."""
    with st.expander("Rincian kendaraan pada state awal dan akhir"):
        left, right = st.columns(2)
        for column, key, label in [(left, "initial_state", "State awal"),
                                    (right, "final_state", "State akhir")]:
            with column:
                st.markdown(f"#### {label}")
                st.dataframe(state_rows(vehicles, run[key]), hide_index=True, use_container_width=True)


def ga_populations(run, vehicles, ship):
    """GA mempunyai populasi sebagai state awal dan akhir."""
    with st.expander("State populasi awal dan akhir GA"):
        left, right = st.columns(2)
        for column, field, label in [(left, "initial_population", "Populasi awal"),
                                     (right, "final_population", "Populasi akhir")]:
            with column:
                population = run["raw"][field]
                chosen = st.selectbox(label, list(range(len(population))),
                    format_func=lambda i: f"Individu {i + 1}",
                    key=f"population_{field}_{run['seed']}_{len(population)}_{run['iterations']}_{run['group']}")
                state = population[chosen]
                st.markdown(ship_scene(vehicles, state, ship), unsafe_allow_html=True)
                summary = state_summary(vehicles, state, ship)
                st.caption(f"Objective: Rp {summary['objective']:g} jt")


def hc_report(run, runs):
    """HC: iterasi, maksimum sideways, dan objective terhadap iterasi."""
    raw = run["raw"]
    scope = raw.get("sideways_limit_scope", "consecutive")
    label = "berturut-turut" if scope == "consecutive" else "total"
    st.caption(f"Maksimum sideways {label}: {raw['parameters']['max_sideways']}. "
               f"Total sideways selama run: {raw['total_sideways']}.")
    st.markdown("#### Objective terhadap iterasi")
    draw_chart(all_histories_chart(runs), "hc_objective")


def sa_report(run, runs, vehicles, ship):
    """SA: objective, exp(delta/T), dan frekuensi local optimum."""
    st.markdown("#### Objective terhadap iterasi")
    draw_chart(all_histories_chart(runs), "sa_objective")
    st.markdown("#### Eksponensial terhadap iterasi")
    draw_chart(sa_exponential_chart(runs), "sa_exponential")
    st.caption("exp(delta/T) ditampilkan pada skala logaritmik. Iterasi tanpa kandidat diberi celah.")
    with st.expander("State terbaik SA"):
        raw = run["raw"]
        st.caption(f"Objective terbaik: Rp {raw['best_objective']:g} jt. "
                   "Gambar FINAL STATE di atas menunjukkan state terakhir.")
        st.markdown(ship_scene(vehicles, raw["best_state"], ship), unsafe_allow_html=True)


def ga_report(run, runs, vehicles, ship):
    """GA: maksimum/rata-rata populasi, parameter, dan state populasi."""
    population = run["raw"]["population_size"]
    st.caption(f"Kelompok {run['group']} | Populasi {population} | {run['iterations']} generasi")
    selected = [record for record in runs if record["group"] == run["group"]
                and record["raw"]["population_size"] == population and record["iterations"] == run["iterations"]]
    st.markdown("#### Objective terhadap generasi")
    draw_chart(ga_configuration_chart(selected), "ga_objective")
    st.caption("Gambar utama GA menampilkan individu terbaik populasi awal dan solusi terbaik selama pencarian.")
    ga_populations(run, vehicles, ship)


def result_panel(bundle, run, vehicles, ship, index):
    """Panel hasil muncul setelah run atau arsip tersedia."""
    if not bundle or not run:
        return
    names = {"HC": "Hill-Climbing with Sideways Move", "SA": "Simulated Annealing", "GA": "Genetic Algorithm"}
    with st.container(key="results"):
        st.html('<div id="hasil-pencarian"></div><h2 class="results-title">HASIL PENCARIAN</h2>'
                f'<p class="results-subtitle">{names[run["algorithm"]]}</p>')
        if len(bundle["runs"]) > 1:
            st.selectbox("Percobaan yang ditampilkan", list(range(len(bundle["runs"]))), key="active_run",
                         format_func=lambda i: result_label(bundle["runs"][i], i))
        completed = len(bundle["runs"])
        expected = bundle.get("expected_runs", 18 if run["algorithm"] == "GA" else 3)
        if bundle.get("status", "complete") == "complete" and completed == expected:
            st.success(f"Selesai: {completed}/{expected} percobaan.")
        else:
            st.warning(f"Belum lengkap: {completed}/{expected} percobaan.")
            if bundle.get("error"):
                st.caption(bundle["error"])
        st.markdown("### Ringkasan percobaan")
        rows = required_summary_rows(bundle["runs"])
        if run["algorithm"] == "GA":
            tabs = st.tabs(["A - Variasi generasi", "B - Variasi populasi"])
            for tab, group in zip(tabs, ["A", "B"]):
                with tab:
                    st.caption("Populasi tetap; tiga variasi generasi, masing-masing tiga percobaan." if group == "A" else
                               "Generasi tetap; tiga variasi populasi, masing-masing tiga percobaan.")
                    st.dataframe([row for row in rows if row["Kelompok"] == group], hide_index=True,
                                 use_container_width=True)
        else:
            st.dataframe(rows, hide_index=True, use_container_width=True)
        extra = ("Jumlah iterasi", run["iterations"], "Perpindahan yang diterima")
        if run["algorithm"] == "SA":
            extra = ("Frekuensi local optimum", run["raw"]["local_optimum_count"], "Percobaan terpilih")
        elif run["algorithm"] == "GA":
            extra = ("Jumlah populasi", run["raw"]["population_size"], f"{run['iterations']} generasi")
        cards([("Objective akhir", f"Rp {run['objective']:g} jt", f"Seed {run['seed']}"),
               ("Durasi", f"{run['duration']:.4f} s", "Percobaan terpilih"), extra], "result-cards")
        if run["algorithm"] == "HC":
            hc_report(run, bundle["runs"])
        elif run["algorithm"] == "SA":
            sa_report(run, bundle["runs"], vehicles, ship)
        else:
            ga_report(run, bundle["runs"], vehicles, ship)
        show_states(run, vehicles, ship)
