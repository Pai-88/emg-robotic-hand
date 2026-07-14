# EMG Robotic Hand · Start Here

A wearable EMG → 5-finger robotic hand + a live ECG / vital-signs dashboard.
One ESP32 streams biosignals wirelessly to a Raspberry Pi 5; the Pi does
inference and either drives a servo hand or serves a live dashboard.

---

## Folder layout

```
emg_hand/
├── START_HERE.md                       ← you are here
│
├── firmware/                           ← Arduino sketch for the ESP32
│   └── esp32_emg_streamer/
│       └── esp32_emg_streamer.ino
│
├── pi/                                 ← everything that runs on the Pi
│   ├── emg_common.py                   shared utilities (packet parser,
│   │                                     filters, CNN model, normaliser)
│   ├── ecg_processing.py               R-peak detection · HR · HRV · resp
│   ├── record_gestures.py              record labelled EMG gesture data
│   ├── train_gestures.py               train the 1D-CNN gesture classifier
│   ├── predict_realtime.py             live inference + HandController
│   ├── dashboard_server.py             FastAPI + WebSocket dashboard backend
│   ├── dashboard.html                  browser-side dashboard (uPlot)
│   └── servo_calibrate.py              interactive servo calibration REPL
│
└── docs/                               ← open in any browser
    ├── parts_and_setup.html            BOM + physical layout
    ├── electronics_setup.html          full pin-level wiring of ESP32+AD8232
    ├── pi_servo_wiring.html            Pi 5 ↔ PCA9685 ↔ servos pin map
    └── wearable_design.html            3D-printable forearm pod design
```

---

## What it does

- **Wearable** (forearm-mounted): ESP32 + 2× AD8232 sample 2 biosignal
  channels at 1 kHz and stream binary UDP packets to the Pi over WiFi.
- **Pi 5** receives that stream and runs one of two modes:
  - **Gesture-control mode** — 1D CNN classifies the EMG window into one of
    five gestures (rest / fist / open / pinch / point) and drives a 5-finger
    servo hand through a PCA9685 over I²C.
  - **ECG-dashboard mode** — treats CH1 as Lead-I ECG, detects R-peaks,
    computes HR / HRV / respiration, and serves a live web dashboard at
    `http://<pi-ip>:8000/`.
- The two modes share UDP :5555 — only one runs at a time per session.

---

## Quick start

### Step 0 · Read the visual references

Open these in a browser before wiring anything (double-click the .html):

1. **`docs/parts_and_setup.html`** — what you need to buy and how it all fits.
2. **`docs/electronics_setup.html`** — pin-level wiring of ESP32 + AD8232.
3. **`docs/pi_servo_wiring.html`** — Pi 5 → PCA9685 → servos.
4. **`docs/wearable_design.html`** — 3D-printable forearm pod (optional).

### Step 1 · Flash the ESP32

1. Install **Arduino IDE 2.x**, add **ESP32 board support** (`Boards Manager → esp32`).
2. Open `firmware/esp32_emg_streamer/esp32_emg_streamer.ino`.
3. At the top, set:
   ```c
   const char* WIFI_SSID     = "<your-network>";
   const char* WIFI_PASSWORD = "<your-password>";
   const char* PI_IP         = "<your-pi-ip>";   // find with `hostname -I` on the Pi
   ```
4. Select board: **ESP32 Dev Module**, the right port, and upload.
5. Open Serial Monitor at **115200 baud** — you should see `UDP ready → ...`
   then periodic packet/sample/RSSI lines.

### Step 2 · Wire the analog frontend

Follow `docs/electronics_setup.html` Panel B2. Quick summary:

| AD8232 #1 (CH1) | → ESP32 |
| --- | --- |
| 3.3V → 3V3 ·  GND → GND | shared rail |
| OUTPUT → **GPIO 34** | analog flexor / ECG |
| LO+ → **GPIO 25** ·  LO− → **GPIO 27** | leads-off detection |

| AD8232 #2 (CH2) | → ESP32 |
| --- | --- |
| OUTPUT → **GPIO 35** | analog extensor |
| LO+ → **GPIO 26** ·  LO− → **GPIO 32** | leads-off detection |

Both AD8232 RL pins → one shared reference electrode (bony spot — olecranon or ulnar styloid).

### Step 3 · Set up the Pi

```bash
# Clone / copy this project onto the Pi at ~/Documents/emg_hand
cd ~/Documents/emg_hand/pi

# Use a venv (Bookworm is externally-managed)
python3 -m venv ~/emg-venv
source ~/emg-venv/bin/activate
pip install -U pip
pip install numpy scipy torch scikit-learn fastapi 'uvicorn[standard]'

# For the robotic hand path (Step 5):
sudo raspi-config         # Interface Options → I2C → Enable, then reboot
pip install adafruit-circuitpython-servokit
```

### Step 4 · Verify the data link

With the ESP32 powered and electrodes on:

```bash
# On the Pi
sudo tcpdump -i any -n udp port 5555 -c 5
```

You should see 5 packets received within a second (each is 48 bytes).
If silent, the ESP32 has the wrong `PI_IP` or isn't on the same network.

---

## Step 5 · Pick a mode

### Mode A · Live ECG dashboard (easiest first run)

1. **Re-wire AD8232 #1 to chest** (Lead I):
   - RA → upper-right chest (just below collarbone)
   - LA → upper-left chest (just below collarbone)
   - RL → right hip / lower-right abdomen (reference)
2. **Run the server**:
   ```bash
   source ~/emg-venv/bin/activate
   cd ~/Documents/emg_hand/pi
   python dashboard_server.py
   ```
3. **Open the dashboard** in any browser on the network:
   `http://<pi-ip>:8000/`
4. Within ~10 s of stable contact you should see HR, HRV, ECG waveform, and
   the RR-interval tachogram updating live.

### Mode B · Gesture classification + robotic hand

1. **Place EMG electrodes** on the forearm:
   - CH1 pair (AD8232 #1) over flexor digitorum (palmar side, ⅓ down from elbow)
   - CH2 pair (AD8232 #2) over extensor digitorum (dorsal side, same level)
   - Shared reference at the olecranon (elbow bone)

2. **Record gesture training data**:
   ```bash
   cd ~/Documents/emg_hand/pi
   python record_gestures.py --reps 3 --duration 5
   ```
   Walks through each gesture for 5 s × 3 reps. Saves `gestures.npz`.

3. **Train the model**:
   ```bash
   python train_gestures.py --epochs 80
   ```
   Prints test accuracy + confusion matrix. Saves `emg_model.pth` + `emg_norm.npz`.

4. **Calibrate the servos** (only if you've wired up the PCA9685 + hand):
   ```bash
   python servo_calibrate.py
   ```
   Interactive REPL — see commands below. Find the angles that mean
   "fully open" and "fully closed" for each finger on your build, save snapshots,
   then paste the resulting dict into [`predict_realtime.py:60`](pi/predict_realtime.py) `GESTURE_ANGLES`.

5. **Run live inference**:
   ```bash
   python predict_realtime.py
   ```
   Without a PCA9685 connected: prints `→ <gesture>  [angles]` to the terminal.
   With one connected: drives the actual servos.

---

## `servo_calibrate.py` quick reference

Interactive REPL once the PCA9685 + servos + 5 V PSU are wired:

```
> 1 45               # set channel 1 (index) to 45°
> s 0                # sweep channel 0 (thumb) 0 → 180 → 0
> s all              # sweep all 5 sequentially
> open               # all servos → 180°
> close              # all servos → 0°
> rest               # all servos → 90° (safe centre)
> snap fist          # save current pose under the name 'fist'
> snap pinch         # save current pose under 'pinch'
> show               # prints GESTURE_ANGLES dict to paste into predict_realtime.py
> q                  # quit (leaves servos where they are)
```

---

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| ESP32 stuck on `Connecting…` in Serial Monitor | WiFi creds wrong, or the Pi's hotspot isn't broadcasting. Check from your phone. |
| `tcpdump` shows nothing on the Pi | `PI_IP` in the .ino is wrong, or your network isolates clients (most hotel/uni guest WiFi does — use a hotspot). |
| Flat / dead EMG signal | 90% of the time: electrode contact. Clean skin with alcohol, abrade lightly, re-stick. Check the orange LO LEDs on the AD8232 — if lit, that lead is off. |
| Dashboard shows `--` for HR forever | Need ≥2 R-peaks. Increase signal amplitude (better electrode placement) or lower `RMS_GATE`. The first 30 s of data is filter warm-up. |
| Gesture model predicts one class 100% of the time | StandardScaler leakage or class imbalance. Re-record with more rest data and longer durations, then retrain. |
| Servos jitter / don't respond | Forgot to tie PSU GND to Pi GND — the single most common mistake. See the red warning in `docs/pi_servo_wiring.html`. |
| `i2cdetect -y 1` doesn't show `0x40` | I²C not enabled (`raspi-config`), or SDA/SCL swapped, or the PCA9685 doesn't have its 3V3 supply. |
| `predict_realtime.py` says "print-only mode" | `adafruit-servokit` not installed in the active venv. `pip install adafruit-circuitpython-servokit`. |

---

## Where to next

Once the core is working, easiest upgrades (see `docs/parts_and_setup.html`):

- **MAX30102** (~£5, I²C) — adds SpO2 + PPG waveform + cross-check HR.
- **MPU6050** (~£3, I²C) — wrist orientation, activity classification, gesture disambiguation.
- **NTC thermistor** (~£1) — skin temperature trend.
- **5× FSR-402 force pads** on fingertips — closes the haptic loop on the hand.

All of the above hang off the ESP32's existing I²C bus or a spare ADC pin — no firmware rewrites needed, just one new processor class in `pi/` and a new panel in `dashboard.html`.

For real EEG, you'd need an ADS1299-class front-end (OpenBCI Ganglion / Cyton). The AD8232 isn't built for it.
