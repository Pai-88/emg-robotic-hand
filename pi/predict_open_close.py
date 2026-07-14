"""
Simple open/close hand control via RMS threshold — no trained model required.

Reads ONE MyoWare 2.0 SIG channel from the ESP32 stream (CH1 / GPIO 34),
applies a short moving-average smoother, compares amplitude to a threshold,
and drives the HandController:

    flexor amplitude  >  threshold  →  close (fist)
    flexor amplitude  <  threshold  →  open  (default safe state)

This is the classic single-channel myoelectric control scheme:
flex = close, relax = open. Force-feedback from the fingertip FSRs is
preserved — any finger whose FSR exceeds FORCE_THRESHOLD halts its closing
motion (egg-grip behaviour).

Calibration happens automatically at startup:
    1. Hold rest for 5 s — baseline mean + std recorded.
    2. Threshold set to baseline_mean + K × baseline_std.

Usage:
    python predict_open_close.py
    python predict_open_close.py --k 5         # higher → harder to trigger
    python predict_open_close.py --manual 800  # skip calibration, T_close = 800

If you wire a 2nd MyoWare (CH2 → GPIO 35) later, switch to the original
2-channel version by editing CHANNEL_MODE below or re-running with
--channels 2.
"""
import argparse
import time
from collections import deque

import numpy as np

from emg_common import EMGReceiver, WINDOW_SIZE, WINDOW_HOP, NUM_CHANNELS
from predict_realtime import HandController


CALIBRATION_SECONDS = 5      # how long to record baseline at startup
THRESHOLD_K         = 4.0    # T = baseline_mean + K × baseline_std
STEP_INTERVAL_S     = 1.0 / 30.0   # 30 Hz force-feedback step
INFERENCE_HZ        = 20     # how often we read a new RMS window
ACTIVATION_HOLD_S   = 0.2    # debounce — must stay above threshold this long


def rms_of_window(window):
    """Per-channel RMS amplitude of a (T, C) float window."""
    return np.sqrt(np.mean(window.astype(np.float32) ** 2, axis=0))


def calibrate(rx, seconds, n_channels=1):
    """Sample `seconds` of rest data and return (mean, std) for CH1.
    (CH2 is ignored in 1-channel mode; included only if n_channels=2.)"""
    print(f"\n  Calibrating baseline — keep your arm RELAXED for {seconds} s ...")
    start = time.monotonic()
    while time.monotonic() - start < seconds:
        rx.poll()
        time.sleep(0.05)
    win = rx.get_latest_window(int(seconds * 1000))
    if win is None:
        raise RuntimeError("Not enough samples received during calibration.")
    win = win.astype(np.float32)
    abs_win = np.abs(win)
    means = abs_win.mean(axis=0)
    stds  = abs_win.std(axis=0)
    print(f"  Baseline mean: CH1={means[0]:7.1f}" + (f"  CH2={means[1]:7.1f}" if n_channels == 2 else ""))
    print(f"  Baseline std : CH1={stds[0]:7.1f}" + (f"  CH2={stds[1]:7.1f}" if n_channels == 2 else ""))
    return means, stds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--k', type=float, default=THRESHOLD_K,
                        help='threshold = baseline_mean + K * baseline_std (default 4)')
    parser.add_argument('--cal-seconds', type=float, default=CALIBRATION_SECONDS,
                        help='seconds of rest used for baseline (default 5)')
    parser.add_argument('--manual', type=float, metavar='T_CLOSE',
                        help='skip calibration, use this single threshold for CH1')
    parser.add_argument('--channels', type=int, default=1, choices=[1, 2],
                        help='1 = MyoWare CH1 only (default), 2 = CH1 flexor + CH2 extensor')
    args = parser.parse_args()

    hand = HandController()
    print("═" * 62)
    if args.channels == 1:
        print("  Open / Close controller · 1-CHANNEL mode (CH1 / GPIO 34)")
        print("  Flex forearm = close · Relax = open")
    else:
        print("  Open / Close controller · 2-CHANNEL mode")
        print("  CH1 flexor = close · CH2 extensor = open")
    print("═" * 62)

    last_step_t = time.monotonic()
    last_infer_total = 0
    activation_state = 'open'   # safe default: hand open when relaxed
    activation_since = time.monotonic()
    activation_print = None

    with EMGReceiver(filtered=True) as rx:
        print("\n  Waiting for ESP32 stream...", end='', flush=True)
        while rx.total_samples < 200:
            rx.poll()
            time.sleep(0.05)
            print('.', end='', flush=True)
        print(" connected.")

        if args.manual is not None:
            t_close = args.manual
            t_open  = args.manual    # not used in 1-channel mode
            print(f"\n  Manual threshold: CH1 (close) > {t_close:.1f}")
        else:
            means, stds = calibrate(rx, args.cal_seconds, n_channels=args.channels)
            t_close = means[0] + args.k * stds[0]
            t_open  = (means[1] + args.k * stds[1]) if args.channels == 2 else 0.0
            print(f"  Threshold (K={args.k}):  CH1 (close) > {t_close:.1f}"
                  + (f"   CH2 (open) > {t_open:.1f}" if args.channels == 2 else ""))

        print(f"\n  Streaming. Flex → close · Relax → open · FSRs handle force feedback.\n")

        while True:
            rx.poll()
            now = time.monotonic()

            # Force-feedback step at 30 Hz
            if now - last_step_t >= STEP_INTERVAL_S:
                hand.step(rx.fsr_latest)
                last_step_t = now

            # Read a window every WINDOW_HOP samples (~20 Hz)
            if rx.total_samples - last_infer_total < WINDOW_HOP:
                time.sleep(0.001)
                continue
            window = rx.get_latest_window(WINDOW_SIZE)
            if window is None:
                continue
            last_infer_total = rx.total_samples

            abs_win = np.abs(window.astype(np.float32))
            amp_ch1 = float(abs_win[:, 0].mean())

            # ── 1-channel decision: flex above threshold → close, otherwise → open ──
            if args.channels == 1:
                target = 'fist' if amp_ch1 > t_close else 'open'
                amps_str = f"CH1={amp_ch1:6.1f}"
            else:
                amp_ch2 = float(abs_win[:, 1].mean())
                if amp_ch1 > t_close and amp_ch1 > amp_ch2:
                    target = 'fist'
                elif amp_ch2 > t_open and amp_ch2 > amp_ch1:
                    target = 'open'
                else:
                    target = 'rest'
                amps_str = f"CH1={amp_ch1:6.1f}  CH2={amp_ch2:6.1f}"

            # Debounce: only commit on changes stable for ACTIVATION_HOLD_S
            if target != activation_state:
                if activation_print != target:
                    activation_since = now
                    activation_print = target
                if now - activation_since >= ACTIVATION_HOLD_S:
                    activation_state = target
                    hand.set_target(target)
                    print(f"  [{int((now - activation_since) * 1000):3d}ms hold] → {target:5s}   {amps_str}")
            else:
                activation_print = None


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n  stopped.")
