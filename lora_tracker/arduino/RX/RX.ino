/*
 * RX.ino - LoRa Receiver with OLED display
 *
 * Receives "<seq>,<lat>,<lng>,<message>" packets over LoRa and forwards
 * them to the Python server over USB serial in this exact format
 * (note the comma BEFORE "RSSI:" as documented):
 *
 *     DATA:<seq>,<lat>,<lng>,<message>,RSSI:<value>
 *
 * Example:
 *     DATA:42,17.385000,78.486700,Hello Trainee!,RSSI:-87
 *
 * Legacy packets (no sequence number) are still forwarded transparently;
 * the server accepts both formats.
 *
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

  String received = "";
  while (LoRa.available()) {
    received += (char)LoRa.read();
  }

  // Read RSSI immediately after receiving (most accurate)
  int rssi = LoRa.packetRssi();

  // ----------------------------------------------------------------
  // Forward to Python server in the documented format:
  //   DATA:<received>,RSSI:<value>
  // Note the COMMA before "RSSI:" - the server\\'s is_valid() requires it.
  // ----------------------------------------------------------------
  Serial.print("DATA:");
  Serial.print(received);
  Serial.print(",RSSI:");
  Serial.println(rssi);

  // ----------------------------------------------------------------
  // Parse fields for OLED display.
  // New format: seq,lat,lng,msg     (4 commas-delimited fields)
  // Legacy:     lat,lng,msg         (3 fields, no seq)
  // We detect new format if the first comma-separated field is a
  // pure integer.
  // ----------------------------------------------------------------
  int firstComma  = received.indexOf(',');
  int secondComma = received.indexOf(',', firstComma + 1);
  int thirdComma  = received.indexOf(',', secondComma + 1);
  if (firstComma < 0 || secondComma < 0) return;   // malformed

  String seqStr = "";
  String lat, lng, msg;

  // Try new format (4 fields) when a 3rd comma exists AND first field is an integer
  bool hasSeq = false;
  if (thirdComma > 0) {
    String first = received.substring(0, firstComma);
    hasSeq = true;
    for (unsigned int i = 0; i < first.length(); i++) {
      if (!isDigit(first[i])) { hasSeq = false; break; }
    }
    if (first.length() == 0) hasSeq = false;
  }

  if (hasSeq) {
    seqStr = received.substring(0, firstComma);
    lat    = received.substring(firstComma + 1, secondComma);
    lng    = received.substring(secondComma + 1, thirdComma);
    msg    = received.substring(thirdComma + 1);
  } else {
    lat = received.substring(0, firstComma);
    lng = received.substring(firstComma + 1, secondComma);
    msg = received.substring(secondComma + 1);
  }

  // Update OLED
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("GPS Tracker RX");
  if (hasSeq) display.println("Seq: " + seqStr);
  display.println("Lat: " + lat);
  display.println("Lng: " + lng);
  display.println("Msg: " + msg);
  display.println("RSSI: " + String(rssi) + " dBm");
  display.display();
}
