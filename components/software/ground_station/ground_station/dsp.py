"""Pure signal-processing helpers — no Qt imports."""

from __future__ import annotations

import numpy as np


def build_colormap() -> np.ndarray:
    """Build a 256x3 uint8 viridis-style LUT (perceptually uniform)."""
    lut = np.zeros((256, 3), dtype=np.uint8)
    stops = [
        (0, (68, 1, 84)),
        (32, (72, 35, 116)),
        (64, (64, 67, 135)),
        (96, (52, 94, 141)),
        (128, (33, 145, 140)),
        (160, (43, 176, 99)),
        (192, (121, 209, 81)),
        (224, (189, 223, 38)),
        (255, (253, 231, 37)),
    ]
    for i in range(len(stops) - 1):
        idx0, c0 = stops[i]
        idx1, c1 = stops[i + 1]
        n = idx1 - idx0
        for ch in range(3):
            lut[idx0 : idx1 + 1, ch] = np.linspace(c0[ch], c1[ch], n + 1).astype(
                np.uint8
            )
    return lut


COLORMAP = build_colormap()


def compute_power_spectrum(
    iq: np.ndarray, window: np.ndarray, *, dc_suppress_bins: int = 5
) -> np.ndarray:
    """Windowed FFT -> power in dB (float32).

    Returns an array of shape ``(len(iq),)`` with dtype ``float32``.
    *dc_suppress_bins* controls how many bins around DC are linearly
    interpolated to remove the LO-leakage spike that direct-conversion
    receivers produce.  Set to 0 to disable.
    """
    spectrum = np.fft.fftshift(np.fft.fft(iq * window))
    power = np.maximum(np.abs(spectrum) ** 2, 1e-20)
    if dc_suppress_bins > 0:
        c = len(power) // 2
        half = dc_suppress_bins // 2
        lo = max(c - half - 1, 0)
        hi = min(c + half + 1, len(power) - 1)
        power[lo + 1 : hi] = np.linspace(power[lo], power[hi], hi - lo - 1)
    power_db = (10.0 * np.log10(power)).astype(np.float32)
    return power_db


def normalize_power_db(
    power_db: np.ndarray, db_min: float, db_max: float
) -> np.ndarray:
    """Map dB values to 0-255 uint8 indices for colormap lookup."""
    span = db_max - db_min
    if span < 1e-6:
        return np.full(power_db.shape, 128, dtype=np.uint8)
    normed = np.clip((power_db - db_min) / span, 0.0, 1.0)
    return (normed * 255).astype(np.uint8)


def generate_demo_iq(
    n: int, sample_rate: int, phase: float
) -> tuple[np.ndarray, float]:
    """Synthesise *n* IQ samples with two drifting tones + noise.

    Returns ``(signal, new_phase)`` where *signal* has dtype ``complex64``.
    """
    t = np.arange(n, dtype=np.float32) / sample_rate

    f1 = 0.15 * sample_rate * np.sin(phase * 0.3)
    f2 = -0.25 * sample_rate * np.cos(phase * 0.17)
    sig = (
        0.8 * np.exp(2j * np.pi * f1 * t) + 0.4 * np.exp(2j * np.pi * f2 * t)
    ).astype(np.complex64)
    sig += (np.random.randn(n) + 1j * np.random.randn(n)).astype(np.complex64) * 0.05

    return sig, phase + 0.05
