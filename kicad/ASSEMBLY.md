# EMG Robotic Hand — Full System (as-built, Rev C)

Captures the **real two-board architecture**: the ESP32 does all sensing and
streams over WiFi/UDP; the Raspberry Pi 5 receives it, runs the classifier, and
drives the servos. The two boards share only a **common star ground** — there is
no data wire between them (the link is WiFi, shown as a note on the sheet).

```
 flexor electrodes  ─▶ AD8232 #1 ─┐
 extensor electrodes─▶ AD8232 #2 ─┤─▶ ESP32 (2×ADC + 3×FSR ADC) ══WiFi/UDP══╗
 3 fingertip FSRs ───────────────┘                                          ║
                                                                            ▼
                        5V PSU ─▶ PCA9685 ─▶ 5 servos ◀── I²C ── Raspberry Pi 5
```

| File | What it is |
|------|-----------|
| `emg_frontend.kicad_sch` | Schematic — open in KiCad ▸ Eeschema |
| `emg_frontend.pdf` | Rendered schematic |
| `emg_frontend_BOM.csv` | Bill of materials |
| `emg_frontend.net` | Netlist |

Verified with KiCad 10.0.4: loads, **ERC = 0 errors**, netlist connectivity
checked (shared RL reference, all 3 FSR dividers, I²C Pi↔PCA9685, independent
servo rail, 22-node star ground). The 26 ERC *warnings* are only the cosmetic
"symbol library `emg` not installed" note — the symbols are embedded, so the file
is self-contained; nothing to install.

---

## Subsystem A — ESP32 sensing board

Powers from a 5 V input (J3) → AMS1117-3.3 → 3.3 V analog/logic rail.

**ESP32 pin map (matches the firmware + `pi/emg_common.py`):**

| ESP32 pin | Net | Role |
|-----------|-----|------|
| GPIO34 | EMG1_OUT | AD8232 **flexor** output (ADC1_CH6) |
| GPIO35 | EMG2_OUT | AD8232 **extensor** output (ADC1_CH7) |
| GPIO25 / GPIO27 | LO1P / LO1N | flexor leads-off (+ / −) |
| GPIO26 / GPIO32 | LO2P / LO2N | extensor leads-off (+ / −) |
| GPIO33 | FSR_TH | fingertip FSR — **thumb** (fsr index 0) |
| GPIO36 (SVP) | FSR_IX | fingertip FSR — **index** (fsr index 1) |
| GPIO39 (SVN) | FSR_MD | fingertip FSR — **middle** (fsr index 2) |
| 3V3 / 5V / GND / EN | power | EN→3V3 (run) |

- All EMG/FSR analog inputs are on **ADC1** (GPIO32–39) — required because ADC2 is
  dead while WiFi is active. GPIO34–39 are input-only, fine for analog in.
- **FSR wiring**: each FSR is the top half of a divider — `3V3 — FSR — node — 10k
  (R1/R2/R3) — GND`, node → ADC. Firmware reads raw 12-bit ADC (`FORCE_THRESHOLD`
  ≈ 1800 halts the finger).
- **AD8232**: both run at 3.3 V (matches the ADC reference — never 5 V). `SDN` tied
  high. `RL` (right-leg drive) is **one shared reference electrode** for both
  channels (net `E_RL`, on the flexor connector J1). RA/LA are the two measurement
  electrodes per muscle group.

> **Packet format is 54 bytes**: header + seq + ts + 10 sample-pairs + 3 FSR
> uint16 (thumb/index/middle). Keep the schematic's FSR order = firmware order.

---

## Subsystem B — Raspberry Pi 5 actuation

The Pi (A1) drives the PCA9685 over I²C and receives the UDP stream in software.

| Pi 5 header | Net | To |
|-------------|-----|----|
| pin 1 (3V3) | PI_3V3 | PCA9685 VCC (logic only) |
| pin 3 (GPIO2 / SDA) | SDA | PCA9685 SDA (addr **0x40**) |
| pin 5 (GPIO3 / SCL) | SCL | PCA9685 SCL |
| pin 6 (GND) | GND | PCA9685 GND + PSU GND (star point) |

- **Servo power is a separate 5 V PSU** (J4 → net `+5VSRV`), never the Pi rail.
  Size it for all five servos stalling at once (SG90 ≈ 700 mA ea ⇒ ~3–4 A).
  C5 (470 µF) buffers spikes; add more bulk at the headers if the Pi browns out.
- **Tie all grounds at one point** (Pi GND, PSU GND, PCA9685 GND) — this is the
  single most important wiring detail for clean servo behaviour.
- Servo channels: PWM0=thumb, 1=index, 2=middle, 3=ring, 4=pinky (J5–J9).
- Set PCA9685 to **50 Hz**. `OE` tied to GND (always enabled) — move to a Pi GPIO
  if you want a hardware "relax hand" line.

---

## BOM (headline)

ESP32-DevKitC · 2× AD8232 breakout · AMS1117-3.3 · Raspberry Pi 5 · PCA9685 ·
3× FSR-402 (+ 3× 10k) · 5× hobby servo · electrode + servo + power connectors ·
10µF/100nF/470µF caps. Full list with footprints in `emg_frontend_BOM.csv`.

---

## Turning it into board(s)

The schematic is one sheet with two ground-shared subsystems. For real hardware
you'd typically fab **one small ESP32 sensor board** and keep the Pi + PCA9685 as
modules on a servo-power harness. KiCad has no CLI router, so layout is a GUI step:

1. Open `emg_frontend.kicad_pro` → PCB Editor → **Tools ▸ Update PCB from Schematic (F8)**.
2. Keep the two EMG analog traces short and away from servo power/PWM.
3. Ground pour both layers; single star-ground stitch.
4. Fab export once routed:
   `kicad-cli pcb export gerbers --output gerbers/ emg_frontend.kicad_pcb`

## Caveats
- Symbols are functional labeled-pin blocks (correct for connectivity/BOM/wiring),
  module footprints are generic headers sized per breakout — confirm each board's
  exact pinout before ordering a PCB.
- FSR ADC pins (GPIO33/36/39) are reconstructed from the docs + `emg_common.py`
  because the canonical `.ino` in `firmware/` was overwritten with a turbidity
  test. **Re-confirm against your real streamer sketch** and tell me if any FSR
  pin differs — it's a one-line change in the generator.
