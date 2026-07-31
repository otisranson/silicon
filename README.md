# silicon

A real-time CPU die visualizer for Linux, styled like a silicon die shot.
Each core is rendered as a grid of animated "transistors" that shift color
with live load, laid out on a die outline with a ring bus, L3 cache strip,
and memory controller. Click a core to zoom in and see its live load and
frequency history as sparklines.

Built with Python, GTK4 (PyGObject), and Cairo. No web view, no Electron —
native GTK4 window, drawn frame by frame on a `Gtk.DrawingArea`.

## Install

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0
pip install -r requirements.txt
```

## Run

```bash
python3 silicon/silicon.py
```

## Controls

- **Click a core** — zoom in on it (live load/freq sparklines, temp if available)
- **Escape** or **click outside the grid** — back to the overview
- **Ctrl+T** — toggle always-on-top
- **Ctrl+Q** — quit

## Known limitations

- **Always-on-top**: GTK4 removed `Gtk.Window.set_keep_above()` — Wayland
  doesn't expose a portable window-stacking API the way X11 did. Ctrl+T
  is wired up and will work if the method happens to be available on your
  GDK backend, but on stock GNOME/Wayland it's currently a no-op. A real
  floating overlay would need [gtk4-layer-shell](https://github.com/wmww/gtk4-layer-shell).
- **Temperature-to-core mapping**: `psutil.sensors_temperatures()["coretemp"]`
  entries are matched to cores by index, which isn't guaranteed to line up
  with logical core ordering — most systems expose one temperature per
  physical core, not per thread.
- Per-core frequency falls back to a single system-wide reading, applied
  to every core, on machines where `psutil.cpu_freq(percpu=True)` isn't
  supported.

## Layout

```
silicon/
  silicon.py   — GTK4 app, window, input handling, render loop
  renderer.py  — all Cairo drawing (die, cores, ring bus, L3, zoom, sparklines)
  metrics.py   — psutil polling, lerp smoothing, per-transistor noise field
LICENSE        — Apache 2.0
requirements.txt
```
