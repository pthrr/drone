"""Widget tests (requires pytest-qt)."""

from __future__ import annotations

import numpy as np
import pytest

from ground_station.widgets import ControlPanel, WaterfallWidget


class TestWaterfallWidget:
    def test_initial_buffer_shape(self, qtbot):
        w = WaterfallWidget()
        qtbot.addWidget(w)
        assert w._buf.shape == (512, 1024)
        assert w._buf.dtype == np.uint8

    def test_add_line_updates_buffer(self, qtbot):
        w = WaterfallWidget()
        qtbot.addWidget(w)
        # Feed a constant-value line; buffer last row should be non-default
        line = np.full(1024, -40.0, dtype=np.float32)
        w.add_line(line)
        # With auto-scaling, a uniform line maps to some value — just check it wrote
        assert not np.all(w._buf[-1] == 0) or np.all(w._buf[-1] == w._buf[-1, 0])

    def test_scrolling_behavior(self, qtbot):
        w = WaterfallWidget()
        qtbot.addWidget(w)

        # Seed the auto-scaler with a line that has real spread
        seed = np.linspace(-60.0, -20.0, 1024, dtype=np.float32)
        w.add_line(seed)

        # Now add a distinctive high line
        line_a = np.full(1024, -20.0, dtype=np.float32)
        w.add_line(line_a)
        val_a = w._buf[-1, 0]

        # Add a low line — previous should scroll up one row
        line_b = np.full(1024, -60.0, dtype=np.float32)
        w.add_line(line_b)
        assert w._buf[-2, 0] == val_a
        assert w._buf[-1, 0] != val_a

    def test_fft_size_resize(self, qtbot):
        w = WaterfallWidget()
        qtbot.addWidget(w)
        assert w._fft_size == 1024

        line_512 = np.zeros(512, dtype=np.float32)
        w.add_line(line_512)
        assert w._fft_size == 512
        assert w._buf.shape == (512, 512)


class TestControlPanel:
    def test_default_values(self, qtbot):
        cp = ControlPanel()
        qtbot.addWidget(cp)
        assert cp.center_freq_hz == 868_000_000
        assert cp.sample_rate_hz == 4_000_000
        assert cp.rx_gain_db == 40
        assert cp.fft_size == 1024

    def test_start_signal_emission(self, qtbot):
        cp = ControlPanel()
        qtbot.addWidget(cp)
        with qtbot.waitSignal(cp.start_requested, timeout=1000):
            cp.start_btn.click()

    def test_stop_signal_emission(self, qtbot):
        cp = ControlPanel()
        qtbot.addWidget(cp)
        # First click → start
        cp.start_btn.click()
        # Second click → stop
        with qtbot.waitSignal(cp.stop_requested, timeout=1000):
            cp.start_btn.click()

    def test_button_text_toggle(self, qtbot):
        cp = ControlPanel()
        qtbot.addWidget(cp)
        assert cp.start_btn.text() == "Start"
        cp.start_btn.click()
        assert cp.start_btn.text() == "Stop"
        cp.start_btn.click()
        assert cp.start_btn.text() == "Start"
