# CLAUDE.md — CPUVisualizer (silicon)

This file is read by Claude Code at session start. It is the source of truth for project state, decisions, and next steps. Update it after each meaningful session.

---

## What This Project Is

`silicon` — a real-time Linux desktop CPU die visualizer. Renders each CPU
core as a grid of animated "transistors" that shift color with live load,
laid out on a die outline with a ring bus, L3 cache strip, and memory
controller strip. Click a core to zoom in and see live load/frequency
history as sparklines. Styled like a silicon die shot — dark background,
green→amber→red heat ramp, monospace labels.

Stack: Python 3, GTK4 (PyGObject), Cairo for all drawing, psutil for CPU
metrics, `GLib.timeout_add` for the render loop (no threading).

Full original spec: given by the user as a single detailed prompt at
project creation (2026-07-30) — not saved verbatim anywhere in the repo,
but everything below was scaffolded directly from it. If behavior here
seems to deviate from what you'd expect, that prompt (in the session
history, not the repo) is the source of truth to check against, not
inference from the code.

---

## Repo Structure (current — matches spec)

```
CPUVisualizer/
├── CLAUDE.md
├── README.md
├── LICENSE           (Apache 2.0)
├── requirements.txt  (psutil, numpy — numpy currently unused, see below)
├── .gitignore
└── silicon/
    ├── silicon.py    — GTK4 app, window, input handling (click/keys), render loop
    ├── renderer.py   — all Cairo drawing: overview, core boxes, ring bus, L3, zoom, sparklines
    └── metrics.py    — psutil polling, lerp smoothing, per-transistor noise field
```

---

## Current State

- [x] Repo created on GitHub (`otisranson/CPUVisualizer`, public), initial commit pushed
- [x] `LICENSE` — Apache 2.0, copied verbatim from `UnconsciousClaude`'s verified copy
- [x] `metrics.py` — fully implemented: per-core load/freq/temp with lerp smoothing (factor 0.15), 60-point history deques for sparklines, 90-value per-core noise field with `drift_noise()` random walk, CPU model read from `/proc/cpuinfo`, L3 size read from `/sys/devices/system/cpu/cpu0/cache/index3/size`. **Actually run end-to-end this session** (see Testing Notes) — works correctly on this machine (AMD Ryzen 7 4800HS, 8C/16T).
- [x] `renderer.py` — fully implemented per spec: header, rounded die outline, per-core transistor grid (10×9 overview / 20×18 zoomed) with the exact `load_color()` ramp from the spec, gate lines above 40% load, dashed ring bus with tap circles, L3 cache bar strip with flash pulses, memory controller strip, footer summary, zoom mode with lerped rect/grid-size animation and a stats panel with sparklines, hit-testing for click-to-zoom. **Not runtime-tested** — see below.
- [x] `silicon.py` — fully implemented per spec: `Gtk.ApplicationWindow`, 920×580 fixed size, `Gtk.DrawingArea` with `set_draw_func`, `GLib.timeout_add` render loop at 33ms (tick) and a separate 250ms poll timer, `Gtk.GestureClick` for click-to-zoom, `Gtk.EventControllerKey` for Ctrl+Q/Ctrl+T/Escape. **Not runtime-tested** — see below.
- [x] `requirements.txt`, `README.md` (install/run/controls/known-limitations), `.gitignore`
- [x] Everything committed and pushed to `master`

### Testing notes — what's actually verified vs. not

This session ran in a sandboxed environment with **no GTK4 gir bindings installed** (`gir1.2-gtk-4.0` missing; confirmed via `gi.require_version("Gtk","4.0")` raising) and no real display/GPU (WSL2, no `/dev/dri`). So:

- **`metrics.py` was actually executed** (in a local `.venv` with `psutil`/`numpy` installed) and confirmed working: real per-core load/freq read, smoothing applied, noise drift running, history deques filling correctly. `temp_c` came back `None` for all cores on this machine — expected, no `coretemp` sensor exposed in this environment; the graceful-fallback path is what's actually exercised, not the populated-temperature path.
- **`renderer.py` and `silicon.py` were only syntax-checked** (`py_compile`), never actually run — no GTK4 available here to import `Gtk`. All the Cairo/Pango drawing code, the GTK4 window/widget wiring, click hit-testing, and keyboard shortcuts are unexecuted. They're written carefully against known GTK4/PyGObject API shapes (`Gtk.DrawingArea.set_draw_func`, `Gtk.GestureClick`, `Gtk.EventControllerKey`, `Gtk.ApplicationWindow`) but **have not been visually confirmed to work**.
- **First thing next session should do**, before anything else: install `python3-gi python3-gi-cairo gir1.2-gtk-4.0` (README has the exact command) and actually run `python3 silicon/silicon.py` on a real GNOME/X11-or-Wayland session. Expect some amount of debugging — this is untested GTK4 layout/drawing code written without ever seeing a frame render.

### Known deviations / limitations (see also README)

- **Always-on-top (Ctrl+T) is likely non-functional as shipped.** GTK4 removed `Gtk.Window.set_keep_above()` entirely — there's no portable stacking API on Wayland. The code checks `hasattr` and no-ops safely rather than crashing, but on stock GNOME/Wayland it almost certainly won't actually raise the window. A real fix needs [gtk4-layer-shell](https://github.com/wmww/gtk4-layer-shell), which is a separate system dependency not yet investigated or added.
- **`numpy` is in `requirements.txt` per the original spec but isn't actually imported anywhere** — the noise field uses plain Python lists + `random.gauss`. Left as a stated but unused dependency rather than removed, since the spec asked for it explicitly (framed as "optional but useful"); could be wired in for real if the per-transistor noise math needs to be vectorized for performance once it's actually rendering at 30fps.
- **Temperature-to-core index alignment is best-effort.** `psutil.sensors_temperatures()["coretemp"]` entries are zipped to cores by list index, which isn't guaranteed to match logical core ordering — most systems report one temp per physical core, not per thread, so on an HT/SMT machine roughly half the "cores" in the visualizer will show a temp that isn't really theirs (or none). Not fixed; flagged in the README too.
- **Core boxes are rendered one per *logical* core** (`psutil.cpu_count(logical=True)`), not one per physical core with HT pairs merged. This was a scaffolding-time judgment call (physical-core grouping would require assuming a specific sibling-ordering convention psutil doesn't guarantee) — worth revisiting once there's a real display to look at the layout on, especially on high-thread-count machines where this doubles the box count.

---

## Scope Ideas / Follow-ups

Not scheduled, not built — just captured so they aren't lost.

- **Real-time logic gate panel (2026-07-30).** User wants to see logic
  gates (AND/OR/XOR/NOT) with live inputs and outputs somewhere in the
  visualization. Important constraint discussed and agreed: there is no
  way to observe actual transistor/gate-level switching inside a running
  CPU from software — no OS or userspace hook exists for that, it's
  billions of silicon-level events per second with zero API surface. So
  this can't be "real" in the literal sense, and shouldn't be presented
  as if it were.
  What's actually buildable, and what we agreed is the right framing: a
  small illustrative gate circuit — a handful of AND/OR/XOR/NOT gates
  rendered near the die (candidate spot: next to or below the L3/memory
  strips) — whose *inputs* are derived from real live signals already in
  `metrics.py` (e.g. a core's load crossing some threshold, a
  frequency delta since last poll, the L3 flash-pulse boolean already
  computed in `renderer._draw_l3_cache`) and whose *outputs* are
  genuinely computed each frame by evaluating those gates against those
  inputs. This is the same honesty move the transistor grid already
  makes — not literal silicon, but a live-data-driven stylization of it,
  not a canned animation. Needs, before building: (1) pick which live
  signals feed the gate inputs, (2) decide the gate topology (how many
  gates, wired how, to what conceptual purpose — e.g. "did any core spike"
  style logic vs. something more elaborate), (3) decide where it lives in
  the 920×580 layout without crowding the existing die.

---

## Next Task

Get a real GTK4 environment (`sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0`), run `python3 silicon/silicon.py`, and actually look at it. Expect to be debugging previously-unexecuted code: layout math in `renderer.py` (box sizing, zoom interpolation, sparkline scaling) is the most likely place for visual bugs, since none of it has rendered a single frame yet. Confirm click-to-zoom and the keyboard shortcuts work before touching anything else. Always-on-top will need a real decision (accept it's non-functional on Wayland for now, or pull in gtk4-layer-shell) once the rest is confirmed working.

---

## Working Conventions

- Update the "Current State" checklist and add a dated session note here at the end of every session.
- This project was scaffolded end-to-end in a single session without ever running the GTK4 code — treat the "Testing notes" section above as load-bearing until it's updated to say otherwise.
