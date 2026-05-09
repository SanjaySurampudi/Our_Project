/*
 * rx.ino  —  LoRa Receiver with OLED display
 *
 * Fix applied
 * -----------
 * RSSI is now appended to the DATA: serial output so the Python server
 * can parse it.  Format:
 *
 *     DATA:<lat>,<lng>,<message>,RSSI:<value>
 *
 * Example:
 *     DATA:17.385000,78.486700,Hello World,RSSI:-87
 *
 * Libraries required
 * ------------------
 *   LoRa          by Sandeep Mistry
 *   Adafruit GFX
 *   Adafruit SSD1306
 */

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ── OLED configuration ───────────────────────────────────────────────────────
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT  64
#define OLED_RESET     -1          // No hardware reset pin used
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ── LoRa pin definitions (Arduino Uno / Nano) ────────────────────────────────
#define LORA_SS    10             // Chip Select (NSS)
#define LORA_RST    9             // Reset
#define LORA_DIO0   2             // Interrupt (DIO0)

// ── Setup ────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);

  // Initialise LoRa
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(433E6)) {       // 433 MHz — must match transmitter
    Serial.println("LoRa init failed!");
    while (1);
  }

  // Initialise OLED (I2C address 0x3C)
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED failed");
    while (1);
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("Waiting for data...");
  display.display();

  Serial.println("LoRa RX ready");
}

// ── Main loop ────────────────────────────────────────────────────────────────
void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize == 0) return;    // Nothing received yet

  // Read the incoming bytes into a String
  String received = "";
  while (LoRa.available()) {
    received += (char)LoRa.read();
  }

  // Read RSSI *immediately* after receiving the packet (most accurate)
  int rssi = LoRa.packetRssi();

  // ── Serial output ──────────────────────────────────────────────────────
  // Format:  DATA:<lat>,<lng>,<message>,RSSI:<value>
  // The Python server splits on ",RSSI:" to extract the RSSI field.
  Serial.print("DATA:");
  Serial.print(received);         // already contains  lat,lng,message
  Serial.print(",RSSI:");
  Serial.println(rssi);           // e.g.  -87

  // ── Parse fields for OLED display ──────────────────────────────────────
  int firstComma  = received.indexOf(',');
  int secondComma = received.indexOf(',', firstComma + 1);

  String lat = received.substring(0, firstComma);
  String lng = received.substring(firstComma + 1, secondComma);
  String msg = received.substring(secondComma + 1);

  // ── Update OLED ────────────────────────────────────────────────────────
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("GPS Tracker RX");
  display.println("Lat: " + lat);
  display.println("Lng: " + lng);
  display.println("Msg: " + msg);
  display.println("RSSI: " + String(rssi) + " dBm");
  display.display();
}
