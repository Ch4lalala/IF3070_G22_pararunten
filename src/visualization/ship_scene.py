"""Gambar SVG kapal dan mobil berdasarkan ukuran grid yang sebenarnya."""

import math
from html import escape
from src.init.constraints import direction_of_car

# Palet mengikuti contoh: merah, ungu, biru, dan kuning.
CAR_COLORS = ["#F4777C", "#CC8CEA", "#49639A", "#F3C955",
              "#5AAFA4", "#EA9A64", "#6A91B7", "#AD88A4"]


def car_svg(x, y, width, height, index, vehicle, title):
    """Menggambar ikon mobil tepat di dalam jejak persegi panjang kendaraan."""
    color = CAR_COLORS[index % len(CAR_COLORS)]
    horizontal = width > height
    short, long = min(width, height), max(width, height)
    angle = 90 if horizontal else 0
    label = escape(vehicle.id)
    return (
        f'<g class="car"><title>{escape(title)}</title>'
        f'<rect x="{x+.25}" y="{y+.25}" width="{max(.1,width-.5)}" '
        f'height="{max(.1,height-.5)}" rx="1" fill="{color}" fill-opacity=".17"/>'
        f'<g transform="translate({x+width/2} {y+height/2}) rotate({angle}) '
        f'scale({short/100} {long/200}) translate(-50 -100)">'
        '<rect x="1" y="36" width="14" height="36" rx="5" fill="#263640"/>'
        '<rect x="85" y="36" width="14" height="36" rx="5" fill="#263640"/>'
        '<rect x="1" y="132" width="14" height="36" rx="5" fill="#263640"/>'
        '<rect x="85" y="132" width="14" height="36" rx="5" fill="#263640"/>'
        f'<rect x="10" y="5" width="80" height="190" rx="20" fill="{color}" '
        'stroke="#FFFFFF" stroke-opacity=".9" stroke-width="3"/>'
        '<path d="M25 41 Q50 30 75 41 L73 68 Q50 62 27 68Z" '
        'fill="#DCEBF1" fill-opacity=".85"/>'
        '<path d="M27 141 Q50 149 73 141 L75 167 Q50 177 25 167Z" '
        'fill="#DCEBF1" fill-opacity=".75"/>'
        '<rect x="22" y="79" width="56" height="49" rx="8" fill="#FFFFFF" fill-opacity=".14"/>'
        '<path d="M18 82 V127 M82 82 V127" stroke="#FFFFFF" stroke-opacity=".6" stroke-width="3"/>'
        '<rect x="19" y="14" width="17" height="7" rx="3" fill="#FFF5CD"/>'
        '<rect x="64" y="14" width="17" height="7" rx="3" fill="#FFF5CD"/>'
        '<rect x="19" y="180" width="14" height="6" rx="2" fill="#B74551"/>'
        '<rect x="67" y="180" width="14" height="6" rx="2" fill="#B74551"/>'
        f'<text x="50" y="110" text-anchor="middle" font-size="18" '
        f'font-weight="700" fill="white">{label}</text></g></g>'
    )


def parking_layout(outside):
    """Menata semua kendaraan di luar dalam baris; tidak mengubah state."""
    if not outside:
        return [], 1, 1
    area = sum(v.dimensions.w * v.dimensions.l for _, v in outside)
    row_width = max(max(v.dimensions.w for _, v in outside), math.sqrt(area) * .75)
    x, y, row_height, used_width = 0, 0, 0, 0
    placements = []
    for index, vehicle in outside:
        w, l = vehicle.dimensions.w, vehicle.dimensions.l
        if x > 0 and x + w > row_width:
            x = 0
            y += row_height + .3
            row_height = 0
        placements.append((index, vehicle, x, y))
        used_width = max(used_width, x + w)
        x += w + .3
        row_height = max(row_height, l)
    return placements, used_width, y + row_height


def ship_scene(vehicles, positions, ship):
    """Menggambar kapal, grid W × L, mobil dimuat, dan parkiran di luar."""
    width, length = ship.dimensions.w, ship.dimensions.l
    cell = min(218 / width, 146 / length)
    deck_w, deck_h = width * cell, length * cell
    deck_x, deck_y = (400 - deck_w) / 2, 148 - deck_h / 2
    parts = [
        '<div class="ship-scene"><svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 400 330" role="img" aria-label="Kapal dengan geladak dan kendaraan">',
        '<rect x="1" y="1" width="398" height="328" fill="#9CD1C9" stroke="#344A49" stroke-width="1.5"/>',
        '<path d="M14 42h27m-20 7h28m292-12h28m-20 7h29M20 286h25m307-11h24" '
        'stroke="#BEE3DD" stroke-width="2" stroke-linecap="round" opacity=".65"/>',
        '<rect x="171" y="228" width="58" height="88" fill="#3C4446"/>',
        '<rect x="175" y="233" width="50" height="79" fill="#D2D6D4"/>',
        '<rect x="23" y="65" width="354" height="168" rx="84" fill="#7B4937"/>',
        '<rect x="46" y="77" width="308" height="144" rx="72" fill="#D99B74"/>',
        '<path d="M200 66v10m0 145v11" stroke="#E7BC99" stroke-width="1.5" opacity=".6"/>',
        f'<rect x="{deck_x}" y="{deck_y}" width="{deck_w}" height="{deck_h}" fill="#D0D2D1"/>',
    ]
    for i in range(width + 1):
        x = deck_x + i * cell
        parts.append(f'<path d="M{x} {deck_y}v{deck_h}" stroke="#555C5B" stroke-width=".65"/>')
    for j in range(length + 1):
        y = deck_y + j * cell
        parts.append(f'<path d="M{deck_x} {y}h{deck_w}" stroke="#555C5B" stroke-width=".65"/>')
    parts.append(f'<rect x="{deck_x}" y="{deck_y}" width="{deck_w}" height="{deck_h}" '
                 'fill="none" stroke="#303B3B" stroke-width="1.2"/>')
    if positions is not None:
        for index, (vehicle, position) in enumerate(zip(vehicles, positions)):
            if position is None:
                continue
            dim = direction_of_car(vehicle, position)
            x = deck_x + position.x * cell
            # Sumbu y pencarian naik ke atas; koordinat SVG naik ke bawah.
            y = deck_y + (length - position.y - dim.l) * cell
            title = (f"{vehicle.id} | {dim.w} × {dim.l} grid | ({position.x}, {position.y})"
                     f" | {position.orientation.value} | Rp {vehicle.shipping_fee:g} juta"
                     f" | berat {vehicle.weight:g} | ETA {vehicle.eta} hari")
            parts.append(car_svg(x, y, dim.w * cell, dim.l * cell, index, vehicle, title))
        outside = [(i, v) for i, (v, p) in enumerate(zip(vehicles, positions)) if p is None]
        placements, park_w, park_h = parking_layout(outside)
        scale = min(44 / park_w, 72 / park_h)
        for index, vehicle, x, y in placements:
            parts.append(car_svg(
                178 + x * scale, 236 + y * scale,
                vehicle.dimensions.w * scale, vehicle.dimensions.l * scale,
                index, vehicle,
                f"{vehicle.id} | Tidak dimuat | {vehicle.dimensions.w} × {vehicle.dimensions.l}"
                f" grid | Rp {vehicle.shipping_fee:g} juta | berat {vehicle.weight:g}",
            ))
        outside_text = f"DI LUAR · {len(outside)}"
    else:
        parts.append('<rect x="112" y="134" width="176" height="28" rx="6" '
                     'fill="#FFFFFF" fill-opacity=".92"/>'
                     '<text x="200" y="153" text-anchor="middle" font-size="12" '
                     'font-weight="600" fill="#455453">Menunggu hasil pencarian</text>')
        outside_text = "DI LUAR · —"
    parts.extend([
        f'<text x="16" y="23" fill="#345C56" font-size="9" font-weight="600">'
        f'GELADAK {width} × {length}</text>',
        f'<text x="385" y="23" text-anchor="end" fill="#345C56" font-size="9">'
        f'KAPASITAS {ship.max_capacity}</text>',
        f'<text x="200" y="325" text-anchor="middle" fill="#345C56" font-size="8">'
        f'{outside_text}</text></svg></div>',
    ])
    return "".join(parts)


def objective_svg(runs, selected=0):
    """Grafik responsif: HC tiap run, atau maksimum dan rata-rata GA terpilih."""
    if not runs:
        return ('<div class="objective-chart chart-empty"><span>Grafik objective</span>'
                '<small>Jalankan algoritma untuk melihat perkembangan nilai.</small></div>')
    run = runs[selected]
    series = []
    if run["algorithm"] == "GA":
        history = run["history"]
        x_values = [row["iteration"] for row in history]
        series = [
            ("Maksimum generasi", x_values, [r["maximum"] for r in history], "#49639A", False),
            ("Rata-rata populasi", x_values, [r["average"] for r in history], "#E19A54", False),
        ]
        best = []
        for row in history:
            best.append(max(row["maximum"], best[-1] if best else row["maximum"]))
        series.append(("Terbaik sepanjang pencarian", x_values, best, "#8C65AB", True))
    else:
        for i, record in enumerate(runs):
            series.append((f"Run {i+1} · seed {record['seed']}",
                           list(range(len(record["history"]))), record["history"],
                           ["#49639A", "#D77F84", "#64A798"][i % 3], False))
    max_x = max(1, max(max(s[1]) for s in series))
    values = [v for series_item in series for v in series_item[2]]
    low, high = min(values), max(values)
    padding = max(5, (high - low) * .2)
    low, high = max(0, low - padding), high + padding
    x0, y0, width, height = 68, 26, 850, 148
    def point(x, y):
        return x0 + x / max_x * width, y0 + (high - y) / (high - low) * height
    parts = ['<div class="objective-chart"><svg xmlns="http://www.w3.org/2000/svg" '
             'viewBox="0 0 1000 225" role="img" aria-label="Grafik objective terhadap iterasi">']
    for i in range(5):
        y = low + (high - low) * i / 4
        _, py = point(0, y)
        parts.append(f'<path d="M{x0} {py}h{width}" stroke="#E7ECEE" stroke-width="1"/>'
                     f'<text x="{x0-12}" y="{py+4}" text-anchor="end" font-size="10" fill="#7A858E">'
                     f'{y:g}</text>')
    for i in range(5):
        value = max_x * i / 4
        px, _ = point(value, low)
        parts.append(f'<text x="{px}" y="192" text-anchor="middle" font-size="10" '
                     f'fill="#7A858E">{value:g}</text>')
    for label, xs, ys, color, dashed in series:
        coordinates = []
        for index, (x, y) in enumerate(zip(xs, ys)):
            px, py = point(x, y)
            if index == 0:
                coordinates.append(f"M{px:.2f},{py:.2f}")
            elif run["algorithm"] == "HC":
                coordinates.append(f"H{px:.2f}V{py:.2f}")
            else:
                coordinates.append(f"L{px:.2f},{py:.2f}")
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        parts.append(f'<path d="{" ".join(coordinates)}" fill="none" stroke="{color}" '
                     f'stroke-width="2.4" stroke-linejoin="round"{dash}/>')
        # Riwayat satu nilai tetap mempunyai satu titik yang terlihat.
        end_x, end_y = point(xs[-1], ys[-1])
        parts.append(f'<circle cx="{end_x}" cy="{end_y}" r="2.8" fill="{color}"/>')
        # Tooltip bawaan SVG; tidak memerlukan JavaScript atau server lain.
        for x, y in zip(xs, ys):
            px, py = point(x, y)
            parts.append(f'<circle cx="{px}" cy="{py}" r="4" fill="{color}" opacity=".01">'
                         f'<title>{escape(label)} | iterasi {x} | objective {y:g}</title></circle>')
    parts.append('<text x="493" y="214" text-anchor="middle" font-size="10" fill="#7A858E">'
                 + ("Generasi" if run["algorithm"] == "GA" else "Iterasi") + '</text>'
                 '<text x="12" y="16" font-size="9" fill="#7A858E">Juta rupiah</text></svg>')
    parts.append('<div class="chart-legend">')
    for label, _, _, color, _ in series:
        parts.append(f'<span><i style="background:{color}"></i>{escape(label)}</span>')
    parts.append('</div></div>')
    return "".join(parts)
