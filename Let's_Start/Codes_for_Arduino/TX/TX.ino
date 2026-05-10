#include <SPI.h>                 // SPI library for LoRa communication
#include <LoRa.h>                // LoRa library for SX1278/SX1276 modules
#include <SoftwareSerial.h>      // Software serial for GPS module
#include <TinyGPS++.h>           // TinyGPS++ library for parsing GPS data

// GPS module connected via SoftwareSerial
// Pin 4 = RX (receives data from GPS TX)
// Pin 3 = TX (sends data to GPS RX)
SoftwareSerial gpsSerial(4, 3);
TinyGPSPlus gps;                 // GPS object

// LoRa module pin definitions
#define LORA_SS   10             // Chip Select (NSS)
#define LORA_RST  9              // Reset pin
#define LORA_DIO0 2              // Interrupt pin (DIO0)

String textMessage;              // Message to send along with GPS data

void setup() {
  Serial.begin(9600);            // Start serial monitor
  gpsSerial.begin(9600);         // Start GPS serial communication

  // Initialize LoRa with defined pins
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(433E6)) {      // Start LoRa at 433 MHz
    Serial.println("LoRa init failed!");
    while (1);                   // Halt if initialization fails
  }
  Serial.println("LoRa TX ready"); // Indicate transmitter is ready
}

void loop() {
  // Continuously feed GPS data to TinyGPS++ parser
  while (gpsSerial.available()) {
    gps.encode(gpsSerial.read());
  }

  // If GPS location is updated successfully
  if (gps.location.isUpdated()) {
    double lat = gps.location.lat();   // Get latitude
    double lng = gps.location.lng();   // Get longitude

    // Read message from Serial Monitor if available
    if (Serial.available() > 0) {
      textMessage = Serial.readString();
    } else {
      textMessage = "Hello Trainee!";   // Default message
    }

    // Build packet in format: LAT,LNG,TEXT
    String packet = String(lat, 6) + "," + String(lng, 6) + "," + textMessage;

    Serial.println("Sending: " + packet); // Print packet to Serial

    // Send packet via LoRa
    LoRa.beginPacket();
    LoRa.print(packet);
    LoRa.endPacket();
  }
  else{
    Serial.println("waiting for gps data");
  }
  delay(2000); // Send every 2 seconds
}
