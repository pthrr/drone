"""Shared fixtures for ground_station tests."""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture()
def rng() -> np.random.Generator:
    """Seeded RNG for reproducible tests."""
    return np.random.default_rng(42)


@pytest.fixture()
def sample_iq(rng: np.random.Generator) -> np.ndarray:
    """1024-sample complex64 IQ buffer with a tone at bin 256."""
    n = 1024
    t = np.arange(n, dtype=np.float32) / n
    tone = np.exp(2j * np.pi * 256 * t).astype(np.complex64)
    noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)).astype(
        np.complex64
    ) * 0.01
    return tone + noise


@pytest.fixture()
def hanning_window() -> np.ndarray:
    """1024-point Hanning window (float32)."""
    return np.hanning(1024).astype(np.float32)
