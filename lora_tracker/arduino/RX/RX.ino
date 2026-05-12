/*
  RX.ino – LoRa GPS Receiver
  Hardware : Arduino Uno + SX1278 433 MHz LoRa + SSD1306 OLED (I2C 128×64)
  Role     : Receive LoRa packets, display on OLED, stamp RSSI, forward over USB-Serial

  Fixes applied:
    • last_display_attempt initialised to millis() inside setup() when
      display.begin() fails, so the first retry is deferred by the full
      30 seconds instead of firing immediately on the first loop() tick.
    • RSSI value appended to forwarded packet replaces the TX-side placeholder.
*/

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ── Pin definitions ────────────────────────────────────────────────────────
static const int LORA_SS  = 10;
static const int LORA_RST = 9;
static const int LORA_DI0 = 2;

static const long LORA_FREQ = 433E6;

// ── OLED ───────────────────────────────────────────────────────────────────
#define SCREEN_W 128
#define SCREEN_H  64
#define OLED_ADDR 0x3C
#define OLED_RETRY_MS 30000UL   // 30 s between OLED re-init attempts

Adafruit_SSD1306 display(SCREEN_W, SCREEN_H, &Wire, -1);

// ── State ──────────────────────────────────────────────────────────────────
static bool     displayOK           = false;
static unsigned long last_display_attempt = 0;  // set in setup() on failure

// ── Helpers ────────────────────────────────────────────────────────────────

static bool initDisplay() {
    return display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
}

static void showOnDisplay(const String& top, const String& bottom, int rssi) {
    if (!displayOK) return;
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);  display.println(top);
    display.setCursor(0, 16); display.println(bottom);
    display.setCursor(0, 32); display.print("RSSI: "); display.println(rssi);
    display.display();
}

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(9600);

    LoRa.setPins(LORA_SS, LORA_RST, LORA_DI0);
    if (!LoRa.begin(LORA_FREQ)) {
        Serial.println("LoRa init failed");
        while (true);
    }

    // Attempt OLED init; if it fails, set retry timer to NOW so the first
    // retry happens after OLED_RETRY_MS, not immediately on the first loop().
    displayOK = initDisplay();
    if (displayOK) {
        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(0, 0);
        display.println("RX Ready");
        display.display();
    } else {
        Serial.println("OLED not found – will retry in 30 s");
        last_display_attempt = millis();   // ← FIX: defer first retry
    }

    Serial.println("RX ready");
}

// ── Main loop ──────────────────────────────────────────────────────────────
void loop() {
    // ── OLED graceful-degradation retry ──────────────────────────────────
    if (!displayOK) {
        if (millis() - last_display_attempt >= OLED_RETRY_MS) {
            last_display_attempt = millis();
            displayOK = initDisplay();
            if (displayOK) {
                Serial.println("OLED recovered");
            } else {
                Serial.println("OLED still absent – next retry in 30 s");
            }
        }
    }

    // ── Receive packet ────────────────────────────────────────────────────
    int packetSize = LoRa.parsePacket();
    if (packetSize == 0) return;

    String incoming = "";
    while (LoRa.available())
        incoming += (char)LoRa.read();

    int rssi = LoRa.packetRssi();

    // Replace the TX-side placeholder RSSI:0 with actual RSSI
    int rssiIdx = incoming.lastIndexOf("RSSI:");
    if (rssiIdx >= 0) {
        incoming = incoming.substring(0, rssiIdx) + "RSSI:" + String(rssi);
    } else {
        // Append if no placeholder present (legacy TX firmware)
        incoming += ",RSSI:" + String(rssi);
    }

    // Forward to PC via USB-Serial for server.py to consume
    Serial.println(incoming);

    // Display summary on OLED
    // Try to extract lat/lng from CSV (fields 1 & 2 for seq packets, 0 & 1 legacy)
    String latStr = "", lngStr = "";
    int c1 = incoming.indexOf(',');
    if (c1 >= 0) {
        // Check if first field is a number (seq) or coordinate
        String field0 = incoming.substring(0, c1);
        bool isSeq = true;
        for (char c : field0) {
            if (!isDigit(c)) { isSeq = false; break; }
        }
        if (isSeq) {
            int c2 = incoming.indexOf(',', c1 + 1);
            int c3 = incoming.indexOf(',', c2 + 1);
            latStr = incoming.substring(c1 + 1, c2);
            lngStr = incoming.substring(c2 + 1, c3);
        } else {
            int c2 = incoming.indexOf(',', c1 + 1);
            latStr = incoming.substring(0, c1);
            lngStr = incoming.substring(c1 + 1, c2);
        }
    }
    showOnDisplay(latStr, lngStr, rssi);
}
