// Build the 8-slide starter deck for the EMG Hand final-year demo.
// Run: node build_presentation.js
// Output: EMG_Hand_Presentation.pptx in the same directory.

const pptxgen = require("pptxgenjs");

// ─── Palette ──────────────────────────────────────────────
const C = {
  navy:    "1E3A5F",
  navyDk:  "152A47",
  white:   "FFFFFF",
  cream:   "F5EDD6",
  accent:  "C0392B",
  accentSoft: "F5D6D1",
  text:    "2C3E50",
  muted:   "7F8C8D",
  border:  "BDC3C7",
  teal:    "16A085",
  skin:    "F0C39A",
  ad8232:  "FEF6E3",
  pi:      "C0392B",
  esp32:   "2C3E50",
};
const FONT = "Calibri";

// ─── Setup ────────────────────────────────────────────────
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 × 7.5
pres.title = "Low-Cost Myoelectric Hand Control";
pres.author = "UCL BME Team";

const SW = 13.3, SH = 7.5;

// ─── Helpers ──────────────────────────────────────────────
function accentBar(s) {
  s.addShape("rect", {
    x: 0, y: 0, w: 0.14, h: SH,
    fill: { color: C.accent }, line: { width: 0 },
  });
}
function pageNum(s, n, total) {
  s.addText(`${n} / ${total}`, {
    x: 12.4, y: 7.1, w: 0.8, h: 0.3,
    fontSize: 10, fontFace: FONT, color: C.muted,
    align: "right", margin: 0,
  });
  s.addText("EMG Robotic Hand · UCL BME", {
    x: 0.4, y: 7.1, w: 8, h: 0.3,
    fontSize: 10, fontFace: FONT, color: C.muted,
    align: "left", margin: 0,
  });
}
function sectionLabel(s, txt) {
  s.addText(txt, {
    x: 0.5, y: 0.4, w: 12.3, h: 0.3,
    fontSize: 10, fontFace: FONT, color: C.accent, bold: true,
    charSpacing: 6, align: "left", margin: 0,
  });
}
function slideTitle(s, line1, line2 = null, accentLine = null) {
  s.addText(line1, {
    x: 0.5, y: 0.85, w: 12.3, h: 0.7,
    fontSize: 36, fontFace: FONT, color: C.text, bold: true,
    align: "left", margin: 0,
  });
  if (line2) {
    s.addText(line2, {
      x: 0.5, y: 1.5, w: 12.3, h: 0.65,
      fontSize: 36, fontFace: FONT, color: accentLine ? C.accent : C.text, bold: true,
      align: "left", margin: 0,
    });
  }
}

const total = 8;

// ═════════════════════════════════════════════════════════
// SLIDE 1 · TITLE
// ═════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // Top label
  s.addText("FINAL-YEAR DEMONSTRATION", {
    x: 0.8, y: 0.6, w: 11.5, h: 0.3,
    fontSize: 11, fontFace: FONT, color: C.accent, bold: true,
    charSpacing: 6, align: "left", margin: 0,
  });

  // Main title — two lines
  s.addText("Low-Cost", {
    x: 0.8, y: 2.0, w: 11.5, h: 0.95,
    fontSize: 56, fontFace: FONT, color: C.white, bold: false,
    align: "left", margin: 0,
  });
  s.addText("Myoelectric Hand Control", {
    x: 0.8, y: 2.95, w: 11.5, h: 1.0,
    fontSize: 56, fontFace: FONT, color: C.white, bold: true,
    align: "left", margin: 0,
  });

  // Accent rule
  s.addShape("rect", {
    x: 0.8, y: 4.1, w: 1.6, h: 0.07,
    fill: { color: C.accent }, line: { width: 0 },
  });

  // Subtitle
  s.addText("An accessible EMG-controlled prosthetic alternative", {
    x: 0.8, y: 4.3, w: 11.5, h: 0.5,
    fontSize: 20, fontFace: FONT, color: "CFD6DF", italic: true,
    align: "left", margin: 0,
  });

  // Team line
  s.addText([
    { text: "Team   ", options: { color: C.muted, bold: false } },
    { text: "[Member 1]    [Member 2]    [Member 3]    [Member 4]", options: { color: C.white } },
  ], {
    x: 0.8, y: 5.7, w: 11.5, h: 0.4,
    fontSize: 14, fontFace: FONT, align: "left", margin: 0,
  });

  s.addText("UCL Biomedical Engineering   ·   2026", {
    x: 0.8, y: 6.15, w: 11.5, h: 0.4,
    fontSize: 13, fontFace: FONT, color: C.muted,
    align: "left", margin: 0,
  });
}

// ═════════════════════════════════════════════════════════
// SLIDE 2 · THE PROBLEM
// ═════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionLabel(s, "01 · THE PROBLEM");
  slideTitle(s, "Commercial Myoelectric Prosthetics", "Are Out of Reach", true);

  // Left bullets
  s.addText([
    { text: "2M+ upper-limb amputees worldwide", options: { bullet: true, breakLine: true } },
    { text: "Commercial myoelectric hands: £30,000–£60,000", options: { bullet: true, breakLine: true } },
    { text: "80% of amputees in low-income regions go without", options: { bullet: true, breakLine: true } },
    { text: "Long NHS assessment & funding waiting lists", options: { bullet: true } },
  ], {
    x: 0.7, y: 2.9, w: 7.0, h: 3.5,
    fontSize: 18, fontFace: FONT, color: C.text,
    paraSpaceAfter: 14,
  });

  // Right stat card
  s.addShape("rect", {
    x: 8.4, y: 2.9, w: 4.4, h: 3.5,
    fill: { color: C.cream }, line: { width: 0 },
  });
  s.addShape("rect", {
    x: 8.4, y: 2.9, w: 4.4, h: 0.12,
    fill: { color: C.accent }, line: { width: 0 },
  });
  s.addText("£30,000+", {
    x: 8.4, y: 3.4, w: 4.4, h: 1.4,
    fontSize: 64, fontFace: FONT, color: C.accent, bold: true,
    align: "center", valign: "middle", margin: 0,
  });
  s.addText([
    { text: "starting cost of a commercial", options: { breakLine: true } },
    { text: "myoelectric prosthetic hand" },
  ], {
    x: 8.4, y: 4.95, w: 4.4, h: 0.8,
    fontSize: 14, fontFace: FONT, color: C.muted,
    align: "center", margin: 0,
  });
  s.addText("Sources to add — Open Bionics, NHS prosthetics", {
    x: 8.4, y: 5.95, w: 4.4, h: 0.3,
    fontSize: 9, fontFace: FONT, color: C.muted, italic: true,
    align: "center", margin: 0,
  });

  pageNum(s, 2, total);
}

// ═════════════════════════════════════════════════════════
// SLIDE 3 · OUR SOLUTION (system flow)
// ═════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionLabel(s, "02 · OUR SOLUTION");

  s.addText([
    { text: "5-Gesture EMG Hand for ", options: { color: C.text } },
    { text: "~£150", options: { color: C.accent } },
  ], {
    x: 0.5, y: 0.85, w: 12.3, h: 0.7,
    fontSize: 36, fontFace: FONT, bold: true,
    align: "left", margin: 0,
  });
  s.addText("End-to-end signal chain: skin to servo", {
    x: 0.5, y: 1.5, w: 12.3, h: 0.45,
    fontSize: 16, fontFace: FONT, color: C.muted, italic: true,
    align: "left", margin: 0,
  });

  // System flow boxes
  const boxes = [
    { label: "Forearm\nelectrodes",     bg: C.skin,   tx: C.text },
    { label: "AD8232\namplifier × 2",   bg: C.ad8232, tx: C.text },
    { label: "ESP32\nWiFi UDP",         bg: C.esp32,  tx: C.white },
    { label: "Raspberry Pi 5\nCNN inference", bg: C.pi, tx: C.white },
    { label: "PCA9685\nservo driver",   bg: C.teal,   tx: C.white },
    { label: "5-finger\nservo hand",    bg: C.skin,   tx: C.text },
  ];

  const boxW = 1.75, boxH = 1.4;
  const arrowW = 0.35;
  const totalW = boxes.length * boxW + (boxes.length - 1) * arrowW;
  const startX = (SW - totalW) / 2;
  const flowY = 2.7;

  boxes.forEach((b, i) => {
    const x = startX + i * (boxW + arrowW);
    s.addShape("rect", {
      x, y: flowY, w: boxW, h: boxH,
      fill: { color: b.bg }, line: { color: C.border, width: 0.5 },
    });
    s.addText(b.label, {
      x, y: flowY, w: boxW, h: boxH,
      fontSize: 13, fontFace: FONT, bold: true, color: b.tx,
      align: "center", valign: "middle", margin: 0,
    });

    if (i < boxes.length - 1) {
      // Arrow drawn as text "▶"
      const ax = x + boxW;
      s.addText("▶", {
        x: ax, y: flowY, w: arrowW, h: boxH,
        fontSize: 18, fontFace: FONT, color: C.muted,
        align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // Pills below
  const pills = ["Real-time (20 Hz)", "Wireless wearable", "5 distinct grasps"];
  const pillW = 3.0, pillGap = 0.4, pillH = 0.65;
  const pillTotal = pills.length * pillW + (pills.length - 1) * pillGap;
  const pillStartX = (SW - pillTotal) / 2;
  const pillY = 5.0;
  pills.forEach((p, i) => {
    const x = pillStartX + i * (pillW + pillGap);
    s.addShape("roundRect", {
      x, y: pillY, w: pillW, h: pillH,
      fill: { color: C.cream }, line: { color: C.border, width: 0.5 },
      rectRadius: 0.32,
    });
    s.addText(p, {
      x, y: pillY, w: pillW, h: pillH,
      fontSize: 14, fontFace: FONT, color: C.text, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
  });

  // Bottom hint
  s.addText("Same hardware reused as a live ECG / vital-signs dashboard — see Results slide.", {
    x: 0.5, y: 6.2, w: 12.3, h: 0.4,
    fontSize: 12, fontFace: FONT, color: C.muted, italic: true,
    align: "center", margin: 0,
  });

  pageNum(s, 3, total);
}

// ═════════════════════════════════════════════════════════
// SLIDE 4 · HARDWARE
// ═════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionLabel(s, "03 · HARDWARE");
  slideTitle(s, "Wearable + Edge Compute");

  // Left: components table
  const tableData = [
    [
      { text: "Component", options: { bold: true, color: C.muted, fontSize: 11 } },
      { text: "Qty", options: { bold: true, color: C.muted, fontSize: 11, align: "center" } },
      { text: "~£", options: { bold: true, color: C.muted, fontSize: 11, align: "right" } },
    ],
    ["ESP32 DevKit V1",                  { text: "1", options: { align: "center" } }, { text: "10",  options: { align: "right" } }],
    ["MyoWare 2.0 sensor + Cable Shield", { text: "1", options: { align: "center" } }, { text: "50",  options: { align: "right" } }],
    ["Raspberry Pi 5 (8 GB)",            { text: "1", options: { align: "center" } }, { text: "70",  options: { align: "right" } }],
    ["PCA9685 PWM driver",               { text: "1", options: { align: "center" } }, { text: "10",  options: { align: "right" } }],
    ["Micro servos (MG90S)",             { text: "5", options: { align: "center" } }, { text: "20",  options: { align: "right" } }],
    ["5 V PSU (≥ 3 A)",                  { text: "1", options: { align: "center" } }, { text: "12",  options: { align: "right" } }],
    ["3× FSR + electrodes + accessories", { text: "—", options: { align: "center" } }, { text: "30",  options: { align: "right" } }],
    [
      { text: "Total", options: { bold: true, fill: { color: C.cream }, color: C.text } },
      { text: "",      options: { fill: { color: C.cream } } },
      { text: "≈ £202", options: { bold: true, color: C.accent, fill: { color: C.cream }, align: "right" } },
    ],
  ];

  s.addTable(tableData, {
    x: 0.7, y: 2.8, w: 6.6, colW: [3.6, 1.0, 2.0],
    fontSize: 13, fontFace: FONT, color: C.text,
    rowH: 0.42, valign: "middle",
    border: { type: "solid", pt: 0.5, color: C.border },
  });

  // Right: photo placeholder
  s.addShape("rect", {
    x: 8.0, y: 2.8, w: 4.7, h: 3.9,
    fill: { color: C.cream }, line: { color: C.border, width: 1 },
  });
  s.addText("Photo of wearable + hand", {
    x: 8.0, y: 4.4, w: 4.7, h: 0.45,
    fontSize: 16, fontFace: FONT, color: C.muted, bold: true,
    align: "center", margin: 0,
  });
  s.addText("[ insert image here ]", {
    x: 8.0, y: 4.85, w: 4.7, h: 0.35,
    fontSize: 12, fontFace: FONT, color: C.muted, italic: true,
    align: "center", margin: 0,
  });

  pageNum(s, 4, total);
}

// ═════════════════════════════════════════════════════════
// SLIDE 5 · SOFTWARE PIPELINE
// ═════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionLabel(s, "04 · SOFTWARE PIPELINE");
  slideTitle(s, "Signal → Gesture → Action");

  // Pipeline boxes (5)
  const stages = [
    { top: "Raw EMG",         sub: "1 kHz · 1 ch · MyoWare 2.0 SIG" },
    { top: "RMS threshold",   sub: "envelope · 5 s auto-calibration · debounced" },
    { top: "Decision",        sub: "flex → close · relax → open" },
    { top: "Force feedback",  sub: "3× FSR-402 halts closing per finger" },
    { top: "Servo angles",    sub: "5 channels → finger positions" },
  ];

  const sW = 2.3, sH = 1.6;
  const sArr = 0.25;
  const sTotal = stages.length * sW + (stages.length - 1) * sArr;
  const sStart = (SW - sTotal) / 2;
  const sY = 3.0;

  stages.forEach((st, i) => {
    const x = sStart + i * (sW + sArr);
    s.addShape("rect", {
      x, y: sY, w: sW, h: sH,
      fill: { color: C.white }, line: { color: C.navy, width: 1.4 },
    });
    s.addShape("rect", {
      x, y: sY, w: sW, h: 0.08,
      fill: { color: C.accent }, line: { width: 0 },
    });
    s.addText(st.top, {
      x, y: sY + 0.15, w: sW, h: 0.5,
      fontSize: 16, fontFace: FONT, color: C.text, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(st.sub, {
      x: x + 0.1, y: sY + 0.7, w: sW - 0.2, h: 0.85,
      fontSize: 10.5, fontFace: FONT, color: C.muted,
      align: "center", valign: "top", margin: 0,
    });

    if (i < stages.length - 1) {
      const ax = x + sW;
      s.addText("▶", {
        x: ax, y: sY, w: sArr, h: sH,
        fontSize: 14, fontFace: FONT, color: C.muted,
        align: "center", valign: "middle", margin: 0,
      });
    }
  });

  // Latency callout
  s.addShape("rect", {
    x: 0.7, y: 5.4, w: 12.0, h: 0.85,
    fill: { color: C.cream }, line: { width: 0 },
  });
  s.addText([
    { text: "< 50 ms ", options: { fontSize: 22, color: C.accent, bold: true } },
    { text: "end-to-end latency on Pi 5 CPU   ", options: { fontSize: 14, color: C.text } },
    { text: "·   sample → prediction → servo command", options: { fontSize: 13, color: C.muted, italic: true } },
  ], {
    x: 0.7, y: 5.4, w: 12.0, h: 0.85,
    fontFace: FONT, align: "center", valign: "middle", margin: 0,
  });

  pageNum(s, 5, total);
}

// ═════════════════════════════════════════════════════════
// SLIDE 6 · DEMO VIDEO
// ═════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionLabel(s, "05 · DEMO");
  slideTitle(s, "Live Demonstration");

  // Video placeholder — big central rectangle
  const vidX = 1.3, vidY = 2.6, vidW = 10.7, vidH = 4.0;
  s.addShape("rect", {
    x: vidX, y: vidY, w: vidW, h: vidH,
    fill: { color: C.navyDk }, line: { color: C.navy, width: 1.5 },
  });
  // Play-triangle icon (use text)
  s.addText("▶", {
    x: vidX, y: vidY, w: vidW, h: vidH - 0.5,
    fontSize: 100, fontFace: FONT, color: C.accent,
    align: "center", valign: "middle", margin: 0,
  });
  s.addText("Embedded demo video — 45–60 s", {
    x: vidX, y: vidY + vidH - 0.6, w: vidW, h: 0.4,
    fontSize: 14, fontFace: FONT, color: "CFD6DF",
    align: "center", margin: 0,
  });

  s.addText("Real-time gesture classification driving the servo hand", {
    x: 0.5, y: 6.75, w: 12.3, h: 0.35,
    fontSize: 13, fontFace: FONT, color: C.muted, italic: true,
    align: "center", margin: 0,
  });

  pageNum(s, 6, total);
}

// ═════════════════════════════════════════════════════════
// SLIDE 7 · RESULTS
// ═════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionLabel(s, "06 · RESULTS");
  slideTitle(s, "Performance");

  // ── Left: 5×5 confusion matrix grid placeholder ──
  const cmX = 0.7, cmY = 2.65;
  const cellW = 0.7, cellH = 0.55;
  const labels = ["rest", "fist", "open", "pinch", "point"];

  // Column labels (top)
  labels.forEach((l, j) => {
    s.addText(l, {
      x: cmX + 1.1 + j * cellW, y: cmY - 0.45, w: cellW, h: 0.35,
      fontSize: 10, fontFace: FONT, color: C.muted, bold: true,
      align: "center", margin: 0,
    });
  });
  s.addText("predicted →", {
    x: cmX + 1.0, y: cmY - 0.75, w: 5 * cellW, h: 0.25,
    fontSize: 9, fontFace: FONT, color: C.muted, italic: true,
    align: "center", margin: 0,
  });
  // Row labels (left)
  labels.forEach((l, i) => {
    s.addText(l, {
      x: cmX, y: cmY + i * cellH, w: 1.0, h: cellH,
      fontSize: 10, fontFace: FONT, color: C.muted, bold: true,
      align: "right", valign: "middle", margin: 0,
    });
  });
  s.addText("← true", {
    x: cmX - 0.6, y: cmY + cellH * 2, w: 0.6, h: cellH,
    fontSize: 9, fontFace: FONT, color: C.muted, italic: true,
    align: "center", valign: "middle", margin: 0,
  });

  // Cells — placeholder values (diagonal = high, off-diagonal = low)
  const placeholder = [
    [0.99, 0.00, 0.01, 0.00, 0.00],
    [0.01, 0.95, 0.01, 0.03, 0.00],
    [0.02, 0.02, 0.93, 0.01, 0.02],
    [0.00, 0.05, 0.00, 0.78, 0.17],
    [0.00, 0.00, 0.03, 0.22, 0.75],
  ];
  for (let i = 0; i < 5; i++) {
    for (let j = 0; j < 5; j++) {
      const v = placeholder[i][j];
      // colour intensity ramps from cream → accent for higher values
      const r = Math.round(0xF5 - v * (0xF5 - 0xC0));
      const g = Math.round(0xED - v * (0xED - 0x39));
      const b = Math.round(0xD6 - v * (0xD6 - 0x2B));
      const hex = [r, g, b].map(x => x.toString(16).padStart(2, "0")).join("");
      s.addShape("rect", {
        x: cmX + 1.1 + j * cellW, y: cmY + i * cellH, w: cellW, h: cellH,
        fill: { color: hex }, line: { color: C.border, width: 0.3 },
      });
      s.addText((v * 100).toFixed(0), {
        x: cmX + 1.1 + j * cellW, y: cmY + i * cellH, w: cellW, h: cellH,
        fontSize: 11, fontFace: FONT, bold: i === j, color: v > 0.5 ? C.white : C.text,
        align: "center", valign: "middle", margin: 0,
      });
    }
  }
  s.addText("Confusion matrix (placeholder — replace with your actual numbers)", {
    x: cmX, y: cmY + 5 * cellH + 0.15, w: 5.5, h: 0.3,
    fontSize: 10, fontFace: FONT, color: C.muted, italic: true,
    align: "left", margin: 0,
  });

  // ── Right: 3 KPI blocks (compact, fit above the baseline note) ──
  const kpis = [
    { label: "Per-subject\naccuracy",   val: "92%",   col: C.teal },
    { label: "Cross-subject\naccuracy", val: "80%",   col: C.accent },
    { label: "End-to-end\nlatency",     val: "47 ms", col: C.navy },
  ];
  const kX = 7.6;
  const kpiH = 1.1, kpiGap = 0.15;
  kpis.forEach((k, i) => {
    const y = 2.65 + i * (kpiH + kpiGap);
    s.addShape("rect", {
      x: kX, y, w: 5.1, h: kpiH,
      fill: { color: C.white }, line: { color: C.border, width: 1 },
    });
    s.addShape("rect", {
      x: kX, y, w: 0.12, h: kpiH,
      fill: { color: k.col }, line: { width: 0 },
    });
    s.addText(k.val, {
      x: kX + 0.25, y, w: 2.2, h: kpiH,
      fontSize: 32, fontFace: FONT, color: k.col, bold: true,
      align: "left", valign: "middle", margin: 0,
    });
    s.addText(k.label, {
      x: kX + 2.6, y, w: 2.4, h: kpiH,
      fontSize: 13, fontFace: FONT, color: C.text,
      align: "left", valign: "middle", margin: 0,
    });
  });

  // Bottom note (centred under both columns, clear of KPIs)
  s.addShape("rect", {
    x: 0.7, y: 6.55, w: 12.0, h: 0.5,
    fill: { color: C.cream }, line: { width: 0 },
  });
  s.addText([
    { text: "Baseline:  ", options: { bold: true, color: C.accent } },
    { text: "1D CNN vs SVM on classical features (MAV, RMS, ZC, WL) — CNN +8% accuracy on the same test set.", options: { color: C.text } },
  ], {
    x: 0.7, y: 6.55, w: 12.0, h: 0.5,
    fontSize: 12, fontFace: FONT, italic: true,
    align: "center", valign: "middle", margin: 0,
  });

  pageNum(s, 7, total);
}

// ═════════════════════════════════════════════════════════
// SLIDE 8 · IMPACT + FUTURE
// ═════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // Section label
  s.addText("07 · IMPACT", {
    x: 0.7, y: 0.6, w: 11.5, h: 0.3,
    fontSize: 11, fontFace: FONT, color: C.accent, bold: true,
    charSpacing: 6, align: "left", margin: 0,
  });

  // The big number comparison
  s.addText([
    { text: "£200", options: { color: C.accent, bold: true, fontSize: 88 } },
    { text: "   vs   ", options: { color: C.muted, fontSize: 32 } },
    { text: "£30,000", options: { color: C.white, fontSize: 64, bold: true } },
  ], {
    x: 0.7, y: 1.4, w: 12.0, h: 1.7,
    fontFace: FONT, align: "center", valign: "middle", margin: 0,
  });

  s.addText("150× cost reduction · open-source · replicable by BME students, makers, low-income clinics", {
    x: 0.7, y: 3.25, w: 12.0, h: 0.5,
    fontSize: 16, fontFace: FONT, color: "CFD6DF", italic: true,
    align: "center", margin: 0,
  });

  // Accent rule
  s.addShape("rect", {
    x: 6.15, y: 3.95, w: 1.0, h: 0.06,
    fill: { color: C.accent }, line: { width: 0 },
  });

  // "Future work" header
  s.addText("FUTURE WORK", {
    x: 0.7, y: 4.2, w: 12.0, h: 0.3,
    fontSize: 11, fontFace: FONT, color: C.muted, bold: true,
    charSpacing: 4, align: "center", margin: 0,
  });

  // Three future-work columns
  const fw = [
    { title: "Multi-channel EMG",         sub: "Distinct gestures beyond open/close\n(currently 1 channel)" },
    { title: "5 fingertip force sensors", sub: "Per-finger closed-loop control\n(currently 3 FSRs)" },
    { title: "Cross-subject pretraining", sub: "Generalise to new users\n(Ninapro DB2 transfer)" },
  ];
  const fwW = 3.7, fwH = 1.5, fwGap = 0.3;
  const fwTotal = fw.length * fwW + (fw.length - 1) * fwGap;
  const fwStart = (SW - fwTotal) / 2;
  const fwY = 4.7;

  fw.forEach((f, i) => {
    const x = fwStart + i * (fwW + fwGap);
    s.addShape("rect", {
      x, y: fwY, w: fwW, h: fwH,
      fill: { color: C.navyDk }, line: { color: C.muted, width: 0.5 },
    });
    s.addShape("rect", {
      x, y: fwY, w: 0.08, h: fwH,
      fill: { color: C.accent }, line: { width: 0 },
    });
    s.addText(f.title, {
      x: x + 0.25, y: fwY + 0.15, w: fwW - 0.35, h: 0.45,
      fontSize: 15, fontFace: FONT, color: C.white, bold: true,
      align: "left", valign: "top", margin: 0,
    });
    s.addText(f.sub, {
      x: x + 0.25, y: fwY + 0.7, w: fwW - 0.35, h: 0.75,
      fontSize: 11, fontFace: FONT, color: "CFD6DF",
      align: "left", valign: "top", margin: 0,
    });
  });

  // Closing line
  s.addText("Accessible myoelectric prosthetics, built today.", {
    x: 0.7, y: 6.65, w: 12.0, h: 0.45,
    fontSize: 18, fontFace: FONT, color: C.white, italic: true,
    align: "center", margin: 0,
  });
}

// ─── Write ────────────────────────────────────────────────
pres.writeFile({ fileName: "EMG_Hand_Presentation.pptx" })
  .then(name => console.log("Wrote " + name))
  .catch(e => { console.error(e); process.exit(1); });
