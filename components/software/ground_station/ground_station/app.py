"""Application wiring: MainWindow + entry point."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QMetaObject, QThread, Qt, Slot
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget

from ground_station.model import SdrModel
from ground_station.widgets import ControlPanel, WaterfallWidget
from ground_station.workers import DemoWorker, SdrWorker, Worker


class MainWindow(QMainWindow):
    """Top-level window: waterfall + control panel."""

    def __init__(self, worker: Worker, model: SdrModel) -> None:
        super().__init__()
        self.setWindowTitle("Ground Station — Waterfall Viewer")
        self.resize(900, 500)

        self._worker = worker
        self._model = model
        self._thread = QThread()
        worker.moveToThread(self._thread)

        # Widgets
        self._waterfall = WaterfallWidget()
        self._controls = ControlPanel()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self._waterfall, stretch=1)
        layout.addWidget(self._controls)
        self.setCentralWidget(central)

        # Signals
        worker.data_ready.connect(
            self._waterfall.add_line, Qt.ConnectionType.QueuedConnection
        )
        worker.error.connect(self._on_error, Qt.ConnectionType.QueuedConnection)
        worker.channels_available.connect(
            self._controls.set_available_channels, Qt.ConnectionType.QueuedConnection
        )
        self._controls.start_requested.connect(self._start_worker)
        self._controls.stop_requested.connect(
            worker.stop, Qt.ConnectionType.QueuedConnection
        )

        # Sync parameters when controls change
        self._controls.freq_spin.valueChanged.connect(self._sync_params)
        self._controls.rate_spin.valueChanged.connect(self._sync_params)
        self._controls.gain_slider.valueChanged.connect(self._sync_params)
        self._controls.fft_combo.currentIndexChanged.connect(self._sync_params)
        self._controls.channel_combo.currentIndexChanged.connect(self._sync_params)

        self._thread.start()

        # Auto-start rx immediately
        self._controls._running = True
        self._controls.start_btn.setText("Stop")
        self._start_worker()

    def _sync_params(self) -> None:
        fft_size = self._controls.fft_size
        rx_channel = self._controls.rx_channel
        if fft_size is None or rx_channel is None:
            return  # combo not yet populated
        self._model.update(
            center_freq_hz=self._controls.center_freq_hz,
            sample_rate_hz=self._controls.sample_rate_hz,
            rx_gain_db=self._controls.rx_gain_db,
            fft_size=fft_size,
            rx_channel=rx_channel,
        )

    def _start_worker(self) -> None:
        self._sync_params()
        QMetaObject.invokeMethod(
            self._worker, "start", Qt.ConnectionType.QueuedConnection
        )

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        self.statusBar().showMessage(f"Error: {msg}", 5000)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._worker.stop()
        self._thread.quit()
        self._thread.wait(2000)
        event.accept()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ground station waterfall viewer")
    parser.add_argument(
        "--demo", action="store_true", help="Use synthetic data (no SDR needed)"
    )
    parser.add_argument(
        "--uri", type=str, default=None, help="Pluto URI (e.g. ip:192.168.2.1)"
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    model = SdrModel()

    if args.demo:
        worker = DemoWorker(model)
    else:
        worker = SdrWorker(model, uri=args.uri)

    window = MainWindow(worker, model)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
