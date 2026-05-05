#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

#define LORA_SS   10
#define LORA_RST  9
#define LORA_DIO0 2

void setup() {
  Serial.begin(9600);

  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed!");
    while (1);
  }

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
  if (packetSize) {
    String received = "";
    while (LoRa.available()) {
      received += (char)LoRa.read();
    }

    Serial.println("DATA:" + received); // send to computer for website

    // Parse: LAT,LNG,TEXT
    int firstComma = received.indexOf(',');
    int secondComma = received.indexOf(',', firstComma + 1);

    String lat = received.substring(0, firstComma);
    String lng = received.substring(firstComma + 1, secondComma);
    String msg = received.substring(secondComma + 1);

    int rssi = LoRa.packetRssi();

    // Show on OLED
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