"""Pure unit tests for ground_station.dsp — no Qt required."""

from __future__ import annotations

import numpy as np
import pytest

from ground_station import dsp


class TestBuildColormap:
    def test_shape_and_dtype(self):
        cmap = dsp.build_colormap()
        assert cmap.shape == (256, 3)
        assert cmap.dtype == np.uint8

    def test_color_stop_first(self):
        cmap = dsp.build_colormap()
        np.testing.assert_array_equal(cmap[0], [68, 1, 84])

    def test_color_stop_mid(self):
        cmap = dsp.build_colormap()
        np.testing.assert_array_equal(cmap[128], [33, 145, 140])

    def test_color_stop_last(self):
        cmap = dsp.build_colormap()
        np.testing.assert_array_equal(cmap[255], [253, 231, 37])

    def test_green_channel_monotonicity(self):
        """Green channel should be non-decreasing across the full viridis range."""
        cmap = dsp.build_colormap()
        green = cmap[:, 1].astype(int)
        assert np.all(np.diff(green) >= 0)

    def test_singleton_matches(self):
        """Module-level COLORMAP should equal a fresh build."""
        np.testing.assert_array_equal(dsp.COLORMAP, dsp.build_colormap())


class TestComputePowerSpectrum:
    def test_output_shape(self, sample_iq, hanning_window):
        result = dsp.compute_power_spectrum(sample_iq, hanning_window)
        assert result.shape == (1024,)

    def test_output_dtype(self, sample_iq, hanning_window):
        result = dsp.compute_power_spectrum(sample_iq, hanning_window)
        assert result.dtype == np.float32

    def test_peak_at_correct_bin(self, sample_iq, hanning_window):
        """Tone at bin 256 should appear at fftshift index 256+512=768."""
        result = dsp.compute_power_spectrum(sample_iq, hanning_window)
        peak_bin = np.argmax(result)
        # fftshift moves DC to center (bin 512), so bin 256 maps to 768
        assert abs(peak_bin - 768) <= 2

    def test_dc_tone_at_center(self, hanning_window):
        """A DC tone should peak at the center bin when dc suppression is off."""
        dc = np.ones(1024, dtype=np.complex64)
        result = dsp.compute_power_spectrum(dc, hanning_window, dc_suppress_bins=0)
        assert np.argmax(result) == 512

    def test_suppress_dc_removes_center_spike(self, hanning_window):
        """DC suppression should reduce center bin power significantly."""
        dc = np.ones(1024, dtype=np.complex64)
        unsuppressed = dsp.compute_power_spectrum(dc, hanning_window, dc_suppress_bins=0)
        suppressed = dsp.compute_power_spectrum(dc, hanning_window, dc_suppress_bins=5)
        c = len(suppressed) // 2
        # The center bin should be much lower after suppression
        assert suppressed[c] < unsuppressed[c] - 10.0

    def test_finite_values(self, sample_iq, hanning_window):
        result = dsp.compute_power_spectrum(sample_iq, hanning_window)
        assert np.all(np.isfinite(result))

    def test_zero_input_safety(self, hanning_window):
        """All-zero input should not produce -inf (1e-20 floor)."""
        zeros = np.zeros(1024, dtype=np.complex64)
        result = dsp.compute_power_spectrum(zeros, hanning_window)
        assert np.all(np.isfinite(result))
        assert np.all(result < 0)  # should be very negative dB, but finite


class TestNormalizePowerDb:
    def test_output_dtype(self):
        db = np.array([-40.0, -20.0, 0.0], dtype=np.float32)
        result = dsp.normalize_power_db(db, -80.0, 0.0)
        assert result.dtype == np.uint8

    def test_clamp_below(self):
        db = np.array([-100.0], dtype=np.float32)
        result = dsp.normalize_power_db(db, -80.0, 0.0)
        assert result[0] == 0

    def test_clamp_above(self):
        db = np.array([10.0], dtype=np.float32)
        result = dsp.normalize_power_db(db, -80.0, 0.0)
        assert result[0] == 255

    def test_midpoint(self):
        db = np.array([-40.0], dtype=np.float32)
        result = dsp.normalize_power_db(db, -80.0, 0.0)
        assert 125 <= result[0] <= 129  # ~127.5

    def test_boundary_min(self):
        db = np.array([-80.0], dtype=np.float32)
        result = dsp.normalize_power_db(db, -80.0, 0.0)
        assert result[0] == 0

    def test_boundary_max(self):
        db = np.array([0.0], dtype=np.float32)
        result = dsp.normalize_power_db(db, -80.0, 0.0)
        assert result[0] == 255


class TestGenerateDemoIq:
    def test_output_shape(self):
        sig, _ = dsp.generate_demo_iq(1024, 4_000_000, 0.0)
        assert sig.shape == (1024,)

    def test_output_dtype(self):
        sig, _ = dsp.generate_demo_iq(1024, 4_000_000, 0.0)
        assert sig.dtype == np.complex64

    def test_phase_advancement(self):
        _, phase1 = dsp.generate_demo_iq(1024, 4_000_000, 0.0)
        _, phase2 = dsp.generate_demo_iq(1024, 4_000_000, phase1)
        assert phase1 == pytest.approx(0.05)
        assert phase2 == pytest.approx(0.10)

    def test_different_fft_sizes(self):
        for n in (256, 512, 2048):
            sig, _ = dsp.generate_demo_iq(n, 4_000_000, 0.0)
            assert sig.shape == (n,)

    def test_nonzero_power(self):
        sig, _ = dsp.generate_demo_iq(1024, 4_000_000, 0.0)
        assert np.mean(np.abs(sig) ** 2) > 0.01
