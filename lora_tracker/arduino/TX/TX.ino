/*
 * TX.ino - LoRa Transmitter with GPS + sequence number
 *
 * Packet format sent over the air:
 *     <seq>,<lat>,<lng>,<message>
 * Example:
 *     42,17.385000,78.486700,Hello Trainee!
 *
 * The RX side prepends "DATA:" and appends ",RSSI:<value>" before
 * forwarding to the Python server.
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

String   textMessage = "Hello Trainee!";   // default message (set once)
uint32_t sequence    = 0;                  // monotonically increasing packet counter

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

  // Build packet: SEQ,LAT,LNG,MESSAGE
  String packet = String(sequence) + "," +
                  String(lat, 6)   + "," +
                  String(lng, 6)   + "," +
                  textMessage;

  Serial.println("Sending: " + packet);

  LoRa.beginPacket();
  LoRa.print(packet);
  LoRa.endPacket();

  sequence++;        // increment for next packet
  delay(2000);       // send every 2 seconds
}
