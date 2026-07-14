# DAY 1 · Get the Signal

> By end of today: EMG waveform on the dashboard when you flex.
> No FSRs. No robotic hand. Just: **skin → ESP32 → WiFi → Pi → browser**.

If any step fails, **stop and ping back** — fixing a wiring/flash issue takes me 2 min from a screenshot; chasing it solo can burn an hour.

---

## STEP 0 · Inventory + order (15 min)

**On the desk:**

- [ ] ESP32 DevKit V1 × 1
- [ ] AD8232 module × 2
- [ ] Raspberry Pi 5 + 27 W USB-C PSU + microSD with Pi OS installed and updated
- [ ] Breadboard (half-size minimum, ideally full)
- [ ] Jumper wires (M-M and M-F mix — ~30 of each)
- [ ] Ag/AgCl gel electrodes — ≥ 6 fresh pads, sealed pack
- [ ] Electrode lead set: 3.5 mm jack → 3 snaps × 2 sets
- [ ] USB-C cable for ESP32
- [ ] Laptop with Arduino IDE 2.x installed + ESP32 board support

**Order today** (Amazon Prime, 1–2 day arrival):

- [ ] 5× **FSR-402** (search: "Interlink FSR 402" or "0.5 inch thin-film force-sensitive resistor")
- [ ] 5× **MG90S micro servos** (metal gear, ~£4 each)
- [ ] 1× **PCA9685** 16-channel PWM driver (Adafruit clone is fine)
- [ ] 1× **5 V / 5 A DC mains adapter** with barrel jack
- [ ] 1× pack of **10 kΩ resistors** (for FSR voltage dividers — a £3 starter pack of 100 is overkill but fine)

✅ **Done when:** inventory list ticked + Amazon receipt timestamped.

---

## STEP 1 · Wire the EMG frontend (60–90 min)

Reference: open `docs/electronics_setup.html` Panel B2 — that's your wiring chart.

**AD8232 #1 → ESP32:**

| AD8232 pin | ESP32 pin |
|---|---|
| `3.3V` | `3V3` |
| `GND` | `GND` |
| `OUTPUT` | `GPIO 34` |
| `LO+` | `GPIO 25` |
| `LO-` | `GPIO 27` |

**AD8232 #2 → ESP32:**

| AD8232 pin | ESP32 pin |
|---|---|
| `3.3V` | `3V3` (same rail) |
| `GND` | `GND` |
| `OUTPUT` | `GPIO 35` |
| `LO+` | `GPIO 26` |
| `LO-` | _leave open_ (will be repurposed for FSR thumb on Step 5+) |

✅ **Done when:** every connection double-checked against the diagram. No bare wires touching each other. The breadboard looks tidy, not like a haystack.

📸 **Photograph the wiring before you flash.** Lets me debug from a distance.

---

## STEP 2 · Flash the ESP32 (30 min)

1. Arduino IDE → **File → Open** → `firmware/esp32_emg_streamer/esp32_emg_streamer.ino`
2. At the top, edit four lines:
   ```c
   const char* WIFI_SSID     = "<your-network>";
   const char* WIFI_PASSWORD = "<your-password>";
   const char* PI_IP         = "<your-pi-ip>";   // run `hostname -I` on the Pi
   const bool  FSR_ENABLED   = false;             // no FSRs yet
   ```
3. **Tools → Board** → ESP32 Dev Module
4. Plug in ESP32 → **Tools → Port** → the new `/dev/cu.usbserial-…` (Mac) or `COMx` (Win)
5. Upload (takes ~30–60 s)
6. **Tools → Serial Monitor** → 115200 baud

✅ **Done when:** you see this in Serial Monitor:
```
UDP ready → <your-pi-ip>:5555
[5s] Pkts:500 | Smp:5000 | Rate:1000Hz | LO1:OFF LO2:OFF | FSR T/I/M: 0/0/0 | WiFi:OK (-50)
```

A status line every 5 s = good. Stuck on `Connecting…` for > 30 s = WiFi creds wrong.

---

## STEP 3 · Pi setup (30–45 min)

SSH into the Pi (or directly on its keyboard):

```bash
# Enable I²C for later (you'll need it for the hand in Step 6+)
sudo raspi-config
#   → Interface Options → I2C → Enable → reboot

# Project Python deps
cd ~/Documents/emg_hand/pi
python3 -m venv ~/emg-venv
source ~/emg-venv/bin/activate
pip install -U pip
pip install numpy scipy torch scikit-learn fastapi 'uvicorn[standard]'

# Confirm the ESP32 is reaching the Pi
sudo tcpdump -i any -n udp port 5555 -c 5
#   → should print 5 packet lines within ~1 second
```

✅ **Done when:** `tcpdump` prints 5 UDP packets from the ESP32's IP.

If silent: `PI_IP` in the .ino is wrong, *or* your network blocks client-to-client traffic. Most university/hotel WiFi does this — **switch to a phone hotspot** for development, it always works.

---

## STEP 4 · Run the dashboard (15 min)

```bash
source ~/emg-venv/bin/activate
cd ~/Documents/emg_hand/pi
python dashboard_server.py
```

Open `http://<pi-ip>:8000/` from any browser (laptop, phone, the Pi itself).

✅ **Done when:** dashboard loads, the green dot in the top-right is pulsing, footer shows "ESP32 streaming". You'll see:
- EMG / ECG waveform panels (flat — electrodes not on skin yet)
- Force gauges at 0 (no FSRs yet)
- Confidence bars panel says "no model loaded" (haven't trained yet)
- Vitals all `--`

All of that is correct for Step 4.

---

## STEP 5 · First EMG signal — the moment (20 min)

**Electrode placement** (right forearm, palm down):

- **CH1 pair (AD8232 #1):** two pads ~2 cm apart on the **flexor** — palmar side, about ⅓ of the way down from your elbow to your wrist.
- **CH2 pair (AD8232 #2):** two pads ~2 cm apart on the **extensor** — dorsal side, same height as CH1.
- **Reference (RL):** one pad on a bony spot — the **olecranon** (elbow point) works perfectly. Both AD8232 RL leads go to this single pad.

**Prep the skin:**
1. Wipe each site with an alcohol pad
2. Press the electrodes firmly for 5 s each to activate the gel
3. Plug the 3.5 mm jacks into the AD8232 boards

✅ **Done when:** on the dashboard EMG panel, **make a fist → the orange (CH1) trace jumps and oscillates**. Open hand and **the cyan (CH2) trace jumps**. Resting → both nearly flat.

📸 **Screenshot the dashboard with both channels firing.**

That's your Day 1 ship moment. Send the screenshot to me + your team + celebrate it. The hard part is done — everything downstream is just extension.

---

## Stuck? Send me this

If anything in any step doesn't behave like the ✅ line says it should, paste me:

1. **Serial Monitor's last 10 lines** (from Step 2)
2. **A photo of the wiring**
3. **A screenshot of the dashboard** (if it loaded at all)
4. **The exact command that failed + its output**

Usually that's enough to spot the issue from 4000 miles away. Don't burn an hour solo — ping back fast.

---

## When Day 1 ships

You'll feel the urge to keep going into Day 2 immediately. **Sleep instead.** The recording session on Day 3 needs you sharp, not exhausted. Day 1 ending with a working signal at midnight is much better than Day 2 starting with a broken pipeline at 3 a.m.
