"""SDR and demo data workers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from ground_station import dsp
from ground_station.model import SdrModel, SdrParams


@runtime_checkable
class Worker(Protocol):
    """Structural type for anything that produces FFT data."""

    data_ready: Signal
    error: Signal

    def start(self) -> None: ...
    def stop(self) -> None: ...


class _WorkerBase(QObject):
    """Shared state and signals for concrete workers."""

    data_ready = Signal(np.ndarray)
    error = Signal(str)
    channels_available = Signal(list)

    def __init__(self, model: SdrModel, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._running = False

    @Slot()
    def stop(self) -> None:
        self._running = False


class SdrWorker(_WorkerBase):
    """Receives IQ samples from ADALM-Pluto in a dedicated thread."""

    def __init__(self, model: SdrModel, uri: str | None = None) -> None:
        super().__init__(model)
        self._uri = uri
        self._sdr = None

    @Slot()
    def start(self) -> None:
        try:
            import adi
        except ImportError:
            self.error.emit("pyadi-iio not installed — use --demo mode")
            return

        try:
            if self._uri:
                self._sdr = adi.Pluto(uri=self._uri)
            else:
                self._sdr = adi.Pluto()
        except Exception as exc:
            self.error.emit(f"Cannot connect to Pluto: {exc}")
            return

        # Probe available RX channels and report to the GUI
        params = self._model.snapshot()
        avail = [0]
        for ch in range(1, 4):
            try:
                self._sdr.rx_enabled_channels = [ch]
                avail.append(ch)
            except Exception:
                break
        self._sdr.rx_enabled_channels = [params.rx_channel]
        self.channels_available.emit(avail)

        self._apply_sdr_params(params)
        self._running = True

        while self._running:
            try:
                params, window = self._model.snapshot_with_window()
                self._apply_sdr_params(params)
                raw = self._sdr.rx()
                iq = np.array(raw, dtype=np.complex64)[: params.fft_size]
                if iq.shape[0] < params.fft_size:
                    iq = np.pad(iq, (0, params.fft_size - iq.shape[0]))
                power_db = dsp.compute_power_spectrum(iq, window)
                self.data_ready.emit(power_db)
            except Exception as exc:
                self.error.emit(str(exc))
                break

    def _apply_sdr_params(self, params: SdrParams | None = None) -> None:
        sdr = self._sdr
        if sdr is None:
            return
        if params is None:
            params = self._model.snapshot()
        sdr.rx_enabled_channels = [params.rx_channel]
        sdr.rx_lo = params.center_freq_hz
        sdr.sample_rate = params.sample_rate_hz
        ch = params.rx_channel
        setattr(sdr, f"gain_control_mode_chan{ch}", "manual")
        setattr(sdr, f"rx_hardwaregain_chan{ch}", params.rx_gain_db)
        sdr.rx_buffer_size = params.fft_size


class DemoWorker(_WorkerBase):
    """Generates synthetic tones + noise for testing without hardware."""

    @Slot()
    def start(self) -> None:
        import time

        self._running = True
        phase = 0.0

        while self._running:
            params, window = self._model.snapshot_with_window()
            sig, phase = dsp.generate_demo_iq(
                params.fft_size, params.sample_rate_hz, phase
            )
            power_db = dsp.compute_power_spectrum(sig, window)
            self.data_ready.emit(power_db)
            time.sleep(0.02)
