"""Integration tests for workers (requires pytest-qt)."""

from __future__ import annotations

import sys
import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ground_station.model import SdrModel, SdrParams
from ground_station.workers import DemoWorker, SdrWorker


class TestSdrWorker:
    def _make_mock_adi(self, fft_size: int, call_limit: int = 2):
        """Build a fake ``adi`` module whose Pluto.rx() returns synthetic IQ."""
        mock_adi = MagicMock()
        pluto = MagicMock()
        mock_adi.Pluto.return_value = pluto

        call_count = 0

        def fake_rx():
            nonlocal call_count
            call_count += 1
            # Return a simple tone so the spectrum is well-defined
            t = np.arange(fft_size, dtype=np.float32) / fft_size
            return np.exp(2j * np.pi * 100 * t).astype(np.complex64)

        pluto.rx = fake_rx
        return mock_adi, pluto

    def test_emits_data_ready_with_mock_sdr(self, qtbot):
        model = SdrModel(SdrParams(fft_size=256))
        worker = SdrWorker(model, uri="ip:mock")

        mock_adi, pluto = self._make_mock_adi(256)

        with patch.dict(sys.modules, {"adi": mock_adi}):
            with qtbot.waitSignal(worker.data_ready, timeout=2000) as blocker:
                t = threading.Thread(target=worker.start, daemon=True)
                t.start()

            result = blocker.args[0]
            assert isinstance(result, np.ndarray)
            assert result.shape == (256,)
            assert result.dtype == np.float32
            assert np.all(np.isfinite(result))

            worker.stop()
            t.join(timeout=2)

        mock_adi.Pluto.assert_called_once_with(uri="ip:mock")

    def test_configures_sdr_params(self, qtbot):
        model = SdrModel(
            SdrParams(
                fft_size=512,
                center_freq_hz=433_000_000,
                sample_rate_hz=2_000_000,
                rx_gain_db=30,
            )
        )
        worker = SdrWorker(model)

        mock_adi, pluto = self._make_mock_adi(512)

        with patch.dict(sys.modules, {"adi": mock_adi}):
            with qtbot.waitSignal(worker.data_ready, timeout=2000):
                t = threading.Thread(target=worker.start, daemon=True)
                t.start()

            worker.stop()
            t.join(timeout=2)

        assert pluto.rx_lo == 433_000_000
        assert pluto.sample_rate == 2_000_000
        assert pluto.rx_hardwaregain_chan0 == 30
        assert pluto.rx_buffer_size == 512

    def test_emits_error_on_connection_failure(self, qtbot):
        model = SdrModel()
        worker = SdrWorker(model)

        mock_adi = MagicMock()
        mock_adi.Pluto.side_effect = RuntimeError("no device")

        with patch.dict(sys.modules, {"adi": mock_adi}):
            with qtbot.waitSignal(worker.error, timeout=2000) as blocker:
                worker.start()

        assert "no device" in blocker.args[0]

    def test_emits_error_without_pyadi(self, qtbot):
        model = SdrModel()
        worker = SdrWorker(model)

        # Temporarily hide adi from imports
        with patch.dict(sys.modules, {"adi": None}):
            with qtbot.waitSignal(worker.error, timeout=2000) as blocker:
                worker.start()

        assert "pyadi-iio" in blocker.args[0].lower() or "demo" in blocker.args[0].lower()

    def test_pads_short_rx_buffer(self, qtbot):
        model = SdrModel(SdrParams(fft_size=512))
        worker = SdrWorker(model)

        mock_adi = MagicMock()
        pluto = MagicMock()
        mock_adi.Pluto.return_value = pluto
        # Return fewer samples than fft_size
        pluto.rx.return_value = np.ones(128, dtype=np.complex64)

        with patch.dict(sys.modules, {"adi": mock_adi}):
            with qtbot.waitSignal(worker.data_ready, timeout=2000) as blocker:
                t = threading.Thread(target=worker.start, daemon=True)
                t.start()

            assert blocker.args[0].shape == (512,)
            worker.stop()
            t.join(timeout=2)

    def test_adapts_to_fft_size_change(self, qtbot):
        model = SdrModel(SdrParams(fft_size=256))
        worker = SdrWorker(model)

        # Return enough samples for any fft_size we'll use
        mock_adi = MagicMock()
        pluto = MagicMock()
        mock_adi.Pluto.return_value = pluto
        pluto.rx.return_value = np.ones(4096, dtype=np.complex64)

        with patch.dict(sys.modules, {"adi": mock_adi}):
            with qtbot.waitSignal(worker.data_ready, timeout=2000):
                t = threading.Thread(target=worker.start, daemon=True)
                t.start()

            # Change fft_size while running
            model.update(fft_size=512)

            # Wait for a signal with the new size
            for _ in range(50):
                with qtbot.waitSignal(worker.data_ready, timeout=2000) as blocker:
                    pass
                if blocker.args[0].shape == (512,):
                    break
            assert blocker.args[0].shape == (512,)

            worker.stop()
            t.join(timeout=2)


class TestDemoWorker:
    def test_emits_data_ready(self, qtbot):
        model = SdrModel(SdrParams(fft_size=256))
        worker = DemoWorker(model)

        with qtbot.waitSignal(worker.data_ready, timeout=2000) as blocker:
            t = threading.Thread(target=worker.start, daemon=True)
            t.start()

        result = blocker.args[0]
        assert isinstance(result, np.ndarray)
        assert result.shape == (256,)
        assert result.dtype == np.float32

        worker.stop()
        t.join(timeout=2)

    def test_stop_halts_emission(self, qtbot):
        model = SdrModel(SdrParams(fft_size=256))
        worker = DemoWorker(model)

        t = threading.Thread(target=worker.start, daemon=True)
        t.start()

        # Let it run briefly
        qtbot.wait(100)
        worker.stop()
        t.join(timeout=2)

        assert not worker._running

    def test_output_length_matches_fft_size(self, qtbot):
        for fft_size in (256, 512, 1024):
            model = SdrModel(SdrParams(fft_size=fft_size))
            worker = DemoWorker(model)

            with qtbot.waitSignal(worker.data_ready, timeout=2000) as blocker:
                t = threading.Thread(target=worker.start, daemon=True)
                t.start()

            assert blocker.args[0].shape == (fft_size,)
            worker.stop()
            t.join(timeout=2)

    def test_adapts_to_fft_size_change(self, qtbot):
        model = SdrModel(SdrParams(fft_size=256))
        worker = DemoWorker(model)

        with qtbot.waitSignal(worker.data_ready, timeout=2000):
            t = threading.Thread(target=worker.start, daemon=True)
            t.start()

        # Change fft_size while running
        model.update(fft_size=1024)

        # Wait for a signal with the new size
        for _ in range(50):
            with qtbot.waitSignal(worker.data_ready, timeout=2000) as blocker:
                pass
            if blocker.args[0].shape == (1024,):
                break
        assert blocker.args[0].shape == (1024,)

        worker.stop()
        t.join(timeout=2)
