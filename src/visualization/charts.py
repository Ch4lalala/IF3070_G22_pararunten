"""Gambar interaktif geladak, area luar, dan grafik pencarian."""

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

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


def all_histories_chart(runs, field="maximum"):
    """Membandingkan riwayat tiap run; untuk GA memakai maksimum generasi."""
    fig = go.Figure()
    for number, run in enumerate(runs, 1):
        history = run["history"]
        x = [row["iteration"] for row in history] if run["algorithm"] == "GA" else list(range(len(history)))
        y = [row[field] for row in history] if run["algorithm"] == "GA" else history
        fig.add_trace(go.Scatter(
            x=x, y=y, name=f"Run {number} · seed {run['seed']}",
            mode="lines", line=dict(width=2, shape="linear" if run["algorithm"] == "GA" else "hv"),
        ))
    base_layout(fig, 380)
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title="Generasi" if runs[0]["algorithm"] == "GA" else "Iterasi")
    fig.update_yaxes(title="Shipping fee · juta rupiah", rangemode="tozero")
    return fig


def sa_exponential_chart(runs):
    """Grafik exp(delta/T) tanpa pembatas 1, dengan koordinat log10 yang stabil."""
    figure = go.Figure()
    bounds = []
    for number, run in enumerate(runs, 1):
        raw = run["raw"]
        values, details = [], []
        for delta, temperature in zip(raw["deltas"], raw["temperatures"]):
            if delta is None:
                values.append(None)
                details.append([None, temperature, "Tidak ada kandidat"])
            else:
                value = delta / temperature / math.log(10)
                values.append(value)
                bounds.append(value)
                details.append([delta, temperature, f"10^({value:.5g})"])
        figure.add_trace(go.Scatter(
            x=list(range(1, len(values) + 1)), y=values, customdata=details,
            mode="lines", name=f"Run {number} · seed {run['seed']}", connectgaps=False,
            line=dict(width=1.5),
            hovertemplate="Iterasi %{x}<br>Delta %{customdata[0]:g}<br>T %{customdata[1]:.6g}"
                          "<br>exp(delta/T) = %{customdata[2]}<extra>%{fullData.name}</extra>",
        ))
    low, high = (min(bounds), max(bounds)) if bounds else (-1, 1)
    if low == high:
        low, high = low - 1, high + 1
    step = (high - low) / 5
    ticks = [low + step * i for i in range(6)]
    base_layout(figure, 400)
    figure.update_xaxes(title="Iterasi")
    figure.update_yaxes(title="exp(delta/T) · skala logaritmik", tickmode="array",
                       tickvals=ticks, ticktext=[f"10<sup>{value:.3g}</sup>" for value in ticks])
    figure.update_layout(title="Eksponensial SA terhadap iterasi")
    if not bounds:
        figure.add_annotation(text="Belum ada kandidat yang dapat dihitung", x=.5, y=.5,
                              xref="paper", yref="paper", showarrow=False)
    return figure


def ga_configuration_chart(runs):
    """Dua kurva wajib GA, dibandingkan antar-pengulangan konfigurasi yang sama."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Maksimum objective", "Rata-rata populasi"))
    for number, run in enumerate(runs):
        history = run["history"]
        color = COLORS[number % len(COLORS)]
        for column, field in [(1, "maximum"), (2, "average")]:
            fig.add_trace(go.Scatter(x=[row["iteration"] for row in history],
                y=[row[field] for row in history], mode="lines", name=f"Seed {run['seed']}",
                legendgroup=str(run["seed"]), showlegend=column == 1,
                line=dict(color=color, width=2)), row=1, col=column)
    base_layout(fig, 420)
    fig.update_xaxes(title_text="Generasi (0 = populasi awal)")
    fig.update_yaxes(title_text="Shipping fee (juta rupiah)", rangemode="tozero")
    return fig
