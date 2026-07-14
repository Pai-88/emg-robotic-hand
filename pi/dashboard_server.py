"""
Live biosignal dashboard server.

Listens to the ESP32 UDP stream and serves a real-time HTML/JS dashboard via
FastAPI + WebSocket. Runs in one process:

  * ECG processing on CH1 (if user is in chest-leads mode) — HR / HRV / resp.
  * EMG processing on both channels (if user is in forearm mode) — filtered
    waveform broadcast + live gesture inference using the trained model.
  * Force readings from 3 fingertip FSRs (read from the UDP packet directly).

    pip install fastapi 'uvicorn[standard]' scipy numpy torch
    python dashboard_server.py
    # open http://<this-host>:8000/ in any browser on the same network

If `emg_model.pth` + `emg_norm.npz` aren't present in this folder, the gesture
panel stays empty — everything else still works.

Note: this server binds UDP :5555 — `predict_realtime.py` also wants this port,
so run one at a time per ESP32. (Future: a UDP-broker process to fan out.)
"""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import torch
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from emg_common import (
    parse_packet, SAMPLE_RATE, NUM_CHANNELS, NUM_FSRS,
    WINDOW_SIZE, FSR_FINGERS,
    EMGFilter, EMGGestureNet, Normaliser,
)
from ecg_processing import ECGProcessor


# ── Config ───────────────────────────────────────────────────
UDP_HOST          = "0.0.0.0"
UDP_PORT          = 5555
HTTP_PORT         = 8000
ECG_CHANNEL       = 0          # 0 = CH1 (GPIO 34), 1 = CH2 (GPIO 35)
WAVEFORM_DECIM    = 4          # browser sees 1000 / 4 = 250 Hz
WAVEFORM_HZ       = 20         # broadcast waveform updates per second
VITALS_HZ         = 2          # broadcast metric updates per second
CONTROL_HZ        = 10         # broadcast gesture + force updates per second
STATS_HZ          = 1          # broadcast connection stats per second
HERE              = Path(__file__).parent

# Per-finger force thresholds shown as a tick mark on the gauge — keep in
# sync with HandController.FORCE_THRESHOLD in predict_realtime.py.
FORCE_THRESHOLDS  = [1800, 1800, 1800]


# ── Hub state ────────────────────────────────────────────────
class Hub:
    def __init__(self):
        # ECG path (single channel)
        self.processor = ECGProcessor(fs=SAMPLE_RATE)
        self.disp_queue: list[float] = []
        self._decim_phase = 0

        # EMG path (both channels, streaming filter into a ring buffer)
        self.emg_filter = EMGFilter()
        self._emg_buf_len = SAMPLE_RATE * 3        # 3 s ring buffer
        self.emg_ring = np.zeros((self._emg_buf_len, NUM_CHANNELS), dtype=np.float32)
        self.emg_write_idx = 0
        self.emg_total_samples = 0
        # Decimated EMG waveforms awaiting broadcast (one queue per channel)
        self.emg_disp_ch1: list[float] = []
        self.emg_disp_ch2: list[float] = []
        self._emg_decim_phase = 0

        # Gesture model state — populated by _load_gesture_model() in lifespan
        self.gesture_model = None
        self.gesture_norm = None
        self.gesture_names: list[str] = []
        self.gesture_probs: list[float] = []
        self.current_gesture: str | None = None

        # Connection / packet stats
        self.clients: set[WebSocket] = set()
        self.packets = 0
        self.dropped = 0
        self.last_seq = None
        self.last_packet_t = None
        self.fsr_latest = np.zeros(NUM_FSRS, dtype=np.uint16)

    def ingest_chunk(self, samples_2ch: np.ndarray):
        """(N, 2) int16 → ECG processor + EMG ring buffer + decimated queues."""
        # ── ECG path (CH selected by ECG_CHANNEL) ──
        ecg = samples_2ch[:, ECG_CHANNEL].astype(np.float64)
        filtered_ecg = self.processor.process(ecg)
        for v in filtered_ecg:
            if self._decim_phase == 0:
                self.disp_queue.append(float(v))
            self._decim_phase = (self._decim_phase + 1) % WAVEFORM_DECIM

        # ── EMG path (both channels, into ring buffer) ──
        emg = samples_2ch.astype(np.float32)
        filtered_emg = self.emg_filter.apply(emg)   # streaming IIR
        n = len(filtered_emg)
        end = self.emg_write_idx + n
        if end <= self._emg_buf_len:
            self.emg_ring[self.emg_write_idx:end] = filtered_emg
        else:
            first = self._emg_buf_len - self.emg_write_idx
            self.emg_ring[self.emg_write_idx:] = filtered_emg[:first]
            self.emg_ring[:n - first] = filtered_emg[first:]
        self.emg_write_idx = end % self._emg_buf_len
        self.emg_total_samples += n

        # Decimate EMG into per-channel broadcast queues
        for s in filtered_emg:
            if self._emg_decim_phase == 0:
                self.emg_disp_ch1.append(float(s[0]))
                self.emg_disp_ch2.append(float(s[1]))
            self._emg_decim_phase = (self._emg_decim_phase + 1) % WAVEFORM_DECIM

    def latest_emg_window(self):
        """Most recent WINDOW_SIZE samples as (WINDOW_SIZE, 2). None if not enough yet."""
        if self.emg_total_samples < WINDOW_SIZE:
            return None
        start = (self.emg_write_idx - WINDOW_SIZE) % self._emg_buf_len
        if start + WINDOW_SIZE <= self._emg_buf_len:
            return self.emg_ring[start:start + WINDOW_SIZE].copy()
        first = self.emg_ring[start:].copy()
        return np.vstack([first, self.emg_ring[:WINDOW_SIZE - len(first)].copy()])


hub = Hub()


def _load_gesture_model():
    """Try to load emg_model.pth + emg_norm.npz from this folder.
    No-op if files don't exist — dashboard runs fine without them."""
    model_path = HERE / "emg_model.pth"
    norm_path = HERE / "emg_norm.npz"
    if not (model_path.exists() and norm_path.exists()):
        print(f"  Gesture model not found in {HERE}.")
        print(f"  (Train via record_gestures.py + train_gestures.py to enable the gesture panel.)")
        return
    try:
        ckpt = torch.load(str(model_path), map_location='cpu', weights_only=False)
        hub.gesture_names = list(ckpt['gestures'])
        hub.gesture_model = EMGGestureNet(num_classes=len(hub.gesture_names))
        hub.gesture_model.load_state_dict(ckpt['model_state'])
        hub.gesture_model.eval()
        hub.gesture_norm = Normaliser.load(str(norm_path))
        print(f"  Gesture model loaded — {len(hub.gesture_names)} classes: {hub.gesture_names}")
    except Exception as e:
        print(f"  Failed to load gesture model: {e}")


# ── UDP receiver ─────────────────────────────────────────────
class UDPProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data, addr):
        parsed = parse_packet(data)
        if parsed is None:
            return
        seq, _, samples, fsr = parsed
        if hub.last_seq is not None:
            expected = (hub.last_seq + 1) & 0xFFFF
            if seq != expected:
                hub.dropped += (seq - expected) & 0xFFFF
        hub.last_seq = seq
        hub.packets += 1
        hub.last_packet_t = time.monotonic()
        hub.ingest_chunk(samples)
        hub.fsr_latest = fsr   # Task 3 (dashboard) will pick this up


# ── Broadcast loops ──────────────────────────────────────────
async def _broadcast(payload: str):
    if not hub.clients:
        return
    dead = []
    for ws in list(hub.clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        hub.clients.discard(ws)


async def waveform_loop():
    """Broadcast ECG + both EMG channels at WAVEFORM_HZ. Each message contains
    whatever new samples have accumulated since the last broadcast."""
    period = 1.0 / WAVEFORM_HZ
    while True:
        await asyncio.sleep(period)
        ecg_chunk = hub.disp_queue
        emg_ch1  = hub.emg_disp_ch1
        emg_ch2  = hub.emg_disp_ch2
        if not ecg_chunk and not emg_ch1:
            continue
        hub.disp_queue    = []
        hub.emg_disp_ch1  = []
        hub.emg_disp_ch2  = []
        await _broadcast(json.dumps({
            "type": "waveform",
            "ecg":     ecg_chunk,
            "emg_ch1": emg_ch1,
            "emg_ch2": emg_ch2,
        }))


async def control_loop():
    """At CONTROL_HZ, run gesture inference on the latest EMG window and
    broadcast (gesture, probabilities, FSR readings, thresholds)."""
    period = 1.0 / CONTROL_HZ
    while True:
        await asyncio.sleep(period)

        gesture = hub.current_gesture
        probs   = list(hub.gesture_probs)

        if hub.gesture_model is not None:
            window = hub.latest_emg_window()
            if window is not None:
                X = window.T[None, :, :].astype(np.float32)      # (1, C, T)
                X = hub.gesture_norm.transform(X)
                with torch.no_grad():
                    logits = hub.gesture_model(torch.from_numpy(X))
                    p = torch.softmax(logits, dim=1).numpy()[0]
                probs = [float(x) for x in p]
                gesture = hub.gesture_names[int(p.argmax())]
                hub.gesture_probs = probs
                hub.current_gesture = gesture

        await _broadcast(json.dumps({
            "type":       "control",
            "gesture":    gesture,
            "probs":      probs,
            "names":      hub.gesture_names,
            "fsr":        [int(x) for x in hub.fsr_latest],
            "thresholds": FORCE_THRESHOLDS,
            "fingers":    FSR_FINGERS,
        }))


async def vitals_loop():
    period = 1.0 / VITALS_HZ
    while True:
        await asyncio.sleep(period)
        p = hub.processor
        await _broadcast(json.dumps({
            "type": "vitals",
            "hr":    p.hr_bpm,
            "hrv":   p.hrv_rmssd_ms,
            "sdnn":  p.hrv_sdnn_ms,
            "rr":    p.last_rr_ms,
            "resp":  p.respiration_rate_per_min,
            "rr_history": list(p.rr_intervals_ms),
            "n_beats": len(p.rr_intervals_ms),
        }))


async def stats_loop():
    period = 1.0 / STATS_HZ
    while True:
        await asyncio.sleep(period)
        active = hub.last_packet_t is not None and (time.monotonic() - hub.last_packet_t) < 1.0
        await _broadcast(json.dumps({
            "type": "stats",
            "packets": hub.packets,
            "dropped": hub.dropped,
            "active":  active,
        }))


# ── FastAPI app ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_gesture_model()
    loop = asyncio.get_event_loop()
    transport, _ = await loop.create_datagram_endpoint(
        UDPProtocol, local_addr=(UDP_HOST, UDP_PORT))
    print(f"  UDP listening on {UDP_HOST}:{UDP_PORT}")
    tasks = [
        asyncio.create_task(waveform_loop()),
        asyncio.create_task(vitals_loop()),
        asyncio.create_task(stats_loop()),
        asyncio.create_task(control_loop()),
    ]
    print(f"  Dashboard at http://<host>:{HTTP_PORT}/")
    yield
    for t in tasks:
        t.cancel()
    transport.close()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(HERE / "dashboard.html")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    hub.clients.add(websocket)
    try:
        while True:
            # Block until the client sends anything (or disconnects).
            # We don't expect inbound messages; this just keeps the connection
            # alive and surfaces disconnects as WebSocketDisconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT, log_level="info")
