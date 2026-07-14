/*
 * esp32_emg_streamer.ino  ·  EMG Robotic Hand project
 * ---------------------------------------------------------------------------
 * Wearable 2-channel sEMG + 3-channel fingertip-FSR streamer.
 *
 * Samples two AD8232 analog front-ends (forearm flexor + extensor) at 1 kHz,
 * reads three FSR-402 fingertip force pads once per packet, and streams
 * everything to the Raspberry Pi 5 over WiFi as 54-byte binary UDP packets
 * on port 5555.
 *
 * Packet layout — little-endian — MUST stay in sync with
 * pi/emg_common.py parse_packet():
 *
 *   off 0  : 0xE1 0xA1              header                         (2)
 *   off 2  : uint16  seq           packet counter, wraps 0xFFFF   (2)
 *   off 4  : uint32  ts_us         micros() of first sample       (4)
 *   off 8  : 10 x [int16 CH1, int16 CH2]   sEMG @ 1 kHz          (40)
 *   off 48 : 3  x  uint16          FSR thumb, index, middle       (6)
 *                                                       total  =  54 bytes
 *
 * At 1 kHz with 10 samples/packet this is 100 packets/s (one FSR reading
 * per packet, i.e. FSRs are effectively sampled at 100 Hz).
 *
 * Pin map = as-built KiCad board (emg_frontend, rev C). All analog inputs
 * are on ADC1 (GPIO32-39) — ADC2 is unusable while WiFi is active.
 *
 *   EMG1_OUT flexor    -> GPIO34      LO1+ GPIO25   LO1- GPIO27
 *   EMG2_OUT extensor  -> GPIO35      LO2+ GPIO26   LO2- GPIO32
 *   FSR thumb          -> GPIO33
 *   FSR index          -> GPIO36 (VP)
 *   FSR middle         -> GPIO39 (VN)
 *
 * Board: ESP32 Dev Module @ 115200 baud.
 * ---------------------------------------------------------------------------
 */

#include <WiFi.h>
#include <WiFiUdp.h>

// ---- user config ----------------------------------------------------------
const char* WIFI_SSID     = "<your-network>";
const char* WIFI_PASSWORD = "<your-password>";
const char* PI_IP         = "<your-pi-ip>";   // find with `hostname -I` on the Pi
const uint16_t UDP_PORT   = 5555;

// ---- pin map (as-built emg_frontend rev C) --------------------------------
const int PIN_EMG1 = 34;   // flexor  / CH1 / ECG Lead-I in dashboard mode
const int PIN_EMG2 = 35;   // extensor / CH2
const int PIN_LO1P = 25, PIN_LO1N = 27;   // CH1 leads-off detect
const int PIN_LO2P = 26, PIN_LO2N = 32;   // CH2 leads-off detect
const int PIN_FSR_TH = 33, PIN_FSR_IX = 36, PIN_FSR_MD = 39;

// ---- packet / timing constants --------------------------------------------
const int      SAMPLE_RATE_HZ     = 1000;
const int      SAMPLES_PER_PACKET = 10;
const int      NUM_FSRS           = 3;
const int      PACKET_SIZE        = 8 + SAMPLES_PER_PACKET * 4 + NUM_FSRS * 2; // 54
const uint32_t SAMPLE_US          = 1000000UL / SAMPLE_RATE_HZ;               // 1000

// ---- state ----------------------------------------------------------------
WiFiUDP  udp;
uint8_t  packet[PACKET_SIZE];
uint16_t seq          = 0;
uint32_t nextSampleUs = 0;
int      sampleCount  = 0;

// little-endian writers into the packet buffer
static inline void put_u16(int off, uint16_t v) { packet[off] = v & 0xFF; packet[off + 1] = v >> 8; }
static inline void put_i16(int off, int16_t  v) { put_u16(off, (uint16_t)v); }
static inline void put_u32(int off, uint32_t v) {
  packet[off]     =  v        & 0xFF;
  packet[off + 1] = (v >> 8)  & 0xFF;
  packet[off + 2] = (v >> 16) & 0xFF;
  packet[off + 3] = (v >> 24) & 0xFF;
}

void connectWiFi() {
  Serial.printf("Connecting to \"%s\" ", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print('.'); }
  Serial.printf("\nWiFi OK  ip=%s  rssi=%d dBm\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());
}

void setup() {
  Serial.begin(115200);
  delay(300);

  analogReadResolution(12);                       // 0..4095
  const int analogPins[] = {PIN_EMG1, PIN_EMG2, PIN_FSR_TH, PIN_FSR_IX, PIN_FSR_MD};
  for (int p : analogPins) analogSetPinAttenuation(p, ADC_11db);   // full ~0..3.3 V

  pinMode(PIN_LO1P, INPUT); pinMode(PIN_LO1N, INPUT);
  pinMode(PIN_LO2P, INPUT); pinMode(PIN_LO2N, INPUT);

  connectWiFi();
  udp.begin(UDP_PORT);

  packet[0] = 0xE1;  packet[1] = 0xA1;            // header — constant for the run

  Serial.printf("UDP ready -> %s:%u   (%d-byte packets, %d Hz, 2ch sEMG + %d FSR)\n",
                PI_IP, UDP_PORT, PACKET_SIZE, SAMPLE_RATE_HZ, NUM_FSRS);
  nextSampleUs = micros();
}

void loop() {
  // keep the link up — cheap check, runs at sample cadence
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi dropped — reconnecting...");
    connectWiFi();
    nextSampleUs = micros();
    sampleCount  = 0;
  }

  uint32_t now = micros();
  if ((int32_t)(now - nextSampleUs) < 0) return;  // not time for the next sample yet
  nextSampleUs += SAMPLE_US;                       // schedule next tick (catches up if late)

  if (sampleCount == 0) {                          // start of a fresh packet
    put_u16(2, seq);
    put_u32(4, now);                               // ts_us of first sample
  }

  int off = 8 + sampleCount * 4;
  put_i16(off,     (int16_t)analogRead(PIN_EMG1)); // CH1 raw ADC (DC removed by Pi HP filter)
  put_i16(off + 2, (int16_t)analogRead(PIN_EMG2)); // CH2
  sampleCount++;

  if (sampleCount >= SAMPLES_PER_PACKET) {
    // one FSR reading per packet — order matches emg_common.FSR_FINGERS
    put_u16(48, (uint16_t)analogRead(PIN_FSR_TH));
    put_u16(50, (uint16_t)analogRead(PIN_FSR_IX));
    put_u16(52, (uint16_t)analogRead(PIN_FSR_MD));

    udp.beginPacket(PI_IP, UDP_PORT);
    udp.write(packet, PACKET_SIZE);
    udp.endPacket();

    seq++;                                          // wraps naturally at 0xFFFF
    sampleCount = 0;

    if ((seq % 100) == 0) {                         // ~1 Hz serial heartbeat
      bool lo1 = digitalRead(PIN_LO1P) || digitalRead(PIN_LO1N);
      bool lo2 = digitalRead(PIN_LO2P) || digitalRead(PIN_LO2N);
      Serial.printf("seq=%u  rssi=%d dBm  CH1 %s  CH2 %s\n",
                    seq, WiFi.RSSI(),
                    lo1 ? "[leads-off]" : "[ok]",
                    lo2 ? "[leads-off]" : "[ok]");
    }
  }
}
