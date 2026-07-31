# Copyright 2026 Otis. Licensed under the Apache License, Version 2.0.
"""silicon — real-time CPU die visualizer. Entry point: GTK4 app, window,
input wiring, and the render loop."""

import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk

from metrics import Metrics
from renderer import Renderer

APP_ID = "org.otisranson.silicon"
WINDOW_WIDTH = 920
WINDOW_HEIGHT = 580
TICK_MS = 33  # ~30fps
POLL_MS = 250
ZOOM_FRAMES = 15


class SiliconWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="silicon")
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.set_resizable(False)

        self.metrics = Metrics()
        self.renderer = Renderer(self.metrics)

        self.zoomed_core = None
        self.zoom_progress = 0.0
        self.always_on_top = True

        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_content_width(WINDOW_WIDTH)
        self.drawing_area.set_content_height(WINDOW_HEIGHT)
        self.drawing_area.set_draw_func(self._on_draw)
        self.set_child(self.drawing_area)

        self._setup_transparency()
        self._setup_always_on_top()
        self._setup_click()
        self._setup_keys()

        GLib.timeout_add(POLL_MS, self._on_poll)
        GLib.timeout_add(TICK_MS, self._on_tick)

    # ---- rendering ------------------------------------------------------------

    def _on_draw(self, area, ctx, width, height):
        self.renderer.draw(ctx, width, height, self.zoomed_core, self.zoom_progress)

    def _on_tick(self):
        self.metrics.drift_noise()
        if self.zoomed_core is not None and self.zoom_progress < 1.0:
            self.zoom_progress = min(1.0, self.zoom_progress + 1.0 / ZOOM_FRAMES)
        elif self.zoomed_core is None and self.zoom_progress > 0.0:
            self.zoom_progress = max(0.0, self.zoom_progress - 1.0 / ZOOM_FRAMES)
        self.drawing_area.queue_draw()
        return True  # keep firing

    def _on_poll(self):
        self.metrics.poll()
        return True  # keep firing

    # ---- transparency / always-on-top ------------------------------------------

    def _setup_transparency(self):
        try:
            css = Gtk.CssProvider()
            css.load_from_data(b"window { background-color: transparent; }")
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception:
            self.set_opacity(0.95)

    def _setup_always_on_top(self):
        # GTK4 dropped Gtk.Window.set_keep_above — Wayland has no portable
        # window-stacking API, so this is best-effort and silently a no-op
        # where unavailable. A real overlay on GNOME/Wayland needs
        # gtk4-layer-shell; left as a follow-up.
        setter = getattr(self, "set_keep_above", None)
        if callable(setter):
            setter(self.always_on_top)

    # ---- input --------------------------------------------------------------

    def _setup_click(self):
        gesture = Gtk.GestureClick()
        gesture.connect("released", self._on_click)
        self.drawing_area.add_controller(gesture)

    def _on_click(self, gesture, n_press, x, y):
        if self.zoomed_core is not None:
            if self.renderer.hit_test(x, y) is None:
                self.zoomed_core = None
            return
        hit = self.renderer.hit_test(x, y)
        if hit is not None:
            self.zoomed_core = hit

    def _setup_keys(self):
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key)
        self.add_controller(controller)

    def _on_key(self, controller, keyval, keycode, state):
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl and keyval == Gdk.KEY_q:
            self.close()
            return True
        if ctrl and keyval == Gdk.KEY_t:
            self.always_on_top = not self.always_on_top
            self._setup_always_on_top()
            return True
        if keyval == Gdk.KEY_Escape:
            self.zoomed_core = None
            return True
        return False


class SiliconApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SiliconWindow(self)
        win.present()


def main():
    app = SiliconApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
