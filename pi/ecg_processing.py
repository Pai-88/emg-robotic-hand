"""
Streaming ECG processing — filtering, R-peak detection, HR / HRV / respiration.

Feed sample chunks to ECGProcessor.process(); read derived metrics from the
properties. State is preserved across chunks so it works for real-time streams.

Pipeline:
    raw → 50 Hz notch → 0.5–40 Hz band-pass  (display signal)
                     ↘ 5–15 Hz band-pass → ² → adaptive threshold  (R-peak detector)

The R-peak detector is a streamable simplification of Pan–Tompkins: it works on
a rolling 3-s buffer of QRS-band energy, and only commits peaks that lie in the
"stable" (older) part of the buffer to avoid edge artefacts. Threshold adapts
to a fraction of the recent maximum, so it tracks gain changes.
"""
from collections import deque
import numpy as np
import scipy.signal as signal


class ECGProcessor:
    """Streaming ECG processor. fs is samples-per-second of the input stream."""

    def __init__(self, fs=1000,
                 disp_band=(0.5, 40), qrs_band=(5, 15),
                 notch_hz=50, notch_q=30,
                 refractory_ms=250,
                 buffer_seconds=3,
                 confirm_lag_ms=150,
                 detect_every_chunks=10,
                 rr_history=120):
        self.fs = fs
        self.refractory_n = int(refractory_ms / 1000 * fs)

        nyq = fs / 2
        # 2nd-order Butterworth band-pass 0.5–40 Hz for display
        self.b_disp, self.a_disp = signal.butter(
            2, [disp_band[0] / nyq, disp_band[1] / nyq], btype='band')
        # IIR notch for mains (UK = 50 Hz)
        self.b_n, self.a_n = signal.iirnotch(notch_hz, notch_q, fs)
        # 2nd-order Butterworth band-pass 5–15 Hz to isolate QRS energy
        self.b_qrs, self.a_qrs = signal.butter(
            2, [qrs_band[0] / nyq, qrs_band[1] / nyq], btype='band')

        # Filter state — initialised lazily from the first sample to avoid
        # large startup transients.
        self._zi_n    = signal.lfilter_zi(self.b_n,    self.a_n)
        self._zi_disp = signal.lfilter_zi(self.b_disp, self.a_disp)
        self._zi_qrs  = signal.lfilter_zi(self.b_qrs,  self.a_qrs)
        self._initialized = False

        # Rolling buffer of QRS-band energy for peak detection
        self._qrs_buf = deque(maxlen=fs * buffer_seconds)
        self._confirm_lag = int(confirm_lag_ms / 1000 * fs)
        self._chunks_since_detect = 0
        self._detect_every = detect_every_chunks

        # State exposed to consumers
        self.total_samples = 0
        self.last_r_global_idx = -fs * 10   # sentinel: "long ago"
        self.rr_intervals_ms = deque(maxlen=rr_history)
        self.recent_r_idxs = deque(maxlen=20)

    # ─────────────────────────────────────────────────────────
    def process(self, samples):
        """Process a chunk of raw ECG samples (1-D array, ADC counts or volts).

        Returns the band-pass-filtered display signal of the same length.
        Side effect: updates R-peak detection state and RR/HR/HRV metrics.
        """
        x = np.asarray(samples, dtype=np.float64)
        if x.size == 0:
            return x

        if not self._initialized:
            # Pre-load filter state with the first sample so the initial
            # transient is a single sample, not many seconds of ringing.
            v0 = float(x[0])
            self._zi_n    = self._zi_n    * v0
            self._zi_disp = self._zi_disp * v0
            self._zi_qrs  = self._zi_qrs  * v0
            self._initialized = True

        # 1. Notch (mains)
        x, self._zi_n = signal.lfilter(self.b_n, self.a_n, x, zi=self._zi_n)
        # 2. Display band-pass (kept separately so we don't double-filter)
        disp, self._zi_disp = signal.lfilter(self.b_disp, self.a_disp, x, zi=self._zi_disp)
        # 3. QRS-band → square → energy stream
        qrs, self._zi_qrs = signal.lfilter(self.b_qrs, self.a_qrs, x, zi=self._zi_qrs)
        energy = qrs ** 2

        self._qrs_buf.extend(energy)
        self.total_samples += x.size

        # Throttle peak detection — running it every chunk wastes CPU on the Pi
        self._chunks_since_detect += 1
        if self._chunks_since_detect >= self._detect_every:
            self._detect_peaks()
            self._chunks_since_detect = 0

        return disp

    # ─────────────────────────────────────────────────────────
    def _detect_peaks(self):
        n_buf = len(self._qrs_buf)
        if n_buf <= self._confirm_lag + self.refractory_n:
            return
        buf = np.fromiter(self._qrs_buf, dtype=np.float64, count=n_buf)

        # Skip when essentially silent — avoids picking up noise as beats
        recent_max = float(buf[-2 * self.fs:].max()) if n_buf > 2 * self.fs else float(buf.max())
        if recent_max < 1.0:
            return

        stable = buf[: n_buf - self._confirm_lag]
        thresh = 0.35 * recent_max
        peaks, _ = signal.find_peaks(stable, height=thresh, distance=self.refractory_n)

        buf_start_global = self.total_samples - n_buf
        for p in peaks:
            global_idx = buf_start_global + int(p)
            if global_idx <= self.last_r_global_idx + self.refractory_n:
                continue
            if self.last_r_global_idx > -self.fs:
                rr_ms = (global_idx - self.last_r_global_idx) * 1000.0 / self.fs
                if 300 < rr_ms < 2000:
                    self.rr_intervals_ms.append(rr_ms)
            self.last_r_global_idx = global_idx
            self.recent_r_idxs.append(global_idx)

    # ─────────────────────────────────────────────────────────
    @property
    def hr_bpm(self):
        """Heart rate averaged over the last ≤8 RR intervals."""
        if len(self.rr_intervals_ms) < 2:
            return None
        recent = list(self.rr_intervals_ms)[-8:]
        return 60000.0 / float(np.mean(recent))

    @property
    def hrv_rmssd_ms(self):
        """HRV — root-mean-square of successive RR differences (ms)."""
        if len(self.rr_intervals_ms) < 5:
            return None
        rrs = np.array(self.rr_intervals_ms)
        return float(np.sqrt(np.mean(np.diff(rrs) ** 2)))

    @property
    def hrv_sdnn_ms(self):
        """HRV — standard deviation of RR intervals (ms)."""
        if len(self.rr_intervals_ms) < 5:
            return None
        return float(np.std(self.rr_intervals_ms, ddof=1))

    @property
    def last_rr_ms(self):
        return float(self.rr_intervals_ms[-1]) if self.rr_intervals_ms else None

    @property
    def respiration_rate_per_min(self):
        """Estimate respiration rate from respiratory-sinus-arrhythmia (RSA).

        Needs ~30 s of stable RR data; otherwise returns None. The estimate is
        free (no extra hardware) but coarse — for clinical accuracy you'd want
        a chest strain gauge or thoracic impedance.
        """
        if len(self.rr_intervals_ms) < 30:
            return None
        rrs = np.array(self.rr_intervals_ms, dtype=np.float64)
        t_beats = np.cumsum(rrs) / 1000.0
        if t_beats[-1] - t_beats[0] < 30:
            return None
        target_t = np.arange(t_beats[0], t_beats[-1], 0.25)   # 4 Hz uniform
        target = np.interp(target_t, t_beats, rrs)
        target = target - target.mean()
        Y = np.abs(np.fft.rfft(target))
        f = np.fft.rfftfreq(len(target), 0.25)
        band = (f >= 0.1) & (f <= 0.5)                          # 6–30 brpm
        if not band.any() or Y[band].max() < 1e-3:
            return None
        peak_f = float(f[band][np.argmax(Y[band])])
        return peak_f * 60.0
