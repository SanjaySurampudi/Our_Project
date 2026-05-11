/*
 * tx.ino — LoRa Transmitter with GPS
 *
 * Sends GPS coordinates + text message via LoRa every 2 seconds.
 *
 * Packet format:  lat,lng,message
 *
 * Libraries:
 *   LoRa            by Sandeep Mistry
 *   TinyGPSPlus     by Mikal Hart
 *   SoftwareSerial  (built-in)
 */

#include <SPI.h>
#include <LoRa.h>
#include <SoftwareSerial.h>
#include <TinyGPS++.h>

// GPS module connected via SoftwareSerial
// Pin 4 = RX (receives data from GPS TX)
// Pin 3 = TX (sends data to GPS RX)
SoftwareSerial gpsSerial(4, 3);
TinyGPSPlus gps;

// LoRa module pin definitions
#define LORA_SS   10
#define LORA_RST   9
#define LORA_DIO0  2

String textMessage = "Hello Trainee!";   // Default message (set once)

void setup() {
  Serial.begin(9600);
  gpsSerial.begin(9600);

  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(433E6)) {
    Serial.println("LoRa init failed!");
    while (1);
  }

  Serial.println("LoRa TX ready");
}

void loop() {
  // Feed GPS data to TinyGPS++ parser
  while (gpsSerial.available()) {
    gps.encode(gpsSerial.read());
  }

  // Read new message from Serial Monitor if available (non-blocking)
  if (Serial.available() > 0) {
    String incoming = Serial.readStringUntil('\n');
    incoming.trim();
    incoming.replace(',', ' ');   // protect CSV parser on RX side
    if (incoming.length() > 0) {
      textMessage = incoming;
      Serial.println("Message updated: " + textMessage);
    }
  }

  // Only transmit when GPS has a valid fix
  if (!gps.location.isValid()) {
    Serial.println("Waiting for GPS fix...");
    delay(2000);
    return;
  }

  double lat = gps.location.lat();
  double lng = gps.location.lng();

  // Build packet: LAT,LNG,MESSAGE
  String packet = String(lat, 6) + "," + String(lng, 6) + "," + textMessage;
  Serial.println("Sending: " + packet);

  // Send via LoRa
  LoRa.beginPacket();
  LoRa.print(packet);
  LoRa.endPacket();

  delay(2000);   // Send every 2 seconds
}

