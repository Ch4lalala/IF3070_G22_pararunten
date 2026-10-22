"""Gambar interaktif geladak, area luar, dan grafik pencarian."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.init.constraints import direction_of_car

# Warna berdasarkan indeks kendaraan dalam dataset, sehingga selalu konsisten.
COLORS = ["#147D79", "#E89046", "#5479AD", "#9D6FA5", "#CBB453",
          "#599C85", "#C96966", "#648D9F", "#A0865E", "#7976AD"]
INK = "#183344"


def base_layout(fig, height=380):
    """Memberi tema, margin, dan garis grid yang seragam."""
    fig.update_layout(
        template="plotly_white", height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#F7FAF9",
        font=dict(family="Arial, sans-serif", color=INK, size=12),
        margin=dict(l=28, r=18, t=28, b=35),
        legend=dict(orientation="h", y=-.2, x=0),
        hoverlabel=dict(bgcolor=INK, font_color="white"),
    )
    fig.update_xaxes(gridcolor="#E3ECE8", zeroline=False)
    fig.update_yaxes(gridcolor="#E3ECE8", zeroline=False)
    return fig


def add_vehicle(fig, vehicle, index, x, y, width, length, orientation, outside=False):
    """Menggambar kendaraan, label ID, dan informasi saat disorot."""
    color = COLORS[index % len(COLORS)]
    fig.add_shape(
        type="rect", x0=x + .05, y0=y + .05,
        x1=x + width - .05, y1=y + length - .05,
        fillcolor=color, line=dict(color="white", width=1.5),
    )
    text = (f"<b>{vehicle.id}</b><br>{width} × {length} grid · {orientation}"
            f"<br>Tarif: {vehicle.shipping_fee:g} juta rupiah"
            f"<br>Berat: {vehicle.weight:g} unit · ETA: {vehicle.eta} hari")
    if outside:
        text += "<br>Tidak dimuat · koordinat hanya untuk tampilan"
    else:
        text += f"<br>Koordinat: ({x}, {y})"
    # Titik hover transparan memenuhi badan kendaraan.
    hover_x = [x + a + .5 for a in range(width) for b in range(length)]
    hover_y = [y + b + .5 for a in range(width) for b in range(length)]
    fig.add_trace(go.Scatter(
        x=hover_x, y=hover_y, mode="markers", showlegend=False,
        marker=dict(size=18, color="rgba(0,0,0,0)"),
        hovertemplate=text + "<extra></extra>",
    ))
    fig.add_annotation(
        x=x + width / 2, y=y + length / 2,
        text=f"<b>{vehicle.id}</b>", showarrow=False,
        font=dict(color="white", size=12),
    )


def deck_chart(vehicles, positions, ship):
    """Menampilkan geladak dengan sel kosong, posisi, dan ukuran terorientasi."""
    fig = go.Figure()
    width, length = ship.dimensions.w, ship.dimensions.l
    for index, (vehicle, position) in enumerate(zip(vehicles, positions)):
        if position is not None:
            dim = direction_of_car(vehicle, position)
            add_vehicle(fig, vehicle, index, position.x, position.y, dim.w, dim.l,
                        position.orientation.value)
    fig.add_shape(type="rect", x0=0, y0=0, x1=width, y1=length,
                  line=dict(color=INK, width=2), fillcolor="rgba(0,0,0,0)")
    base_layout(fig, 395)
    fig.update_xaxes(range=[-.3, width + .3], dtick=1, title="x · lebar geladak",
                     constrain="domain", fixedrange=True)
    fig.update_yaxes(range=[-.3, length + .3], dtick=1, title="y · panjang geladak",
                     scaleanchor="x", scaleratio=1, constrain="domain", fixedrange=True)
    return fig


def outside_chart(vehicles, positions, ship):
    """Menggambar kendaraan di luar; None pada state tidak diubah."""
    fig = go.Figure()
    outside = [(i, v) for i, (v, p) in enumerate(zip(vehicles, positions)) if p is None]
    if not outside:
        fig.add_annotation(x=.5, y=.5, xref="paper", yref="paper",
                           text="Semua kendaraan sudah dimuat", showarrow=False)
        base_layout(fig, 220)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig
    # Penataan ini hanya untuk gambar area tunggu; memakai dimensi asli.
    row_width = max(ship.dimensions.w, max(v.dimensions.w for _, v in outside))
    x, y, row_height = 0, 0, 0
    for index, vehicle in outside:
        w, l = vehicle.dimensions.w, vehicle.dimensions.l
        if x > 0 and x + w > row_width:
            x = 0
            y += row_height + 1
            row_height = 0
        add_vehicle(fig, vehicle, index, x, y, w, l, "dimensi asli", outside=True)
        x += w + 1
        row_height = max(row_height, l)
    total_height = y + row_height
    base_layout(fig, min(650, max(250, int(300 * total_height / row_width))))
    fig.update_xaxes(range=[-.3, row_width + .3], visible=False, constrain="domain")
    fig.update_yaxes(range=[total_height + .3, -.3], visible=False,
                     scaleanchor="x", scaleratio=1, constrain="domain")
    return fig


def history_chart(run):
    """Menggambar riwayat HC atau maksimum/rata-rata setiap generasi GA."""
    fig = go.Figure()
    if run["algorithm"] == "HC":
        fig.add_trace(go.Scatter(
            x=list(range(len(run["history"]))), y=run["history"],
            name="Objective", mode="lines",
            line=dict(color="#147D79", width=3, shape="hv"),
            fill="tozeroy", fillcolor="rgba(20,125,121,.07)",
        ))
    else:
        history = run["history"]
        x = [row["iteration"] for row in history]
        maximum = [row["maximum"] for row in history]
        best = []
        for value in maximum:
            best.append(max(value, best[-1] if best else value))
        for name, values, color, dash in [
            ("Maksimum generasi", maximum, "#147D79", "solid"),
            ("Rata-rata populasi", [r["average"] for r in history], "#E89046", "solid"),
            ("Terbaik sepanjang pencarian", best, "#5479AD", "dot"),
        ]:
            fig.add_trace(go.Scatter(x=x, y=values, name=name, mode="lines",
                                     line=dict(color=color, width=2.5, dash=dash)))
    base_layout(fig, 355)
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title="Generasi (0 = populasi awal)" if run["algorithm"] == "GA"
                     else "Iterasi (0 = state awal)", rangemode="tozero")
    fig.update_yaxes(title="Shipping fee · juta rupiah", rangemode="tozero")
    return fig


def comparison_chart(runs):
    """Membandingkan objective dan durasi run dalam satu sesi."""
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Objective hasil", "Durasi pencarian"))
    labels = [f"Run {i + 1}" for i in range(len(runs))]
    for col, key, color in [(1, "objective", "#147D79"), (2, "duration", "#E89046")]:
        fig.add_trace(go.Bar(
            x=labels, y=[r[key] for r in runs], marker_color=color, showlegend=False,
            customdata=[r["seed"] for r in runs],
            hovertemplate="%{x}<br>Seed %{customdata}<br>%{y:.3f}<extra></extra>",
        ), row=1, col=col)
    base_layout(fig, 320)
    fig.update_yaxes(title_text="Juta rupiah", row=1, col=1)
    fig.update_yaxes(title_text="Detik", row=1, col=2)
    return fig


def all_histories_chart(runs):
    """Membandingkan riwayat tiap run; untuk GA memakai maksimum generasi."""
    fig = go.Figure()
    for number, run in enumerate(runs, 1):
        history = run["history"]
        x = [row["iteration"] for row in history] if run["algorithm"] == "GA" else list(range(len(history)))
        y = [row["maximum"] for row in history] if run["algorithm"] == "GA" else history
        fig.add_trace(go.Scatter(
            x=x, y=y, name=f"Run {number} · seed {run['seed']}",
            mode="lines", line=dict(width=2, shape="linear" if run["algorithm"] == "GA" else "hv"),
        ))
    base_layout(fig, 380)
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title="Generasi" if runs[0]["algorithm"] == "GA" else "Iterasi")
    fig.update_yaxes(title="Shipping fee · juta rupiah", rangemode="tozero")
    return fig
