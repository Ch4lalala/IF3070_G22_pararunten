"""Panel laporan setelah pencarian, dengan keluaran khusus untuk HC dan GA."""

import csv
import io
from collections import defaultdict
from html import escape
from pathlib import Path
from statistics import mean, stdev

import plotly.graph_objects as go
import streamlit as st

from src.visualization.charts import all_histories_chart, comparison_chart, history_chart
from src.result_io import export_json, result_label, state_summary, summary_rows
from src.visualization.ship_scene import ship_scene
from src.result_io import comparison_rows

REASONS = {
    "sideways_limit": "Batas sideways berturut-turut tercapai",
    "local_optimum": "Tidak ada tetangga bernilai sama atau lebih tinggi",
    "no_valid_neighbor": "Tidak ada tetangga valid",
}


def draw_chart(figure, key):
    """Menampilkan grafik besar yang dapat disorot dan diunduh sebagai PNG."""
    figure.update_layout(height=420, margin=dict(l=45, r=25, t=45, b=85))
    st.plotly_chart(
        figure, use_container_width=True, theme=None, key=key,
        config={"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2}},
    )


def cards(items, class_name):
    """Membuat kartu dari pasangan label, nilai, dan keterangan."""
    markup = f'<div class="{class_name}">'
    for label, value, note in items:
        markup += (f'<div class="result-card"><span>{escape(str(label))}</span>'
                   f'<strong>{escape(str(value))}</strong>'
                   f'<small>{escape(str(note))}</small></div>')
    st.html(markup + "</div>")


def state_rows(vehicles, positions):
    """Mencatat semua kendaraan pada satu state, termasuk yang tidak dimuat."""
    return [{
        "ID": v.id, "Status": "Dimuat" if p is not None else "Di luar",
        "x": p.x if p is not None else None,
        "y": p.y if p is not None else None,
        "Orientasi": p.orientation.value if p is not None else "—",
        "Tarif (jt)": v.shipping_fee, "Berat": v.weight,
    } for v, p in zip(vehicles, positions)]


def show_states(run, vehicles, ship):
    """Menyediakan data state awal/hasil untuk laporan, selain gambar di atas."""
    with st.expander("Rincian state awal dan hasil"):
        left, right = st.columns(2)
        for column, key, title in [
            (left, "initial_state", "Awal" if run["algorithm"] == "HC" else "Terbaik populasi awal"),
            (right, "final_state", "Akhir" if run["algorithm"] == "HC" else "Terbaik sepanjang pencarian"),
        ]:
            with column:
                st.markdown(f"#### {title}")
                summary = state_summary(vehicles, run[key], ship)
                st.caption(f"Objective Rp {summary['objective']:g} jt · "
                           f"berat {summary['weight']:g}/{ship.max_capacity} · "
                           f"{'valid' if summary['valid'] else 'tidak valid'}")
                st.dataframe(state_rows(vehicles, run[key]), hide_index=True,
                             use_container_width=True)


def hc_report(run, runs):
    """Keluaran khusus Hill-Climbing with Sideways Move sesuai spesifikasi."""
    raw = run["raw"]
    limit = raw["parameters"]["max_sideways"]
    cards([
        ("Jumlah iterasi", run["iterations"], "Perpindahan state yang diterima"),
        ("Maksimum sideways", limit, "Batas langkah sideways berturut-turut"),
        ("Total sideways", raw["total_sideways"], "Seluruh langkah bernilai sama"),
    ], "algorithm-cards")
    st.markdown("#### Perkembangan objective")
    draw_chart(history_chart(run), "report_hc_history")
    st.caption("Iterasi 0 adalah initial state. Garis mendatar menunjukkan langkah "
               "sideways; hitungan sideways berturut-turut direset saat objective meningkat.")
    st.info("Pencarian berhenti: " + REASONS.get(raw["stop_reason"], raw["stop_reason"]) + ".")
    if len(runs) > 1:
        st.markdown("#### Riwayat seluruh percobaan")
        draw_chart(all_histories_chart(runs), "report_hc_all_history")
    else:
        st.caption("Ini hasil satu percobaan. Untuk eksperimen tugas besar HC, "
                   "pilih mode Tiga percobaan dengan tiga seed berbeda.")


def ga_populations(run, vehicles, ship):
    """Memvisualisasikan setiap individu pada populasi awal dan populasi akhir."""
    with st.expander("Lihat seluruh individu populasi awal dan akhir"):
        st.caption("Dua populasi ini berbeda dari best_individual yang disimpan "
                   "sebagai rekor terbaik sepanjang pencarian.")
        with st.container(key="population_inspector"):
            left, right = st.columns(2)
            for column, field, label in [
                (left, "initial_population", "Populasi awal"),
                (right, "final_population", "Populasi akhir"),
            ]:
                with column:
                    population = run["raw"][field]
                    selected = st.selectbox(
                        label, list(range(len(population))),
                        format_func=lambda i: f"Individu {i + 1}",
                        key=(f"report_{field}_{run['seed']}_{len(population)}_"
                             f"{run['iterations']}_{run['group']}"),
                    )
                    positions = population[selected]
                    summary = state_summary(vehicles, positions, ship)
                    st.markdown(ship_scene(vehicles, positions, ship), unsafe_allow_html=True)
                    st.caption(f"Objective Rp {summary['objective']:g} jt · "
                               f"{summary['loaded']} kendaraan · berat "
                               f"{summary['weight']:g}/{ship.max_capacity}")


def ga_report(run, vehicles, ship):
    """Parameter, kurva maksimum/rata-rata, dan populasi yang diwajibkan untuk GA."""
    raw = run["raw"]
    cards([
        ("Jumlah populasi", raw["population_size"], "Individu per generasi"),
        ("Jumlah iterasi", run["iterations"], "Generasi setelah populasi awal"),
        ("Peluang mutasi", f"{raw['mutation_rate']:.0%}", "Parameter selama pencarian"),
    ], "algorithm-cards")
    st.markdown("#### Objective tiap generasi")
    draw_chart(history_chart(run), "report_ga_history")
    last = run["history"][-1]
    st.caption(f"Populasi terakhir: maksimum {last['maximum']:g} jt · "
               f"rata-rata {last['average']:.2f} jt.")
    st.info("Initial state yang ditampilkan adalah individu terbaik pada populasi awal. "
            "Final state adalah solusi terbaik sepanjang pencarian. Maksimum suatu "
            "generasi bisa turun; garis rekor terbaik tidak turun.")
    ga_populations(run, vehicles, ship)


def grouped_ga_rows(runs):
    """Menggabungkan pengulangan dengan parameter sama untuk analisis eksperimen."""
    groups = defaultdict(list)
    for run in runs:
        raw = run["raw"]
        key = (run["group"] or "Uji", raw["population_size"], run["iterations"],
               raw["mutation_rate"])
        groups[key].append(run)
    rows = []
    for (group, population, generations, mutation), records in sorted(groups.items()):
        objectives = [r["objective"] for r in records]
        rows.append({
            "Kelompok": group, "Populasi": population, "Generasi": generations,
            "Mutasi": mutation, "Jumlah run": len(records),
            "Seed": ", ".join(str(r["seed"]) for r in records),
            "Objective minimum": min(objectives),
            "Objective rata-rata": round(mean(objectives), 2),
            "Objective maksimum": max(objectives),
            "SD objective": round(stdev(objectives), 2) if len(records) > 1 else None,
            "Durasi rata-rata (s)": round(mean(r["duration"] for r in records), 4),
        })
    return rows


def ga_parameter_chart(rows, group):
    """Membandingkan perubahan generasi/populasi dari rata-rata setiap konfigurasi."""
    x_field = "Generasi" if group == "A" else "Populasi"
    rows = sorted(rows, key=lambda row: row[x_field])
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=[r[x_field] for r in rows], y=[r["Objective rata-rata"] for r in rows],
        mode="lines+markers", name="Objective rata-rata",
        line=dict(color="#49639A", width=3),
    ))
    figure.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="white", xaxis_title=x_field,
                         yaxis_title="Shipping fee · juta rupiah",
                         title=f"Pengaruh jumlah {x_field.lower()} · kelompok {group}")
    return figure


def experiment_report(bundle):
    """Tabel per run dan analisis parameter GA tidak dicampur dengan hasil HC."""
    runs = bundle["runs"]
    st.markdown("### Analisis eksperimen")
    st.caption("Grafik berikut membandingkan seluruh run pada sesi yang sama.")
    if len(runs) > 1:
        draw_chart(comparison_chart(runs), "report_comparison")
    if runs[0]["algorithm"] == "GA":
        rows = grouped_ga_rows(runs)
        st.markdown("#### Konsistensi pada parameter yang sama")
        st.dataframe(rows, hide_index=True, use_container_width=True)
        st.caption("SD adalah simpangan baku sampel objective antar-run. "
                   "Nilainya ditampilkan jika tersedia lebih dari satu run pada konfigurasi yang sama.")
        a_rows = [r for r in rows if r["Kelompok"] == "A"]
        b_rows = [r for r in rows if r["Kelompok"] == "B"]
        if a_rows and b_rows:
            group_a, group_b = st.tabs(["A · Variasi generasi", "B · Variasi populasi"])
            for tab, group, records in [(group_a, "A", a_rows), (group_b, "B", b_rows)]:
                with tab:
                    st.caption("Populasi dipertahankan; generasi divariasikan." if group == "A"
                               else "Generasi dipertahankan; populasi divariasikan.")
                    st.dataframe(records, hide_index=True, use_container_width=True)
                    draw_chart(ga_parameter_chart(records, group), f"report_group_{group}")
            st.caption("Konfigurasi kontrol ada pada kedua kelompok. Setiap baris "
                       "menunjukkan jumlah pengulangan yang benar-benar selesai.")
        else:
            st.caption("Untuk memenuhi matriks eksperimen GA pada tugas besar, gunakan "
                       "mode Eksperimen GA · 18 percobaan: tiga variasi generasi dan "
                       "tiga variasi populasi, masing-masing diulang tiga kali.")
    with st.expander("Bandingkan sesi HC dan GA pada dataset yang sama"):
        records = comparison_rows(Path(__file__).resolve().parents[2], bundle["dataset"])
        if records:
            st.dataframe(records, hide_index=True, use_container_width=True)
            if len({r["Algoritma"] for r in records}) > 1:
                figure = go.Figure()
                for name, color in [("HC", "#49639A"), ("GA", "#D77F84")]:
                    points = [r for r in records if r["Algoritma"] == name]
                    figure.add_trace(go.Scatter(
                        x=[r["Durasi (s)"] for r in points],
                        y=[r["Objective"] for r in points],
                        text=[f"Seed {r['Seed']} · {r['Kelompok']} · P{r['Populasi']} / G{r['Generasi']}"
                              for r in points],
                        mode="markers", name=name, marker=dict(color=color, size=9),
                        hovertemplate="%{text}<br>Durasi %{x:.4f} s<br>Objective %{y:g}<extra></extra>",
                    ))
                figure.update_layout(template="plotly_white", xaxis_title="Durasi (detik)",
                                     yaxis_title="Shipping fee (juta rupiah)",
                                     title="Objective dan durasi antaralgoritma")
                draw_chart(figure, "report_cross_algorithm")
            else:
                st.caption("Jalankan algoritma lainnya dengan dataset yang sama untuk menambahkan perbandingan.")
        else:
            st.caption("Perbandingan menggunakan sesi lengkap yang tersimpan di output.")
        st.caption("Data kapal dan kendaraan harus identik. Hasil terbaik yang ditemukan "
                   "belum merupakan bukti global optimum.")
    st.caption("Durasi HC tidak memasukkan inisialisasi state; durasi GA memasukkan "
               "pembuatan populasi awal, mengikuti pengukuran pada implementasi algoritma.")


def downloads(bundle):
    """Menyediakan hasil lengkap dan tabel CSV di panel hasil."""
    rows = summary_rows(bundle["runs"])
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    left, right = st.columns(2)
    left.download_button("Unduh hasil lengkap · JSON", export_json(bundle),
                         file_name="pararunten_session.json", mime="application/json",
                         use_container_width=True)
    right.download_button("Unduh ringkasan · CSV", buffer.getvalue(),
                          file_name="ringkasan_eksperimen.csv", mime="text/csv",
                          use_container_width=True)


def result_panel(bundle, run, vehicles, ship, index):
    """Hanya dipanggil bila hasil pencarian atau arsip benar-benar tersedia."""
    if not bundle or not run:
        return
    with st.container(key="results"):
        name = "Hill-Climbing with Sideways Move" if run["algorithm"] == "HC" else "Genetic Algorithm"
        st.html('<div id="hasil-pencarian"></div><h2 class="results-title">HASIL PENCARIAN</h2>'
                f'<p class="results-subtitle">{name}</p>')
        if len(bundle["runs"]) > 1:
            st.selectbox("Percobaan yang ditampilkan", list(range(len(bundle["runs"]))),
                         key="active_run",
                         format_func=lambda i: result_label(bundle["runs"][i], i))
        completed = len(bundle["runs"])
        expected = bundle.get("expected_runs", 3 if run["algorithm"] == "HC" else 18)
        if bundle.get("status", "complete") == "complete" and completed == expected:
            st.success(f"Selesai: {completed}/{expected} percobaan tersimpan.")
        else:
            st.warning(f"Sesi belum lengkap: {completed}/{expected} percobaan tercatat.")
            if bundle.get("error"):
                st.caption("Proses berhenti: " + bundle["error"])
        st.markdown("### Tabel ringkasan seluruh percobaan")
        st.dataframe(summary_rows(bundle["runs"]), hide_index=True, use_container_width=True)
        if bundle.get("folder"):
            st.caption("Arsip permanen: " + bundle["folder"])
        st.caption("Pilih percobaan di atas untuk melihat state, nilai, dan grafik run tersebut.")
        st.caption(f"Dataset: {bundle['dataset'].get('dataset_id', 'dataset')} · "
                   f"seed {run['seed']} · sumber: {bundle['source']}")
        end = state_summary(vehicles, run["final_state"], ship)
        initial = state_summary(vehicles, run["initial_state"], ship)
        cards([
            ("Shipping Fee", f"Rp {end['objective']:,.0f} jt",
             f"{end['objective'] - initial['objective']:+g} jt dari awal"),
            ("Kendaraan Dimuat", f"{end['loaded']} / {len(vehicles)}",
             f"{end['outside']} di luar · berat {end['weight']:g}/{ship.max_capacity}"),
            ("Durasi Pencarian", f"{run['duration']:.4f} s",
             "Waktu proses algoritma"),
        ], "result-cards")
        if run["algorithm"] == "HC":
            hc_report(run, bundle["runs"])
        else:
            ga_report(run, vehicles, ship)
        show_states(run, vehicles, ship)
        experiment_report(bundle)
        downloads(bundle)
