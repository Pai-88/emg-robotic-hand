# Demo Video · Script & Shot List

**60-second video clip embedded on slide 6 of `EMG_Hand_Presentation.pptx`.**

This is the single most important visual in the whole pitch. The audience will remember the demo and the cost slide; everything else is supporting evidence. Invest the time to make it good — shoot it twice if needed.

---

## Format

| | |
|---|---|
| Duration | **60 s** (45–60 s acceptable) |
| Resolution | 1920 × 1080 minimum, 30 fps |
| Audio | **Silent + text overlays + soft music bed.** The presenter narrates live over the video; no double-voice. |
| Aspect | 16:9 landscape |
| Format | `.mp4` (H.264), embeddable in PowerPoint |
| Where to put it | `demo.mp4` in this project folder — drag onto slide 6 in PowerPoint |

---

## Equipment checklist · bring this on shoot day

**Hardware**
- [ ] Wearable pod (charged · electrodes loaded with gel · tested 30 min before)
- [ ] **Spare electrode pads** — at least 6 (gel-pads dry out)
- [ ] Robotic hand (calibrated · `GESTURE_ANGLES` set · dry-test passed twice)
- [ ] PCA9685 + servos + 5 V PSU + Pi 5 (cabled together · I²C confirmed via `i2cdetect`)
- [ ] Display showing dashboard (HDMI monitor / iPad / laptop — see Beat 1)
- [ ] Phone/camera + tripod

**The "props"**
- [ ] **Raw eggs × 3** (one for the take, two for retakes — and accept that one will break)
- [ ] Marshmallow × 2 (warm-up + take)
- [ ] Paper cup, half-filled with water (closer — the "doesn't crumple" final beat)
- [ ] Small clean surface to place egg on (white cloth or paper looks best on camera)

**Support**
- [ ] Bright, even lighting — overhead office light + maybe one desk lamp from a side. Avoid harsh shadows on the hand.
- [ ] Plain background (paint a board matte black, or use a white wall — both work)
- [ ] Editing software open + ready to import: **CapCut** (phone, easiest) or **DaVinci Resolve** (laptop, more powerful, free)
- [ ] Royalty-free music track downloaded ahead of time (~80 BPM, instrumental, see Editing Notes)

---

## The 60-second arc · 4 beats

### Beat 1 · Setup (0:00 – 0:08) — *8 seconds*

> Goal: in 8 seconds, show what the device is, that it's on a person, and that the dashboard is live.

| Time | Shot | What happens | Text overlay |
|---|---|---|---|
| 0:00 | **S1** — wide medium shot, person seated at a desk, wearable visible on forearm, robotic hand on the table | hold for 2 s, slow pan | `LOW-COST MYOELECTRIC HAND` (top-left, fades after 2 s) |
| 0:02 | **S2** — close-up of wearable strapped to forearm, cable running to robotic hand | hold 2 s | `2-CH SURFACE EMG  ·  1 kHz` (bottom-right) |
| 0:04 | **S3** — close-up of the dashboard on screen, ECG / EMG waveforms scrolling, "no gesture yet" | hold 2 s | `LIVE INFERENCE @ 20 Hz` |
| 0:06 | **S4** — cut back to wide, person flexes wrist gently for the first time, hand moves slightly | hold 2 s | (no overlay) |

---

### Beat 2 · Gesture set (0:08 – 0:22) — *14 seconds*

> Goal: show 4 distinct gestures, and prove the system *visibly thinks* by cutting to the confidence bars at each one.

For each gesture: ~3 seconds. Use this pattern: **hand action → cut to dashboard → cut back**.

| Time | Shot | What happens | Text overlay |
|---|---|---|---|
| 0:08 | **S5** — wide, person makes a **fist** | hand closes ~1 s | `fist` (large, lower-third, matches dashboard colour) |
| 0:09 | **S6** — dashboard close-up, "fist" confidence bar climbs to ~95 % | hold 1.5 s |   |
| 0:11 | **S7** — wide, person opens hand fully | hand opens | `open` |
| 0:12 | **S8** — dashboard close, "open" bar peaks | hold 1.5 s |   |
| 0:14 | **S9** — close-up of the wearer's hand performing **pinch** | thumb + index together | `pinch` |
| 0:15 | **S10** — dashboard close, "pinch" bar peaks | hold 1.5 s |   |
| 0:17 | **S11** — robotic hand close-up doing **point** (index extended) | hold 2 s | `point` |
| 0:19 | **S12** — half-screen split: wearer's hand AND robotic hand mirroring in sync, doing fist → open | 3 s |   |

> **Editing tip:** beat 2 lives or dies on rhythm. Each gesture transition should land *on* a beat of the background music. Use J-cuts (audio bleeds across the visual cut) to keep it flowing.

---

### Beat 3 · The egg-grip moment (0:22 – 0:50) — *28 seconds, slow*

> **This is the headline.** Let it breathe — don't rush. The audience needs to *feel* the tension of "is it going to crush it?"

| Time | Shot | What happens | Text overlay |
|---|---|---|---|
| 0:22 | **S13** — wide reset, person picks up an egg and places it on the table in front of the robotic hand | hold 3 s | `FORCE-AWARE GRIP` (top-left, large, fades after 4 s) |
| 0:25 | **S14** — close-up of robotic hand, fingers fully open, hovering above the egg | hold 2 s |   |
| 0:27 | **S15** — wearer's hand starts to slowly form a pinch | 1 s |   |
| 0:28 | **S16** — robotic hand close-up, fingers begin closing **slowly** toward the egg | 3 s — *slow it down in editing if needed* |   |
| 0:31 | **S17** — dashboard ECU: split-screen — "pinch" bar climbing AND thumb force gauge starting to fill | 3 s | `FSR FEEDBACK` (small caption) |
| 0:34 | **S18** — extreme close-up (macro if possible) of the moment fingers touch the egg shell | 2 s |   |
| 0:36 | **S19** — dashboard ECU: thumb force gauge **crossing the red threshold tick** — bar flips red | hold 2 s | `THRESHOLD REACHED → MOTION HALTED` |
| 0:38 | **S20** — robotic hand close-up — fingers visibly **stop** without crushing | hold 2 s |   |
| 0:40 | **S21** — wide, robotic hand lifts the egg, slowly, walks it across the table | 6 s — long shot, slow camera follow |   |
| 0:46 | **S22** — robotic hand places the egg gently down, fingers release | 3 s |   |
| 0:49 | **S23** — close-up of the **intact** egg sitting on the surface, hand pulls back | 1 s | `INTACT  ·  10 / 10 trials` (lower-third, large) |

> **What to do if the egg breaks on a take:** keep filming. Sometimes a broken egg take is more interesting (shows what would happen *without* the feedback). But you want the clean take as the hero. Plan for ≥ 5 takes.

> **Camera angle for S16/S18/S20:** shoot from a **low angle** looking up at the hand — makes it look more physical and intentional. Eye-level shots make it look like a toy.

---

### Beat 4 · Cost callout & close (0:50 – 0:60) — *10 seconds*

> Goal: the single number that makes a non-engineer remember you.

| Time | Shot | What happens | Text overlay |
|---|---|---|---|
| 0:50 | **S24** — fade to black for 0.5 s, then large white text on black: `£30,000` | hold 1.5 s | `£30,000  ·  Commercial myoelectric hand` (subtitle below, smaller) |
| 0:52 | text cross-dissolves to: `£150` | hold 2 s | `£150  ·  This build` (in accent colour) |
| 0:54 | **S25** — quick recap montage: 3 × 1-second clips: dashboard / egg pickup / wearable | montage |   |
| 0:57 | **S26** — final freeze frame: robotic hand at rest, egg intact in front of it, dashboard visible in the background | hold 3 s | `ACCESSIBLE PROSTHETICS  ·  BUILT TODAY` (centred, large) + name / institution in small text bottom |
| 1:00 | END · fade to black |   |   |

---

## Master shot list — quick reference for shoot day

Print this and tape it to your monitor while filming.

| # | Time | Camera | Subject | Light | Re-takes needed |
|---|---|---|---|---|---|
| S1  | 0:00 | wide, eye-level, slow pan | person + wearable + hand | 3-point | 1 |
| S2  | 0:02 | medium close, ⅓ down from elbow | wearable + electrodes | side fill | 1 |
| S3  | 0:04 | dashboard screen, slight angle | full UI · waveforms scrolling | screen own | 1 |
| S4  | 0:06 | back to wide | person flexes for first time | 3-point | 1 |
| S5  | 0:08 | wide | fist gesture | | 1 |
| S6  | 0:09 | dashboard close | "fist" bar at peak | | 1 |
| S7–S12 | 0:11–0:22 | alternating wide / dashboard close / hand close | open, pinch, point + sync montage | | 1–2 each |
| S13 | 0:22 | wide reset | placing egg | | 1 |
| S14 | 0:25 | hand close, low angle | fingers open above egg | rim-light if possible | 2 |
| S15 | 0:27 | wearer hand | starting pinch | | 1 |
| S16 | 0:28 | hand close, low angle, **slow-motion later** | fingers closing | strong key light | 2–3 |
| S17 | 0:31 | dashboard split | pinch bar + thumb gauge | | 1 |
| S18 | 0:34 | macro (close as your lens allows) | fingertip ↔ shell | hard direct light | **3+** |
| S19 | 0:36 | dashboard ECU | gauge crossing red tick | | 1 |
| S20 | 0:38 | hand close, low angle | fingers holding still | | 2 |
| S21 | 0:40 | wide tracking | hand carrying egg | | **3+** |
| S22 | 0:46 | medium close | placing egg gently | | 2 |
| S23 | 0:49 | egg-only close | intact egg sitting | side fill | 1 |
| S24–S26 | 0:50–0:60 | (graphics + recap) | text overlays | — | edit only |

**Total shot count: 26 named shots. Plan for ~3 hours of shooting** if everything goes smoothly. **Budget 5 hours** including resets, snack break, and the inevitable wiring fix mid-shoot.

---

## Editing notes

**Software** — pick one:
- **CapCut** (free, mobile + desktop) — fast for first-time editors. Built-in text overlays. Great for cuts on beat. Recommended.
- **DaVinci Resolve** (free, desktop) — pro-grade. Better for precise colour correction + smooth motion. Use if you have colour-grading experience.
- **iMovie** (Mac, free) — fine, but limited multi-track. Last resort.

**Music** — instrumental, ~80 BPM, builds gently. Try:
- "Inspiring Cinematic Ambient" or "Tech Documentary" categories on:
  - Pixabay Music · https://pixabay.com/music/ (CC0, no attribution required)
  - YouTube Audio Library · https://studio.youtube.com/ → Audio Library
  - Uppbeat · https://uppbeat.io/ (free tier, attribution required)
- Avoid anything copyrighted. Avoid songs with lyrics — the presenter is talking.

**Colour grading** — keep it simple:
- Bump contrast +10
- Slight cyan tint in shadows (matches the dashboard's dark navy)
- Don't oversaturate — medical/technical projects look more credible with restrained colour.

**Text overlays** — match the slide deck:
- Font: **Calibri Bold** (or Inter / Helvetica Neue Bold if available)
- Colour: white text on shots; navy `#1E3A5F` text when on white bg; accent `#C0392B` for the £ numbers
- Position: lower-third for captions, top-left for section labels
- All overlays fade in over 0.3 s, hold, fade out over 0.4 s

**Cuts** — *no slow zooms on still shots*. Cut crisp, on a music beat. The only slow movement in this video is the hand closing on the egg in Beat 3 — that's the only place pacing should drop.

---

## Pitfalls & rehearsal tips

**The day before shooting:**
- Run the full pipeline end-to-end for 30 minutes. If `predict_realtime.py` crashes once, it'll crash on shoot day. Fix it now.
- Do **one full take** of the egg-grip with your phone, just to find out where the camera should go. Watch it back.
- Test the dashboard on the monitor you'll use on shoot day — refresh issues, font scaling, screen-tearing all show up at this point.

**On shoot day:**
- **Charge everything overnight.** Wearable battery, phone, monitor, laptop.
- **Bring more electrodes than you think.** Gel pads dry out in minutes if you leave them out.
- **Shoot S16 / S18 / S20 / S21 multiple times.** These are the heroes — the more takes, the better the edit.
- **Don't trust the first egg take.** Always do at least 3 takes of the full pickup sequence.

**Common mistakes to avoid:**
- ❌ Shooting handheld (camera shake destroys macro shots). **Always use a tripod or stable surface.**
- ❌ Filming against a window (backlit = silhouettes). Plain wall or paper backdrop.
- ❌ Voiceover layered with presenter narration. **Silent + text + music only.**
- ❌ Music with vocals. Distracts from the live narration.
- ❌ More than 26 cuts. Restraint reads as confidence; over-editing reads as nervousness.
- ❌ Letting the egg take longer than 28 s. If you can't cut it down, your egg sequence is overshot.
- ❌ Forgetting to back up the raw footage to a second drive **before** opening the edit.

---

## If things go wrong on shoot day

| Problem | Fix |
|---|---|
| Egg breaks every take | Lower `FORCE_THRESHOLD` in `predict_realtime.py` by 200; recalibrate; retry. Or use a hard-boiled egg with a *very* clean shell — looks identical on camera and won't crack. |
| Robotic hand twitchy | Servo PSU and Pi GND not tied. Classic. Fix now. |
| Dashboard not updating | UDP packet size mismatch. Re-flash firmware. `i2cdetect -y 1` to confirm PCA9685 still on bus. |
| Camera battery dies | Always have spares charged + ready. |
| Lighting changes mid-shoot | Pause, fix the light, *don't* try to colour-grade your way out of inconsistent shots later. |
| Person fatigued / sweaty (EMG drift) | Take a break. Re-prep electrodes with fresh gel. Trust the model less; rely more on the gesture-confidence overlay to confirm hits. |

---

## Sign-off checklist (before exporting the final MP4)

- [ ] Total length is 55–62 seconds (anything outside this gets awkward in the 5-min slot)
- [ ] No copyrighted music
- [ ] Team / institution credit visible in the final freeze frame
- [ ] All text overlays readable at 720p (assume the projector is bad)
- [ ] Exported as H.264 `.mp4`, 1080p, ~10 Mb/s
- [ ] Watched it back **twice** with audio + once muted (will the presenter's narration fit?)
- [ ] Backed up to USB + cloud + a second machine. Murphy *will* show up.
- [ ] Embedded into slide 6 of `EMG_Hand_Presentation.pptx`, autoplay disabled (presenter controls playback)

When all 8 are ticked: you've shipped.
