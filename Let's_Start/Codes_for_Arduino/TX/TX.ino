#include <SPI.h>
#include <LoRa.h>
#include <SoftwareSerial.h>
#include <TinyGPS++.h>

// GPS on pins 3 (TX to GPS RX) and 4 (RX from GPS TX)
SoftwareSerial gpsSerial(4, 3);
TinyGPSPlus gps;

#define LORA_SS   10
#define LORA_RST  9
#define LORA_DIO0 2

String textMessage ; // change this to your text

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
  // Feed GPS data
  while (gpsSerial.available()) {
    gps.encode(gpsSerial.read());
  }

  if (gps.location.isUpdated()) {
    double lat = gps.location.lat();
    double lng = gps.location.lng();
    if(Serial.available()>0){
      textMessage = Serial.readString();
    }
    else{
      textMessage = "Hello Traine!";
    }
    // Build packet: LAT,LNG,TEXT
    String packet = String(lat, 6) + "," + String(lng, 6) + "," + textMessage;

    Serial.println("Sending: " + packet);

    LoRa.beginPacket();
    LoRa.print(packet);
    LoRa.endPacket();
  }
  else{
    double lat = 17.087741;
    double lng = 82.068771;
     if(Serial.available()>0){
      textMessage = Serial.readString();
    }
    else{
      textMessage = "Hello Traine!";
    }

    // Build packet: LAT,LNG,TEXT
    String packet = String(lat, 6) + "," + String(lng, 6) + "," + textMessage;

    Serial.println("Sending: " + packet);

    LoRa.beginPacket();
    LoRa.print(packet);
    LoRa.endPacket();
  }
  delay(2000); // send every 2 seconds
  }