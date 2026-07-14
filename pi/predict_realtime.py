"""
Real-time gesture inference from the live ESP32 EMG stream.

  * Receives UDP packets, filters online, slides a 200 ms window.
  * Runs the trained CNN every WINDOW_HOP samples (~20 Hz).
  * RMS-gates quiet windows to 'rest' to suppress idle jitter.
  * Majority-votes the last N predictions for stability.
  * Dispatches the stable gesture to HandController.

Replace HandController.set() with your servo driver (Adafruit ServoKit,
PCA9685, dynamixel, whatever you're using). Until you do, it just prints.

    python predict_realtime.py --model emg_model.pth --norm emg_norm.npz
"""
import argparse
import time
from collections import deque

import numpy as np
import torch

from emg_common import (
    EMGReceiver, EMGGestureNet, Normaliser,
    WINDOW_SIZE, WINDOW_HOP, RMS_GATE,
)

try:
    from adafruit_servokit import ServoKit
    _SERVOKIT_AVAILABLE = True
except ImportError:
    _SERVOKIT_AVAILABLE = False


class HandController:
    """Drives a 5-finger servo hand through a PCA9685, with force feedback
    from 3 fingertip FSRs (thumb / index / middle).

    Two-stage control loop:
      • set_target(gesture)  — load the desired pose into self.target_angles.
                                Called when a new gesture is detected.
      • step(fsr_readings)   — advance current_angles one tick toward target,
                                halting the close-direction step on any finger
                                whose FSR reading exceeds FORCE_THRESHOLD.
                                Call at ~30 Hz from the main loop.

    Falls back to print-only mode if `adafruit-servokit` isn't installed.

    Channel map (PCA9685 channel → finger):
        0 = thumb · 1 = index · 2 = middle · 3 = ring · 4 = pinky
    FSR map (fsr_readings[i] → finger):
        0 = thumb · 1 = index · 2 = middle    (no FSR on ring / pinky)

    Wiring (Pi 5 → PCA9685):
        Pi 3V3 (pin 1) → PCA9685 VCC
        Pi GND (pin 6) → PCA9685 GND
        Pi SDA (pin 3) → PCA9685 SDA
        Pi SCL (pin 5) → PCA9685 SCL
        External 5–6 V PSU → PCA9685 V+   (separate terminal block)
        PSU GND → PCA9685 V+ GND  AND  Pi GND   ← common ground, mandatory

    Setup once on the Pi:
        sudo raspi-config   → Interface Options → I2C → Enable, reboot
        i2cdetect -y 1      → PCA9685 should appear at 0x40
        pip install adafruit-circuitpython-servokit
    """

    # 0° = closed (tendon pulled), 180° = open. Flip values per finger if
    # your specific hand build moves the wrong way.
    GESTURE_ANGLES = {
        'rest':  [180, 180, 180, 180, 180],   # all open (default)
        'open':  [180, 180, 180, 180, 180],   # all open
        'fist':  [  0,   0,   0,   0,   0],   # all closed
        'pinch': [  0,   0, 180, 180, 180],   # thumb + index closed only
        'point': [180,   0, 180, 180, 180],   # index extended, rest closed
    }

    # MG90S / SG90 typically need 500–2500 µs to reach the full 0–180°.
    PULSE_WIDTH_RANGE_US = (500, 2500)

    # Per-finger FSR thresholds (raw ADC 0–4095). Above this → stop closing.
    # Tune empirically with servo_calibrate.py: at rest the FSR reads ~50,
    # at hard squeeze ~3500+. Start around 40–50% of your hard-squeeze value.
    FORCE_THRESHOLD = [1800, 1800, 1800]   # thumb, index, middle

    # Motion smoothing. At step() called every ~33 ms (30 Hz), a step of 8°
    # means full close (180 → 0) takes ~750 ms — feels natural, gives the
    # force loop time to react before crushing.
    MAX_STEP_DEG = 8.0

    def __init__(self, n_servos=5):
        self.n_servos = n_servos
        self.target_angles  = [90.0] * n_servos    # safe centre
        self.current_angles = [90.0] * n_servos
        self.current_gesture = None
        self._blocked_prev = [False] * n_servos

        if _SERVOKIT_AVAILABLE:
            self.kit = ServoKit(channels=16)
            for ch in range(n_servos):
                self.kit.servo[ch].set_pulse_width_range(*self.PULSE_WIDTH_RANGE_US)
                self.kit.servo[ch].angle = 90
            self.set_target('rest')
            print("  [HandController] PCA9685 connected — moving to 'rest'")
        else:
            self.kit = None
            print("  [HandController] adafruit-servokit not installed — print-only mode")

    # ─────────────────────────────────────────────────────────
    def set_target(self, gesture):
        """Update the desired pose. Servos move toward it via step()."""
        if gesture == self.current_gesture:
            return
        angles = self.GESTURE_ANGLES.get(gesture)
        if angles is None:
            return
        self.target_angles = [float(a) for a in angles[: self.n_servos]]
        self.current_gesture = gesture
        if self.kit is None:
            print(f"  → target: {gesture}  {[int(a) for a in self.target_angles]}")

    # Backwards-compatible alias for the old call site.
    def set(self, gesture):
        self.set_target(gesture)

    # ─────────────────────────────────────────────────────────
    def step(self, fsr_readings=None):
        """Advance current_angles one tick toward target_angles.
        Respects per-finger force feedback for thumb / index / middle.

        fsr_readings: optional length-≥3 array-like of uint16 ADC counts.
                      If None or shorter, no force blocking is applied.
        """
        blocked = [False] * self.n_servos
        if fsr_readings is not None:
            for ch in range(min(3, self.n_servos, len(fsr_readings))):
                if int(fsr_readings[ch]) > self.FORCE_THRESHOLD[ch]:
                    blocked[ch] = True

        for ch in range(self.n_servos):
            target  = self.target_angles[ch]
            current = self.current_angles[ch]
            closing = target < current   # lower angle = more closed

            if closing and blocked[ch]:
                # Hold the finger where it is — and edge-trigger a log
                if not self._blocked_prev[ch] and self.kit is None:
                    print(f"  ✋ force blocked finger {ch} at {current:.0f}°")
                self._blocked_prev[ch] = True
                continue
            self._blocked_prev[ch] = False

            delta = target - current
            step = max(-self.MAX_STEP_DEG, min(self.MAX_STEP_DEG, delta))
            new_angle = max(0.0, min(180.0, current + step))
            self.current_angles[ch] = new_angle
            if self.kit is not None:
                self.kit.servo[ch].angle = new_angle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='emg_model.pth')
    parser.add_argument('--norm',  default='emg_norm.npz')
    parser.add_argument('--smooth', type=int, default=5,
                        help='majority-vote length (default 5 = 250 ms @ 20 Hz)')
    args = parser.parse_args()

    ckpt = torch.load(args.model, map_location='cpu', weights_only=False)
    gestures = list(ckpt['gestures'])
    model = EMGGestureNet(num_classes=len(gestures))
    model.load_state_dict(ckpt['model_state'])
    model.eval()
    norm = Normaliser.load(args.norm)
    rest_idx = gestures.index('rest') if 'rest' in gestures else None

    smoothing = deque(maxlen=args.smooth)
    hand = HandController()

    print(f"  Classes: {gestures}")
    print(f"  RMS gate: {RMS_GATE}  smoothing: {args.smooth} windows")
    print(f"  Listening on UDP {EMGReceiver().port}...\n")

    STEP_INTERVAL_S = 1.0 / 30.0   # 30 Hz force-feedback control loop

    with EMGReceiver(filtered=True) as rx:
        last_inference_total = 0
        last_step_t = time.monotonic()
        while True:
            rx.poll()
            now = time.monotonic()

            # Force-feedback step — independent of inference cadence so the
            # hand reacts to fingertip pressure faster than gesture changes.
            if now - last_step_t >= STEP_INTERVAL_S:
                hand.step(rx.fsr_latest)
                last_step_t = now

            # Inference fires once per WINDOW_HOP new samples (~20 Hz)
            if rx.total_samples - last_inference_total < WINDOW_HOP:
                time.sleep(0.001)
                continue
            window = rx.get_latest_window(WINDOW_SIZE)
            if window is None:
                continue
            last_inference_total = rx.total_samples

            rms = float(np.sqrt(np.mean(window.astype(np.float32) ** 2)))
            if rms < RMS_GATE and rest_idx is not None:
                pred = rest_idx
            else:
                X = window.T[None, :, :].astype(np.float32)   # (1, C, T)
                X = norm.transform(X)
                with torch.no_grad():
                    pred = int(model(torch.from_numpy(X)).argmax(1).item())

            smoothing.append(pred)
            counts = np.bincount(smoothing, minlength=len(gestures))
            hand.set_target(gestures[int(counts.argmax())])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n  stopped.")
