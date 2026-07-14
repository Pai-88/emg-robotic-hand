"""
Shared utilities for the EMG → robotic hand pipeline.

Matches the binary packet format from esp32_emg_streamer.ino:
    HEADER(2) | SEQ(2) | TIMESTAMP(4) | 10 × [CH1(2) CH2(2)]   = 48 bytes
    sampled at 1 kHz, two channels (forearm flexors + extensors).

Used by:
    record_gestures.py     — collect labelled training data
    train_gestures.py      — fit a gesture classifier
    predict_realtime.py    — live inference from the ESP32 stream
"""
import socket
import struct
import numpy as np
import scipy.signal as signal
import torch
import torch.nn as nn
import torch.nn.functional as F


# ============================================================
#  CONSTANTS — must stay in sync with the ESP32 firmware
# ============================================================
SAMPLE_RATE         = 1000      # Hz, set by esp32_emg_streamer.ino
NUM_CHANNELS        = 2
SAMPLES_PER_PACKET  = 10
NUM_FSRS            = 3         # fingertip FSR-402s: thumb / index / middle
PACKET_SIZE         = 8 + SAMPLES_PER_PACKET * 4 + NUM_FSRS * 2   # 54 bytes
HEADER              = b'\xe1\xa1'
UDP_PORT            = 5555

# FSR channel order matches the firmware (thumb=0, index=1, middle=2)
FSR_FINGERS = ['thumb', 'index', 'middle']

# Real-time windowing — 200 ms windows, 50 ms hop → 20 predictions/sec.
# Standard for prosthetic hand control: hop short enough to feel
# responsive (<100 ms), window long enough to be statistically stable.
WINDOW_SIZE = 200
WINDOW_HOP  = 50

# Default gesture set. Start with these five — add more once you have
# a baseline working. The order here defines the class indices.
GESTURES = ['rest', 'fist', 'open', 'pinch', 'point']

# Quiet-window threshold: if filtered RMS is below this, force a 'rest'
# prediction. Avoids spurious classifications when no muscle is active.
# Tune from your own baseline recording — print the RMS of a true rest
# window and pick a value comfortably below the lowest gesture activity.
RMS_GATE = 30.0


# ============================================================
#  PACKET PARSING
# ============================================================
def parse_packet(buf):
    """Decode a 54-byte EMG+FSR packet.

    Returns (seq, ts_us, samples, fsr) or None.
        samples: (SAMPLES_PER_PACKET, NUM_CHANNELS) int16
        fsr:     (NUM_FSRS,) uint16 — raw ADC, thumb/index/middle
    """
    if len(buf) != PACKET_SIZE or buf[0:2] != HEADER:
        return None
    seq, ts_us = struct.unpack('<HI', buf[2:8])
    samples = np.frombuffer(
        buf, dtype='<i2', offset=8, count=SAMPLES_PER_PACKET * NUM_CHANNELS
    ).reshape(SAMPLES_PER_PACKET, NUM_CHANNELS)
    fsr = np.frombuffer(
        buf, dtype='<u2', offset=8 + SAMPLES_PER_PACKET * 4, count=NUM_FSRS
    )
    return seq, ts_us, samples, fsr


# ============================================================
#  FILTERING
# ============================================================
class EMGFilter:
    """Streaming IIR filter chain for sEMG: 20 Hz HP → 50 Hz notch → 450 Hz LP.

    Maintains per-channel state (zi) so the filter can be applied chunk-by-
    chunk without restarting (and so without edge artefacts at chunk
    boundaries).
    """
    def __init__(self, fs=SAMPLE_RATE, num_channels=NUM_CHANNELS):
        nyq = fs / 2
        self.b_hp,    self.a_hp    = signal.butter(4, 20  / nyq, btype='high')
        self.b_notch, self.a_notch = signal.iirnotch(50, 30, fs)
        self.b_lp,    self.a_lp    = signal.butter(4, 450 / nyq, btype='low')

        def zi_for(b, a):
            n = max(len(a), len(b)) - 1
            return np.zeros((n, num_channels), dtype=np.float64)

        self.zi_hp    = zi_for(self.b_hp,    self.a_hp)
        self.zi_notch = zi_for(self.b_notch, self.a_notch)
        self.zi_lp    = zi_for(self.b_lp,    self.a_lp)

    def apply(self, x):
        """Filter a (T, C) chunk and update internal state."""
        x = np.asarray(x, dtype=np.float64)
        x, self.zi_hp    = signal.lfilter(self.b_hp,    self.a_hp,    x, axis=0, zi=self.zi_hp)
        x, self.zi_notch = signal.lfilter(self.b_notch, self.a_notch, x, axis=0, zi=self.zi_notch)
        x, self.zi_lp    = signal.lfilter(self.b_lp,    self.a_lp,    x, axis=0, zi=self.zi_lp)
        return x.astype(np.float32)


def filter_offline(x, fs=SAMPLE_RATE):
    """Zero-phase filter for offline analysis (training data, plotting)."""
    nyq = fs / 2
    b_hp, a_hp = signal.butter(4, 20  / nyq, btype='high')
    b_n,  a_n  = signal.iirnotch(50, 30, fs)
    b_lp, a_lp = signal.butter(4, 450 / nyq, btype='low')
    x = signal.filtfilt(b_hp, a_hp, x.astype(np.float64), axis=0)
    x = signal.filtfilt(b_n,  a_n,  x, axis=0)
    x = signal.filtfilt(b_lp, a_lp, x, axis=0)
    return x.astype(np.float32)


# ============================================================
#  UDP RECEIVER WITH RING BUFFER
# ============================================================
class EMGReceiver:
    """Non-blocking UDP listener with a ring buffer of recent samples.

    If filtered=True, samples are run through an EMGFilter as they arrive
    (recommended for real-time inference — gives properly filtered windows
    without per-window edge artefacts). For recording training data, leave
    filtered=False and filter offline with filter_offline().

    Usage:
        with EMGReceiver(filtered=True) as rx:
            while running:
                rx.poll()
                window = rx.get_latest_window(WINDOW_SIZE)
                if window is not None: ...
    """
    def __init__(self, port=UDP_PORT, buffer_seconds=5, filtered=False):
        self.port = port
        self.sock = None
        self.filt = EMGFilter() if filtered else None
        dtype = np.float32 if filtered else np.int16
        self.buf = np.zeros(
            (buffer_seconds * SAMPLE_RATE, NUM_CHANNELS), dtype=dtype)
        self.write_idx = 0
        self.total_samples = 0
        self.last_seq = None
        self.dropped = 0
        # Latest FSR readings, updated on every packet (one reading per packet)
        self.fsr_latest = np.zeros(NUM_FSRS, dtype=np.uint16)
        self.fsr_total = 0   # number of FSR readings ever received

    def __enter__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        self.sock.setblocking(False)
        return self

    def __exit__(self, *exc):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def poll(self):
        """Drain pending UDP packets into the ring buffer. Returns # new samples."""
        n_new = 0
        while True:
            try:
                data, _ = self.sock.recvfrom(64)
            except BlockingIOError:
                break
            parsed = parse_packet(data)
            if parsed is None:
                continue
            seq, _, samples, fsr = parsed

            if self.last_seq is not None:
                expected = (self.last_seq + 1) & 0xFFFF
                if seq != expected:
                    self.dropped += (seq - expected) & 0xFFFF
            self.last_seq = seq

            # Store the latest FSR reading (one per packet)
            self.fsr_latest = fsr.copy()
            self.fsr_total += 1

            if self.filt is not None:
                samples = self.filt.apply(samples)
            else:
                samples = samples.astype(self.buf.dtype)

            n = len(samples)
            end_idx = self.write_idx + n
            if end_idx <= len(self.buf):
                self.buf[self.write_idx:end_idx] = samples
            else:
                first = len(self.buf) - self.write_idx
                self.buf[self.write_idx:] = samples[:first]
                self.buf[:n - first] = samples[first:]
            self.write_idx = end_idx % len(self.buf)
            self.total_samples += n
            n_new += n
        return n_new

    def get_latest_window(self, window_size):
        """Return the most recent window_size samples as (window_size, C)."""
        if self.total_samples < window_size:
            return None
        start = (self.write_idx - window_size) % len(self.buf)
        if start + window_size <= len(self.buf):
            return self.buf[start:start + window_size].copy()
        first = self.buf[start:].copy()
        return np.vstack([first, self.buf[:window_size - len(first)].copy()])


# ============================================================
#  WINDOWING (offline)
# ============================================================
def window_signal(x, window_size=WINDOW_SIZE, hop=WINDOW_HOP):
    """Slide a window across a (T, C) signal. Returns (N, C, window_size)."""
    T = x.shape[0]
    if T < window_size:
        return np.empty((0, x.shape[1], window_size), dtype=np.float32)
    n_windows = (T - window_size) // hop + 1
    out = np.stack([
        x[i * hop : i * hop + window_size].T
        for i in range(n_windows)
    ]).astype(np.float32)
    return out


# ============================================================
#  NORMALISATION — z-score per channel, fit on training data only
# ============================================================
class Normaliser:
    def __init__(self):
        self.mean = None
        self.std = None

    def fit(self, X):
        # X: (N, C, T) — mean/std per channel across windows and time
        self.mean = X.mean(axis=(0, 2), keepdims=True).astype(np.float32)
        self.std = (X.std(axis=(0, 2), keepdims=True) + 1e-6).astype(np.float32)

    def transform(self, X):
        return ((X - self.mean) / self.std).astype(np.float32)

    def save(self, path):
        np.savez(path, mean=self.mean, std=self.std)

    @classmethod
    def load(cls, path):
        d = np.load(path)
        n = cls()
        n.mean, n.std = d['mean'].astype(np.float32), d['std'].astype(np.float32)
        return n


# ============================================================
#  MODEL — small 1D CNN for (NUM_CHANNELS, WINDOW_SIZE) windows
# ============================================================
class EMGGestureNet(nn.Module):
    """~16k-param 1D CNN. Runs in <1 ms on a Pi 5 CPU."""
    def __init__(self, num_classes, num_channels=NUM_CHANNELS):
        super().__init__()
        self.conv1 = nn.Conv1d(num_channels, 16, kernel_size=11, padding=5)
        self.bn1   = nn.BatchNorm1d(16)
        self.conv2 = nn.Conv1d(16, 32, kernel_size=7, padding=3)
        self.bn2   = nn.BatchNorm1d(32)
        self.conv3 = nn.Conv1d(32, 64, kernel_size=5, padding=2)
        self.bn3   = nn.BatchNorm1d(64)
        self.gap   = nn.AdaptiveAvgPool1d(1)
        self.fc1   = nn.Linear(64, 32)
        self.drop  = nn.Dropout(0.3)
        self.fc2   = nn.Linear(32, num_classes)

    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.max_pool1d(x, 2)
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.max_pool1d(x, 2)
        x = F.relu(self.bn3(self.conv3(x)))
        x = self.gap(x).squeeze(-1)
        x = F.relu(self.fc1(x))
        x = self.drop(x)
        return self.fc2(x)
