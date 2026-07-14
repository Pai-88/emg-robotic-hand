"""
Interactive servo calibration for the 5-finger hand.

Use this to dial in the per-finger angles before plugging real EMG into
predict_realtime.py — sweep each servo through its range, find the exact
0° / 180° positions for "fully closed" / "fully open" on YOUR build, and
copy the resulting dict into HandController.GESTURE_ANGLES.

Requires:
    pip install adafruit-circuitpython-servokit

Usage:
    python servo_calibrate.py

REPL commands:
    <ch> <ang>      set channel ch (0–4) to ang° (0–180)
                      example:   1 45      → index to 45°
    s <ch>          sweep one channel 0 → 180 → 0
    s all           sweep all 5 channels sequentially
    open            all fingers to 180°
    close           all fingers to 0°
    rest            all fingers to 90° (safe centre)
    save            print current angles as a Python list
    snap <name>     save current pose under a gesture name (rest/fist/...)
    show            print all stored snapshots
    q               quit (leaves servos where they are)
"""
import sys
import time

try:
    from adafruit_servokit import ServoKit
except ImportError:
    print("ERROR: adafruit-circuitpython-servokit not installed.")
    print("  pip install adafruit-circuitpython-servokit")
    sys.exit(1)

N_SERVOS      = 5
PULSE_RANGE   = (500, 2500)    # MG90S / SG90 full-range pulse widths in µs
FINGER_NAMES  = ['thumb', 'index', 'middle', 'ring', 'pinky']
SAFE_CENTRE   = 90
SWEEP_STEP    = 10
SWEEP_DWELL_S = 0.12


def setup():
    kit = ServoKit(channels=16)
    for ch in range(N_SERVOS):
        kit.servo[ch].set_pulse_width_range(*PULSE_RANGE)
        kit.servo[ch].angle = SAFE_CENTRE
    return kit


def sweep_channel(kit, ch, start=0, end=180, step=SWEEP_STEP, dwell=SWEEP_DWELL_S):
    direction = 1 if end >= start else -1
    print(f"    sweeping CH {ch} ({FINGER_NAMES[ch]}): {start}° → {end}°")
    ang = start
    while (direction == 1 and ang <= end) or (direction == -1 and ang >= end):
        kit.servo[ch].angle = max(0, min(180, ang))
        print(f"\r      angle = {ang:3d}°", end='', flush=True)
        time.sleep(dwell)
        ang += step * direction
    kit.servo[ch].angle = max(0, min(180, end))
    print()


def banner():
    print("=" * 64)
    print("  SERVO CALIBRATION  ·  5-finger hand")
    print("=" * 64)
    print(f"  Channels 0–{N_SERVOS - 1} mapped to: {FINGER_NAMES}")
    print()
    print("  Commands:")
    print("    <ch> <ang>     e.g. '1 45'  → set channel ch to ang°")
    print("    s <ch> | s all                 sweep")
    print("    open | close | rest            macros")
    print("    save                           print current angles")
    print("    snap <name>                    save pose as a named gesture")
    print("    show                           list saved snapshots")
    print("    q                              quit")
    print()


def main():
    banner()
    kit = setup()
    current = [SAFE_CENTRE] * N_SERVOS
    snapshots = {}

    while True:
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        parts = raw.split()
        cmd = parts[0].lower()

        try:
            # ── single-word commands ───────────────────────
            if cmd in ('q', 'quit', 'exit'):
                break

            elif cmd == 'open':
                for ch in range(N_SERVOS):
                    kit.servo[ch].angle = 180; current[ch] = 180
                print("    → all open  [180, 180, 180, 180, 180]")

            elif cmd == 'close':
                for ch in range(N_SERVOS):
                    kit.servo[ch].angle = 0; current[ch] = 0
                print("    → all closed  [0, 0, 0, 0, 0]")

            elif cmd == 'rest':
                for ch in range(N_SERVOS):
                    kit.servo[ch].angle = SAFE_CENTRE; current[ch] = SAFE_CENTRE
                print(f"    → all centre  [{SAFE_CENTRE}] × 5")

            elif cmd == 'save':
                print(f"    current angles: {current}")
                print(f"    paste into HandController.GESTURE_ANGLES if you like.")

            elif cmd == 'snap':
                if len(parts) < 2:
                    print("    usage: snap <gesture-name>")
                    continue
                name = parts[1].lower()
                snapshots[name] = list(current)
                print(f"    saved '{name}' = {current}")

            elif cmd == 'show':
                if not snapshots:
                    print("    (no snapshots yet)")
                else:
                    print("    GESTURE_ANGLES = {")
                    for name, angs in snapshots.items():
                        print(f"        {name!r:10s}: {angs},")
                    print("    }")

            elif cmd == 's':
                if len(parts) < 2:
                    print("    usage: s <ch>  or  s all")
                    continue
                if parts[1].lower() == 'all':
                    for ch in range(N_SERVOS):
                        sweep_channel(kit, ch, 0, 180)
                        sweep_channel(kit, ch, 180, 0)
                        kit.servo[ch].angle = SAFE_CENTRE
                        current[ch] = SAFE_CENTRE
                else:
                    ch = int(parts[1])
                    if not 0 <= ch < N_SERVOS:
                        print(f"    channel out of range (0–{N_SERVOS - 1})")
                        continue
                    sweep_channel(kit, ch, 0, 180)
                    sweep_channel(kit, ch, 180, 0)
                    kit.servo[ch].angle = SAFE_CENTRE
                    current[ch] = SAFE_CENTRE

            else:
                # ── "<ch> <ang>" form ───────────────────────
                ch = int(parts[0])
                ang = int(parts[1])
                if not 0 <= ch < N_SERVOS:
                    print(f"    channel out of range (0–{N_SERVOS - 1})")
                    continue
                if not 0 <= ang <= 180:
                    print("    angle out of range (0–180)")
                    continue
                kit.servo[ch].angle = ang
                current[ch] = ang
                print(f"    CH {ch} ({FINGER_NAMES[ch]}) → {ang}°")

        except (ValueError, IndexError):
            print(f"    unknown command: {raw!r}")
            print("    type 'q' to quit, or see the banner above.")

    print("  done.  servos left at:", current)


if __name__ == '__main__':
    main()
