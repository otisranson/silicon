# Copyright 2026 Otis. Licensed under the Apache License, Version 2.0.
"""renderer — all Cairo drawing logic for the silicon die visualizer."""

import math
import time

import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Pango, PangoCairo

BG_COLOR = (0.02, 0.02, 0.03)
DIE_COLOR = (0.05, 0.05, 0.07)
DIE_BORDER = (0.15, 0.18, 0.16)
CORE_BG = (0.04, 0.04, 0.05)
RING_BUS_COLOR = (0.11, 0.235, 0.157)  # #1c3c28
TEXT_COLOR = (0.75, 0.78, 0.75)
TEXT_DIM = (0.45, 0.48, 0.45)

CORES_PER_ROW = 4
OVERVIEW_GRID = (10, 9)  # cols, rows
ZOOM_GRID = (20, 18)


def lerp(a, b, t):
    return a + (b - a) * t


def load_color(load):
    l = max(0.0, min(1.0, load))
    if l < 0.33:
        t = l / 0.33
        r = lerp(0.04, 0.10, t)
        g = lerp(0.15, 0.63, t)
        b = lerp(0.07, 0.25, t)
    elif l < 0.66:
        t = (l - 0.33) / 0.33
        r = lerp(0.10, 0.91, t)
        g = lerp(0.63, 0.63, t)
        b = lerp(0.25, 0.08, t)
    else:
        t = (l - 0.66) / 0.34
        r = lerp(0.91, 1.0, t)
        g = lerp(0.63, 0.28, t)
        b = lerp(0.08, 0.09, t)
    return (r, g, b)


class Renderer:
    """Owns all Cairo drawing for both the overview and zoomed-core views.
    `hit_test()` reads back the rects computed by the last overview draw
    so the caller (silicon.py) can turn a click into a core index."""

    def __init__(self, metrics):
        self.metrics = metrics
        self.core_rects = {}  # core index -> (x, y, w, h) from the last overview draw

    # ---- text ---------------------------------------------------------------

    def _text(self, ctx, x, y, text, size=11, color=TEXT_COLOR, bold=False, align="left"):
        layout = PangoCairo.create_layout(ctx)
        weight = "bold" if bold else "normal"
        layout.set_font_description(Pango.FontDescription(f"Monospace {weight} {size}"))
        layout.set_text(text, -1)
        _ink, logical = layout.get_pixel_extents()
        tx = x
        if align == "right":
            tx = x - logical.width
        elif align == "center":
            tx = x - logical.width / 2
        ctx.save()
        ctx.set_source_rgb(*color)
        ctx.move_to(tx, y)
        PangoCairo.show_layout(ctx, layout)
        ctx.restore()

    # ---- top-level ------------------------------------------------------------

    def draw(self, ctx, width, height, zoomed_core, zoom_t):
        ctx.set_source_rgb(*BG_COLOR)
        ctx.paint()

        if zoomed_core is not None and zoom_t > 0.0:
            self._draw_zoomed(ctx, width, height, zoomed_core, zoom_t)
        else:
            self._draw_overview(ctx, width, height)

    # ---- overview ---------------------------------------------------------

    def _draw_overview(self, ctx, width, height):
        m = self.metrics
        margin = 20
        header_h = 36
        footer_h = 24

        self._draw_header(ctx, width, header_h)

        die_x = margin
        die_y = header_h + 10
        die_w = width - margin * 2
        die_h = height - header_h - footer_h - 30

        self._rounded_rect(ctx, die_x, die_y, die_w, die_h, 10)
        ctx.set_source_rgb(*DIE_COLOR)
        ctx.fill_preserve()
        ctx.set_source_rgb(*DIE_BORDER)
        ctx.set_line_width(1.5)
        ctx.stroke()

        n = m.logical_cores
        rows = math.ceil(n / CORES_PER_ROW)
        pad = 14
        grid_top = die_y + pad
        bus_h = 14
        l3_h = 34
        mem_h = 20
        available_h = die_h - pad * 2 - bus_h - l3_h - mem_h - 20
        box_h = max(60, available_h / max(rows, 1))
        box_w = (die_w - pad * 2) / CORES_PER_ROW - 8

        self.core_rects = {}
        for i in range(n):
            row = i // CORES_PER_ROW
            col = i % CORES_PER_ROW
            bx = die_x + pad + col * (box_w + 8)
            by = grid_top + row * (box_h + 8)
            self.core_rects[i] = (bx, by, box_w, box_h)
            self._draw_core_box(ctx, i, bx, by, box_w, box_h, OVERVIEW_GRID)

        bus_y = grid_top + rows * (box_h + 8) + 6
        self._draw_ring_bus(ctx, die_x + pad, bus_y, die_w - pad * 2, n)

        l3_y = bus_y + bus_h + 6
        self._draw_l3_cache(ctx, die_x + pad, l3_y, die_w - pad * 2, l3_h)

        mem_y = l3_y + l3_h + 6
        self._draw_memory_controller(ctx, die_x + pad, mem_y, die_w - pad * 2, mem_h)

        self._draw_footer(ctx, width, height - footer_h + 4, n)

    def _draw_header(self, ctx, width, header_h):
        m = self.metrics
        avg_load = sum(m.load) / max(len(m.load), 1) * 100
        avg_freq = sum(m.freq_mhz) / max(len(m.freq_mhz), 1) / 1000.0
        clock = time.strftime("%H:%M:%S")
        left = f"{m.cpu_model}  ·  {m.physical_cores}C/{m.logical_cores}T"
        right = f"avg {avg_load:4.1f}%  ·  {avg_freq:.2f} GHz  ·  {clock}"
        self._text(ctx, 20, 10, left, size=11, bold=True)
        self._text(ctx, width - 20, 10, right, size=11, color=TEXT_DIM, align="right")

    def _draw_footer(self, ctx, width, y, n):
        m = self.metrics
        parts = [f"C{i}:{m.load[i] * 100:.0f}%" for i in range(n)]
        self._text(ctx, 20, y, "  ".join(parts), size=9, color=TEXT_DIM)

    # ---- core box -------------------------------------------------------------

    def _draw_core_box(self, ctx, index, x, y, w, h, grid, noise_scale=1.0):
        m = self.metrics
        load = m.load[index] if index < len(m.load) else 0.0
        freq = m.freq_mhz[index] if index < len(m.freq_mhz) else 0.0
        temp = m.temp_c[index] if index < len(m.temp_c) else None
        noise = m.noise[index] if index < len(m.noise) else [0.0]

        ctx.set_source_rgb(*CORE_BG)
        ctx.rectangle(x, y, w, h)
        ctx.fill()

        label_h = 16
        bar_h = 6
        grid_top = y + label_h
        grid_bottom = y + h - bar_h - 14
        grid_area_h = max(grid_bottom - grid_top, 10)
        grid_area_w = w - 8

        cols, rows_ = grid
        cell_w = grid_area_w / cols
        cell_h = grid_area_h / rows_
        cell = min(cell_w, cell_h)
        gx = x + 4 + (grid_area_w - cell * cols) / 2
        gy = grid_top + (grid_area_h - cell * rows_) / 2

        for cy in range(rows_):
            for cx in range(cols):
                idx = cy * cols + cx
                n = noise[idx % len(noise)] * noise_scale
                effective = max(0.0, min(1.0, load + n))
                r, g, b = load_color(effective)
                ctx.set_source_rgb(r, g, b)
                px = gx + cx * cell
                py = gy + cy * cell
                ctx.rectangle(px, py, max(cell - 1, 1), max(cell - 1, 1))
                ctx.fill()
                if load > 0.4:
                    ctx.set_source_rgba(0, 0, 0, 0.35)
                    ctx.set_line_width(1)
                    ctx.move_to(px, py + cell / 2)
                    ctx.line_to(px + cell - 1, py + cell / 2)
                    ctx.stroke()

        self._text(ctx, x + 4, y + 2, f"C{index}", size=8, color=TEXT_DIM)
        self._text(ctx, x + w - 4, y + 2, f"{load * 100:.0f}%", size=8,
                    color=load_color(load), align="right")

        bar_y = y + h - bar_h - 4
        ctx.set_source_rgba(1, 1, 1, 0.08)
        ctx.rectangle(x + 4, bar_y, w - 8, bar_h)
        ctx.fill()
        freq_ratio = min(freq / 5000.0, 1.0) if freq else 0.0
        ctx.set_source_rgb(*load_color(load))
        ctx.rectangle(x + 4, bar_y, (w - 8) * freq_ratio, bar_h)
        ctx.fill()

        ghz = freq / 1000.0 if freq else 0.0
        self._text(ctx, x + 4, y + h - 14, f"{ghz:.2f}GHz", size=7, color=TEXT_DIM)
        if temp is not None:
            self._text(ctx, x + w - 4, y + h - 14, f"{temp:.0f}°C", size=7,
                        color=TEXT_DIM, align="right")

    # ---- ring bus / l3 / memory ------------------------------------------------

    def _draw_ring_bus(self, ctx, x, y, w, n):
        ctx.set_source_rgb(*RING_BUS_COLOR)
        ctx.set_line_width(1.5)
        ctx.set_dash([6, 4])
        ctx.move_to(x, y)
        ctx.line_to(x + w, y)
        ctx.stroke()
        ctx.set_dash([])

        cols = min(n, CORES_PER_ROW)
        for i in range(cols):
            cx = x + (i + 0.5) * (w / cols)
            ctx.arc(cx, y, 2.5, 0, 2 * math.pi)
            ctx.fill()

    def _draw_l3_cache(self, ctx, x, y, w, h):
        m = self.metrics
        bars = 40
        avg_load = sum(m.load) / max(len(m.load), 1)
        bar_w = w / bars
        noise_source = m.noise[0] if m.noise else [0.0]
        for i in range(bars):
            n = noise_source[i % len(noise_source)]
            bh = max(2, (avg_load + n * 0.5) * h)
            flash = (int(time.time() * 4) + i) % 40 == 0
            color = (0.3, 1.0, 0.5) if flash else load_color(avg_load)
            ctx.set_source_rgb(*color)
            ctx.rectangle(x + i * bar_w, y + h - bh, max(bar_w - 1, 1), bh)
            ctx.fill()
        label = "L3 UNIFIED CACHE"
        if m.l3_size:
            label += f"  {m.l3_size}"
        self._text(ctx, x, y - 10, label, size=8, color=TEXT_DIM)

    def _draw_memory_controller(self, ctx, x, y, w, h):
        m = self.metrics
        avg_load = sum(m.load) / max(len(m.load), 1)
        r, g, b = load_color(avg_load)
        ctx.set_source_rgba(r, g, b, 0.6)
        ctx.rectangle(x, y, w * min(avg_load * 1.2, 1.0), h)
        ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.06)
        ctx.rectangle(x, y, w, h)
        ctx.set_line_width(1)
        ctx.stroke()
        self._text(ctx, x, y - 4, "MEMORY CONTROLLER", size=8, color=TEXT_DIM)

    # ---- zoom -------------------------------------------------------------

    def hit_test(self, x, y):
        for index, (bx, by, bw, bh) in self.core_rects.items():
            if bx <= x <= bx + bw and by <= y <= by + bh:
                return index
        return None

    def _draw_zoomed(self, ctx, width, height, index, t):
        m = self.metrics
        if index >= len(m.load):
            return

        panel_w = width * 0.35
        grid_w = width - panel_w - 60
        grid_h = height - 80

        # Interpolate from the overview box's rect to the full zoomed rect
        # over ZOOM_FRAMES frames (driven by t, owned by silicon.py).
        start = self.core_rects.get(index, (20, 60, 200, 200))
        end = (20, 60, grid_w, grid_h)
        x = lerp(start[0], end[0], t)
        y = lerp(start[1], end[1], t)
        w = lerp(start[2], end[2], t)
        h = lerp(start[3], end[3], t)

        grid = tuple(int(lerp(a, b, t)) for a, b in zip(OVERVIEW_GRID, ZOOM_GRID))
        self._draw_core_box(ctx, index, x, y, w, h, grid, noise_scale=lerp(1.0, 2.2, t))

        if t > 0.85:
            self._draw_stats_panel(ctx, index, width - panel_w + 20, 60, panel_w - 40, grid_h)

    def _draw_stats_panel(self, ctx, index, x, y, w, h):
        m = self.metrics
        load = m.load[index]
        freq = m.freq_mhz[index]
        temp = m.temp_c[index] if index < len(m.temp_c) else None

        self._text(ctx, x, y, f"CORE {index}", size=14, bold=True)

        self._text(ctx, x, y + 26, f"LOAD  {load * 100:5.1f}%", size=11, color=load_color(load))
        self._draw_sparkline(ctx, list(m.load_history[index]), x, y + 44, w, 50, load_color(load))

        self._text(ctx, x, y + 110, f"FREQ  {freq / 1000:5.2f} GHz", size=11)
        self._draw_sparkline(ctx, list(m.freq_history[index]), x, y + 128, w, 50,
                              (0.6, 0.7, 1.0), normalize=True)

        if temp is not None:
            self._text(ctx, x, y + 194, f"TEMP  {temp:5.1f} °C", size=11, color=TEXT_DIM)

    def _draw_sparkline(self, ctx, values, x, y, w, h, color, normalize=False):
        if not values:
            return
        vmax = max(values) if normalize else 1.0
        vmax = vmax or 1.0
        ctx.set_source_rgba(1, 1, 1, 0.06)
        ctx.rectangle(x, y, w, h)
        ctx.fill()
        ctx.set_source_rgb(*color)
        ctx.set_line_width(1.2)
        n = len(values)
        for i, v in enumerate(values):
            px = x + (i / max(n - 1, 1)) * w
            py = y + h - (min(v / vmax, 1.0) * h)
            if i == 0:
                ctx.move_to(px, py)
            else:
                ctx.line_to(px, py)
        ctx.stroke()

    # ---- shapes -------------------------------------------------------------

    def _rounded_rect(self, ctx, x, y, w, h, r):
        ctx.new_sub_path()
        ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        ctx.close_path()
