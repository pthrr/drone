"""Tests for SdrParams and SdrModel — pure Python, no Qt required."""

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from ground_station.model import SdrModel, SdrParams, VALID_FFT_SIZES


# ── SdrParams ────────────────────────────────────────────────────────────


class TestSdrParams:
    def test_defaults(self):
        p = SdrParams()
        assert p.center_freq_hz == 868_000_000
        assert p.sample_rate_hz == 4_000_000
        assert p.rx_gain_db == 40
        assert p.fft_size == 1024
        assert p.rx_channel == 0

    def test_frozen(self):
        p = SdrParams()
        with pytest.raises(FrozenInstanceError):
            p.fft_size = 512  # type: ignore[misc]

    def test_replace_returns_new_instance(self):
        p = SdrParams()
        p2 = replace(p, fft_size=2048)
        assert p2.fft_size == 2048
        assert p.fft_size == 1024  # original unchanged

    def test_equality(self):
        assert SdrParams() == SdrParams()
        assert SdrParams(fft_size=512) != SdrParams(fft_size=1024)


# ── SdrModel validation ─────────────────────────────────────────────────


class TestSdrModelValidation:
    def test_valid_update_succeeds(self):
        m = SdrModel()
        result = m.update(fft_size=2048)
        assert result.fft_size == 2048
        assert m.snapshot().fft_size == 2048

    def test_invalid_fft_size_raises(self):
        m = SdrModel()
        for bad in (128, 999, 8192):
            with pytest.raises(ValueError, match="fft_size"):
                m.update(fft_size=bad)

    def test_invalid_freq_low_raises(self):
        m = SdrModel()
        with pytest.raises(ValueError, match="center_freq_hz"):
            m.update(center_freq_hz=50_000_000)

    def test_invalid_freq_high_raises(self):
        m = SdrModel()
        with pytest.raises(ValueError, match="center_freq_hz"):
            m.update(center_freq_hz=7_000_000_000)

    def test_invalid_gain_raises(self):
        m = SdrModel()
        with pytest.raises(ValueError, match="rx_gain_db"):
            m.update(rx_gain_db=-1)
        with pytest.raises(ValueError, match="rx_gain_db"):
            m.update(rx_gain_db=74)

    def test_invalid_channel_raises(self):
        m = SdrModel()
        with pytest.raises(ValueError, match="rx_channel"):
            m.update(rx_channel=-1)
        with pytest.raises(ValueError, match="rx_channel"):
            m.update(rx_channel=4)

    def test_invalid_sample_rate_raises(self):
        m = SdrModel()
        with pytest.raises(ValueError, match="sample_rate_hz"):
            m.update(sample_rate_hz=0)
        with pytest.raises(ValueError, match="sample_rate_hz"):
            m.update(sample_rate_hz=62_000_000)

    def test_partial_update_preserves_unchanged(self):
        m = SdrModel()
        m.update(rx_gain_db=50)
        p = m.snapshot()
        assert p.rx_gain_db == 50
        assert p.fft_size == 1024
        assert p.center_freq_hz == 868_000_000

    def test_failed_update_does_not_change_state(self):
        m = SdrModel()
        original = m.snapshot()
        with pytest.raises(ValueError):
            m.update(fft_size=999)
        assert m.snapshot() == original


# ── SdrModel window cache ────────────────────────────────────────────────


class TestSdrModelWindow:
    def test_initial_window_shape(self):
        m = SdrModel()
        assert m.window().shape == (1024,)

    def test_window_dtype_float32(self):
        m = SdrModel()
        assert m.window().dtype == np.float32

    def test_window_regenerates_on_fft_size_change(self):
        m = SdrModel()
        w1 = m.window()
        m.update(fft_size=2048)
        w2 = m.window()
        assert w1 is not w2
        assert w2.shape == (2048,)

    def test_window_not_regenerated_on_gain_change(self):
        m = SdrModel()
        w1 = m.window()
        m.update(rx_gain_db=50)
        w2 = m.window()
        assert w1 is w2

    def test_window_matches_snapshot_after_update(self):
        m = SdrModel()
        for size in VALID_FFT_SIZES:
            m.update(fft_size=size)
            assert m.window().shape[0] == m.snapshot().fft_size


# ── SdrModel thread safety ──────────────────────────────────────────────


class TestSdrModelThreadSafety:
    def test_snapshot_returns_frozen(self):
        m = SdrModel()
        p = m.snapshot()
        with pytest.raises(FrozenInstanceError):
            p.fft_size = 512  # type: ignore[misc]

    def test_concurrent_update_snapshot(self):
        m = SdrModel()
        errors: list[Exception] = []

        def writer():
            try:
                for size in VALID_FFT_SIZES * 20:
                    m.update(fft_size=size)
            except Exception as exc:
                errors.append(exc)

        def reader():
            try:
                for _ in range(100):
                    p, w = m.snapshot_with_window()
                    assert w.shape[0] == p.fft_size
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(5)]
        threads += [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == []

    def test_window_consistent_under_contention(self):
        m = SdrModel()
        inconsistencies: list[str] = []

        def check():
            for _ in range(200):
                p, w = m.snapshot_with_window()
                if w.shape[0] != p.fft_size:
                    inconsistencies.append(
                        f"window {w.shape[0]} != params {p.fft_size}"
                    )

        def mutate():
            for size in VALID_FFT_SIZES * 40:
                m.update(fft_size=size)

        threads = [threading.Thread(target=mutate) for _ in range(3)]
        threads += [threading.Thread(target=check) for _ in range(7)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert inconsistencies == []
