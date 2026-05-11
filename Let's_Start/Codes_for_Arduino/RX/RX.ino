/*
 * rx.ino — LoRa Receiver with OLED display
 * Receives GPS coordinates + text message via LoRa and displays them
 * on a 128x64 SSD1306 OLED. Also forwards data via USB serial to the
 * Python server in this format:
 *     DATA:<lat>,<lng>,<message>,RSSI:<value>
 * Example:
 *     DATA:17.385000,78.486700,Hello Trainee!,RSSI:-87
 * Libraries:
 *   LoRa             by Sandeep Mistry
 *   Adafruit GFX
 *   Adafruit SSD1306
 */

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// OLED configuration
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT  64
#define OLED_RESET     -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// LoRa pin definitions
#define LORA_SS    10
#define LORA_RST    9
#define LORA_DIO0   2

void setup() {
  Serial.begin(9600);

  // Initialise LoRa
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(433E6)) {
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

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize == 0) return;

  // FIX: Start with an empty string (was incorrectly pre-loaded)
  String received = "";
  while (LoRa.available()) {
    received += (char)LoRa.read();
  }

  // Read RSSI immediately after receiving (most accurate)
  int rssi = LoRa.packetRssi();

  // Serial output for Python server
  // Format: DATA:<lat>,<lng>,<message>,RSSI:<value>
  Serial.print("DATA:");
  Serial.print(received);
  Serial.print("| RSSI:");
  Serial.println(rssi);

  // Parse fields for OLED display
  int firstComma  = received.indexOf('|');
  int secondComma = received.indexOf('|', firstComma + 1);

  if (firstComma < 0 || secondComma < 0) return;   // skip malformed packets

  String lat = received.substring(0, firstComma);
  String lng = received.substring(firstComma + 1, secondComma);
  String msg = received.substring(secondComma + 1);

  // Update OLED
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("GPS Tracker RX");
  display.println("Lat: " + lat);
  display.println("Lng: " + lng);
  display.println("Msg: " + msg);
  display.println("RSSI: " + String(rssi) + " dBm");
  display.display();
}

