#include <SPI.h>                 // SPI library for communication with LoRa
#include <LoRa.h>                // LoRa library for SX1278/SX1276 modules
#include <Wire.h>                // I2C library for OLED display
#include <Adafruit_GFX.h>        // Graphics library for OLED
#include <Adafruit_SSD1306.h>    // OLED driver library

// OLED display configuration
#define SCREEN_WIDTH 128         // OLED width in pixels
#define SCREEN_HEIGHT 64         // OLED height in pixels
#define OLED_RESET -1            // Reset pin (not used here)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// LoRa module pin definitions
#define LORA_SS   10             // Chip Select (NSS)
#define LORA_RST  9              // Reset pin
#define LORA_DIO0 2              // Interrupt pin (DIO0)

void setup() {
  Serial.begin(9600);            // Start serial communication at 9600 baud

  // Initialize LoRa with defined pins
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(433E6)) {      // Start LoRa at 433 MHz
    Serial.println("LoRa init failed!");
    while (1);                   // Halt if initialization fails
  }

  // Initialize OLED display
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // Address 0x3C for OLED
    Serial.println("OLED failed");
    while (1);                   // Halt if OLED fails
  }

  // Show initial message on OLED
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("Waiting for data...");
  display.display();

  Serial.println("LoRa RX ready"); // Indicate receiver is ready
}

void loop() {
  // Check if a LoRa packet has been received
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String received = "";
    while (LoRa.available()) {
      received += (char)LoRa.read();  // Read incoming data
    }

    Serial.println("DATA:" + received); // Print received data to Serial

    // Parse received string in format: LAT,LNG,TEXT
    int firstComma = received.indexOf(',');
    int secondComma = received.indexOf(',', firstComma + 1);

    String lat = received.substring(0, firstComma);              // Extract latitude
    String lng = received.substring(firstComma + 1, secondComma); // Extract longitude
    String msg = received.substring(secondComma + 1);             // Extract message

    int rssi = LoRa.packetRssi(); // Get signal strength (RSSI)

    // Display parsed data on OLED
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("GPS Tracker RX");
    display.println("Lat: " + lat);
    display.println("Lng: " + lng);
    display.println("Msg: " + msg);
    display.println("RSSI: " + String(rssi));
    display.display();
  }
}
