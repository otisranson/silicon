# Copyright 2026 Otis. Licensed under the Apache License, Version 2.0.
"""metrics — psutil data collection and smoothing for the silicon die visualizer."""

import random
from collections import deque

import psutil

LERP_FACTOR = 0.15
NOISE_SIZE = 90
HISTORY_LEN = 60
NOISE_DRIFT_STDDEV = 0.04
NOISE_CLAMP = 0.35


def lerp(a, b, t):
    return a + (b - a) * t


class Metrics:
    """Live per-core CPU load/frequency/temperature, lerp-smoothed, plus a
    slowly drifting per-transistor noise field so the die looks alive
    between the 250ms metric polls."""

    def __init__(self):
        self.physical_cores = psutil.cpu_count(logical=False) or 1
        self.logical_cores = psutil.cpu_count(logical=True) or self.physical_cores
        n = self.logical_cores

        # Primes psutil's internal comparison baseline — the first real
        # cpu_percent() call needs a prior sample to diff against.
        psutil.cpu_percent(percpu=True)

        self.load = [0.0] * n
        self.freq_mhz = [0.0] * n
        self.temp_c = [None] * n
        self.load_history = [deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN) for _ in range(n)]
        self.freq_history = [deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN) for _ in range(n)]
        self.noise = [
            [random.uniform(-NOISE_CLAMP, NOISE_CLAMP) for _ in range(NOISE_SIZE)]
            for _ in range(n)
        ]

        self.cpu_model = self._read_cpu_model()
        self.l3_size = self._read_l3_size()

    def poll(self):
        """Fetch fresh psutil data and lerp it toward the smoothed values.
        Call roughly every 250ms."""
        self._poll_load()
        self._poll_freq()
        self._poll_temp()

    def drift_noise(self):
        """Nudge every transistor's noise value with a small random walk.
        Call every render frame, independent of poll()."""
        for core_noise in self.noise:
            for i in range(len(core_noise)):
                v = core_noise[i] + random.gauss(0, NOISE_DRIFT_STDDEV)
                core_noise[i] = max(-NOISE_CLAMP, min(NOISE_CLAMP, v))

    # ---- individual polls ---------------------------------------------------

    def _poll_load(self):
        raw = psutil.cpu_percent(percpu=True)
        for i, v in enumerate(raw):
            if i >= len(self.load):
                break
            self.load[i] = lerp(self.load[i], v / 100.0, LERP_FACTOR)
            self.load_history[i].append(self.load[i])

    def _poll_freq(self):
        try:
            per_core = psutil.cpu_freq(percpu=True)
        except Exception:
            per_core = None

        if per_core and any(f is not None for f in per_core):
            for i, f in enumerate(per_core):
                if i >= len(self.freq_mhz) or f is None:
                    continue
                self.freq_mhz[i] = lerp(self.freq_mhz[i], f.current, LERP_FACTOR)
                self.freq_history[i].append(self.freq_mhz[i])
            return

        # No per-core reading available on this system — apply one global
        # frequency to every core instead.
        try:
            g = psutil.cpu_freq()
        except Exception:
            g = None
        if g is None:
            return
        for i in range(len(self.freq_mhz)):
            self.freq_mhz[i] = lerp(self.freq_mhz[i], g.current, LERP_FACTOR)
            self.freq_history[i].append(self.freq_mhz[i])

    def _poll_temp(self):
        try:
            temps = psutil.sensors_temperatures()
        except (AttributeError, psutil.AccessDenied, OSError):
            return
        if not temps:
            return
        core_temps = temps.get("coretemp") or temps.get("k10temp")
        if not core_temps:
            return
        # Best-effort index alignment — sensor label ordering isn't
        # guaranteed to match psutil's logical core ordering, especially
        # with hyperthreading (usually one temp entry per physical core).
        for i, entry in enumerate(core_temps):
            if i < len(self.temp_c):
                self.temp_c[i] = entry.current

    # ---- static info ---------------------------------------------------------

    def _read_cpu_model(self):
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
        return "Unknown CPU"

    def _read_l3_size(self):
        try:
            with open("/sys/devices/system/cpu/cpu0/cache/index3/size") as f:
                return f.read().strip()
        except OSError:
            return ""
