/*
  TX.ino – LoRa GPS Transmitter
  Hardware : Arduino Uno + NEO-6M (SoftwareSerial) + SX1278 433 MHz LoRa module
  Protocol : CSV packet  →  seq,lat,lng,alt,speed,heading,msg,RSSI:<val>
             (legacy 4-field format also supported by server)

  Fixes applied:
    • Non-blocking GPS warm-up: continues feeding gps.encode() during the
      2-second stale-data wait instead of calling delay(2000), which was
      starving the GPS buffer and losing NMEA sentences.
    • Sequence number added to every packet (future multi-node id hook).
    • Altitude / speed / heading transmitted (future scope).
*/

#include <SoftwareSerial.h>
#include <TinyGPS++.h>
#include <SPI.h>
#include <LoRa.h>

// ── Pin definitions ────────────────────────────────────────────────────────
static const int GPS_RX   = 4;
static const int GPS_TX   = 3;
static const int LORA_SS  = 10;
static const int LORA_RST = 9;
static const int LORA_DI0 = 2;

// ── LoRa parameters ────────────────────────────────────────────────────────
static const long LORA_FREQ      = 433E6;   // ISM 433 MHz
static const int  LORA_TX_POWER  = 17;      // dBm
static const long TX_INTERVAL_MS = 2000;    // transmit every 2 s

// ── Objects ────────────────────────────────────────────────────────────────
SoftwareSerial gpsSerial(GPS_RX, GPS_TX);
TinyGPSPlus    gps;

// ── State ──────────────────────────────────────────────────────────────────
static uint32_t seq        = 0;
static char     txMsg[32]  = "Hello";       // default message

// ── Helpers ────────────────────────────────────────────────────────────────

/** Feed GPS parser for up to `ms` milliseconds without blocking. */
static void feedGPS(unsigned long ms) {
    unsigned long deadline = millis() + ms;
    while (millis() < deadline) {
        while (gpsSerial.available())
            gps.encode(gpsSerial.read());
    }
}

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(9600);
    gpsSerial.begin(9600);

    LoRa.setPins(LORA_SS, LORA_RST, LORA_DI0);
    if (!LoRa.begin(LORA_FREQ)) {
        Serial.println("LoRa init failed");
        while (true);
    }
    LoRa.setTxPower(LORA_TX_POWER);
    Serial.println("TX ready");
}

// ── Main loop ──────────────────────────────────────────────────────────────
void loop() {
    // Feed GPS parser for one full TX_INTERVAL before checking location
    feedGPS(TX_INTERVAL_MS);

    if (!gps.location.isValid()) {
        Serial.println("Waiting for GPS fix…");
        return;   // keep looping; feedGPS will run again next iteration
    }

    // ── Stale-data check ─────────────────────────────────────────────────
    // If the last fix is > 2 s old keep feeding the parser (non-blocking)
    // instead of calling delay(2000), which starved the buffer.
    if (gps.location.age() > 2000) {
        Serial.println("GPS data stale – waiting for fresh fix");
        feedGPS(2000);   // continues parsing NMEA during the wait
        if (gps.location.age() > 2000) {
            Serial.println("Still stale – skipping transmission");
            return;
        }
    }

    // ── Build packet ─────────────────────────────────────────────────────
    double lat     = gps.location.lat();
    double lng     = gps.location.lng();
    double alt     = gps.altitude.isValid()  ? gps.altitude.meters()  : 0.0;
    double speed   = gps.speed.isValid()     ? gps.speed.kmph()       : 0.0;
    double heading = gps.course.isValid()    ? gps.course.deg()       : 0.0;

    // Warn if the message contains a comma (would corrupt CSV)
    if (strchr(txMsg, ',') != nullptr) {
        Serial.println("WARNING: txMsg contains comma – stripping");
        char* p;
        while ((p = strchr(txMsg, ',')) != nullptr) *p = ';';
    }

    // Format: seq,lat,lng,alt,speed,heading,msg,RSSI:0
    // (receiver will overwrite RSSI:0 with actual RSSI on RX side)
    char packet[128];
    snprintf(packet, sizeof(packet),
             "%lu,%.6f,%.6f,%.1f,%.1f,%.1f,%s,RSSI:0",
             seq, lat, lng, alt, speed, heading, txMsg);

    // ── Transmit ─────────────────────────────────────────────────────────
    LoRa.beginPacket();
    LoRa.print(packet);
    LoRa.endPacket();

    Serial.print("TX ["); Serial.print(seq); Serial.print("]: ");
    Serial.println(packet);

    seq++;
}
