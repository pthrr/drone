"""Thread-safe SDR parameter model with cached Hanning window."""

from __future__ import annotations

import threading
from dataclasses import dataclass, replace

import numpy as np

VALID_FFT_SIZES = (256, 512, 1024, 2048, 4096)


@dataclass(frozen=True)
class SdrParams:
    """Immutable snapshot of all SDR parameters."""

    center_freq_hz: int = 868_000_000
    sample_rate_hz: int = 4_000_000
    rx_gain_db: int = 40
    fft_size: int = 1024
    rx_channel: int = 0


def _validate(params: SdrParams) -> None:
    """Raise ValueError if any field is out of range."""
    if params.fft_size not in VALID_FFT_SIZES:
        raise ValueError(
            f"fft_size must be one of {VALID_FFT_SIZES}, got {params.fft_size}"
        )
    if not 70_000_000 <= params.center_freq_hz <= 6_000_000_000:
        raise ValueError(
            f"center_freq_hz must be 70 MHz..6 GHz, got {params.center_freq_hz}"
        )
    if not 0 <= params.rx_gain_db <= 73:
        raise ValueError(f"rx_gain_db must be 0..73, got {params.rx_gain_db}")
    if not 0 <= params.rx_channel <= 3:
        raise ValueError(f"rx_channel must be 0..3, got {params.rx_channel}")
    if not 1_000_000 <= params.sample_rate_hz <= 61_000_000:
        raise ValueError(
            f"sample_rate_hz must be 1 MSPS..61 MSPS, got {params.sample_rate_hz}"
        )


class SdrModel:
    """Thread-safe parameter store with cached Hanning window."""

    def __init__(self, params: SdrParams | None = None) -> None:
        self._lock = threading.RLock()
        self._params = params or SdrParams()
        _validate(self._params)
        self._window = np.hanning(self._params.fft_size).astype(np.float32)

    def update(self, **kwargs: object) -> SdrParams:
        """Validate, apply changes atomically, regenerate window if fft_size changed.

        Returns the new SdrParams after the update.
        Raises ValueError on invalid input.
        """
        with self._lock:
            new = replace(self._params, **kwargs)
            _validate(new)
            if new.fft_size != self._params.fft_size:
                self._window = np.hanning(new.fft_size).astype(np.float32)
            self._params = new
            return new

    def snapshot(self) -> SdrParams:
        """Atomic read — returns frozen dataclass."""
        with self._lock:
            return self._params

    def window(self) -> np.ndarray:
        """Current Hanning window (consistent with most recent snapshot().fft_size)."""
        with self._lock:
            return self._window

    def snapshot_with_window(self) -> tuple[SdrParams, np.ndarray]:
        """Atomic read of params and window together — guaranteed consistent."""
        with self._lock:
            return self._params, self._window
