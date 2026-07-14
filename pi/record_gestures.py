"""
Interactive gesture data collection.

Walks through each gesture in GESTURES, records `duration` seconds of
dual-channel EMG per repetition, and saves the raw + windowed data to
an .npz file.

Run on whichever machine is on the same network as the ESP32 (Pi or
laptop). The ESP32's PI_IP must point at this machine.

    python record_gestures.py --reps 3 --duration 5
"""
import argparse
import time
import numpy as np
from emg_common import (
    EMGReceiver, GESTURES, SAMPLE_RATE,
    WINDOW_SIZE, WINDOW_HOP, filter_offline, window_signal,
)


def wait_for_n_samples(rx, n):
    """Block until at least n more samples have arrived."""
    start_total = rx.total_samples
    while rx.total_samples - start_total < n:
        rx.poll()
        time.sleep(0.005)


def grab_last_n(rx, n):
    """Pull the most recent n samples from the ring buffer as (n, C)."""
    end = rx.write_idx
    start = (end - n) % len(rx.buf)
    if start + n <= len(rx.buf):
        return rx.buf[start:start + n].copy()
    first = rx.buf[start:].copy()
    return np.vstack([first, rx.buf[:n - len(first)].copy()])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=float, default=5.0,
                        help='seconds of recording per gesture per rep')
    parser.add_argument('--reps', type=int, default=3,
                        help='repetitions per gesture')
    parser.add_argument('--rest-between', type=float, default=2.0,
                        help='seconds of countdown between recordings')
    parser.add_argument('--output', default='gestures.npz')
    args = parser.parse_args()

    print("=" * 60)
    print("  EMG Gesture Recorder")
    print("=" * 60)
    print(f"  Gestures:  {GESTURES}")
    print(f"  Schedule:  {args.duration}s × {args.reps} reps × {len(GESTURES)} gestures")
    print(f"  Output:    {args.output}")
    print("\n  Place electrodes: CH1 on forearm flexors, CH2 on extensors.")
    print("  Press ENTER to begin. (Ctrl-C to abort.)")
    input()

    raw_by_label = {g: [] for g in GESTURES}

    with EMGReceiver() as rx:
        print("  Waiting for ESP32 stream...", end='', flush=True)
        while rx.total_samples < SAMPLE_RATE:
            rx.poll()
            time.sleep(0.05)
            print(".", end='', flush=True)
        print(f" got first samples (write_idx={rx.write_idx})")

        for rep in range(args.reps):
            print(f"\n--- Rep {rep + 1}/{args.reps} ---")
            for gesture in GESTURES:
                for s in range(int(args.rest_between), 0, -1):
                    print(f"  Next: '{gesture}' in {s}...   ", end='\r', flush=True)
                    time.sleep(1)
                print(f"  → Hold '{gesture}' for {args.duration:.1f}s ...", end='', flush=True)
                wait_for_n_samples(rx, int(args.duration * SAMPLE_RATE))
                chunk = grab_last_n(rx, int(args.duration * SAMPLE_RATE))
                raw_by_label[gesture].append(chunk)
                print(f" done ({len(chunk)} samples)")

        print(f"\n  Dropped packets during session: {rx.dropped}")

    # ── Offline filter + windowing for the training-set view ──
    print("\n  Filtering and windowing...")
    X_all, y_all = [], []
    raw_concat = {}
    for label_idx, gesture in enumerate(GESTURES):
        raw = np.vstack(raw_by_label[gesture]).astype(np.int16)
        raw_concat[f'raw_{gesture}'] = raw
        filtered = filter_offline(raw)
        windows = window_signal(filtered, WINDOW_SIZE, WINDOW_HOP)
        X_all.append(windows)
        y_all.append(np.full(len(windows), label_idx, dtype=np.int64))
        print(f"    {gesture}: {raw.shape[0]} raw samples → {len(windows)} windows")

    X = np.concatenate(X_all, axis=0)
    y = np.concatenate(y_all, axis=0)

    np.savez(
        args.output,
        X=X, y=y,
        gestures=np.array(GESTURES),
        window_size=WINDOW_SIZE,
        window_hop=WINDOW_HOP,
        sample_rate=SAMPLE_RATE,
        **raw_concat,
    )
    print(f"\n  Saved {X.shape} → {args.output}")
    print(f"  (Raw arrays also saved as raw_<gesture> for re-windowing.)")


if __name__ == '__main__':
    main()
