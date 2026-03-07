"""Qt widgets for the waterfall viewer."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QWidget,
)

from ground_station.dsp import COLORMAP, normalize_power_db


class WaterfallWidget(QWidget):
    """QImage-based scrolling spectrogram display."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fft_size = 1024
        self._history = 512
        self._db_min: float | None = None
        self._db_max: float | None = None
        self._buf = np.zeros((self._history, self._fft_size), dtype=np.uint8)
        self.setMinimumSize(512, 256)

    def set_fft_size(self, n: int) -> None:
        if n != self._fft_size:
            self._fft_size = n
            self._buf = np.zeros((self._history, self._fft_size), dtype=np.uint8)

    @Slot(np.ndarray)
    def add_line(self, power_db: np.ndarray) -> None:
        """Append a single FFT power line (dB) to the waterfall."""
        if power_db.shape[0] != self._fft_size:
            self.set_fft_size(power_db.shape[0])

        # Auto-scale: seed from first frame, then smooth-track
        line_min = float(np.min(power_db))
        line_max = float(np.max(power_db))
        if self._db_min is None:
            self._db_min = line_min
            self._db_max = line_max
        else:
            alpha = 0.05
            self._db_min += alpha * (line_min - self._db_min)
            self._db_max += alpha * (line_max - self._db_max)

        indices = normalize_power_db(power_db, self._db_min, self._db_max)

        # Scroll buffer up
        self._buf[:-1] = self._buf[1:]
        self._buf[-1] = indices

        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        w, h = self.width(), self.height()
        rgb = COLORMAP[self._buf]  # (history, fft_size, 3)
        rows, cols, _ = rgb.shape

        # Build RGBX (32-bit) buffer for QImage
        rgbx = np.zeros((rows, cols, 4), dtype=np.uint8)
        rgbx[:, :, :3] = rgb
        rgbx[:, :, 3] = 255

        img = QImage(rgbx.data, cols, rows, cols * 4, QImage.Format.Format_RGBX8888)
        # prevent dangling pointer
        img._numpy_ref = rgbx

        painter = QPainter(self)
        painter.drawImage(self.rect(), img)
        painter.end()


class ControlPanel(QWidget):
    """Sidebar controls for SDR parameters."""

    start_requested = Signal()
    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)

        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(70, 6000)
        self.freq_spin.setValue(868)
        self.freq_spin.setSuffix(" MHz")
        layout.addRow("Center Freq", self.freq_spin)

        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(1, 61)
        self.rate_spin.setValue(4)
        self.rate_spin.setSuffix(" MSPS")
        layout.addRow("Sample Rate", self.rate_spin)

        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setRange(0, 73)
        self.gain_slider.setValue(40)
        self.gain_label = QLabel("40 dB")
        self.gain_slider.valueChanged.connect(
            lambda v: self.gain_label.setText(f"{v} dB")
        )
        layout.addRow("RX Gain", self.gain_slider)
        layout.addRow("", self.gain_label)

        self.fft_combo = QComboBox()
        for size in (256, 512, 1024, 2048, 4096):
            self.fft_combo.addItem(str(size), size)
        self.fft_combo.setCurrentIndex(2)  # 1024
        layout.addRow("FFT Size", self.fft_combo)

        self.channel_combo = QComboBox()
        self.channel_combo.addItem("RX1", 0)
        self.channel_combo.addItem("RX2", 1)
        layout.addRow("RX Channel", self.channel_combo)

        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self._toggle)
        layout.addRow(self.start_btn)

        self._running = False
        self.setFixedWidth(220)

    def _toggle(self) -> None:
        if self._running:
            self._running = False
            self.start_btn.setText("Start")
            self.stop_requested.emit()
        else:
            self._running = True
            self.start_btn.setText("Stop")
            self.start_requested.emit()

    @property
    def center_freq_hz(self) -> int:
        return self.freq_spin.value() * 1_000_000

    @property
    def sample_rate_hz(self) -> int:
        return self.rate_spin.value() * 1_000_000

    @property
    def rx_gain_db(self) -> int:
        return self.gain_slider.value()

    @property
    def fft_size(self) -> int:
        return self.fft_combo.currentData()

    @property
    def rx_channel(self) -> int:
        return self.channel_combo.currentData()

    @Slot(list)
    def set_available_channels(self, channels: list[int]) -> None:
        """Populate the channel combo with only the hardware-supported channels."""
        current = self.channel_combo.currentData()
        self.channel_combo.clear()
        for ch in channels:
            self.channel_combo.addItem(f"RX{ch + 1}", ch)
        # Restore previous selection if still available
        idx = self.channel_combo.findData(current)
        if idx >= 0:
            self.channel_combo.setCurrentIndex(idx)
