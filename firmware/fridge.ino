/*
 * /dev/lol fridge
 * (C) 2015 by Christoph (doebi) Döberl
*/

#include <HX711.h>
#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <PubSubClient.h>

#define DOUT  2
#define CLK  4

int zero_factor = 8458217;
float calibration_factor = 11600;

HX711 scale(DOUT, CLK);
ESP8266WiFiMulti wifiMulti;

IPAddress MQTTserver(158, 255, 212, 248);
WiFiClient wclient;
PubSubClient client(wclient, MQTTserver);

void mqtt_callback(const MQTT::Publish& pub) {
  String topic = pub.topic();
  String msg = pub.payload_string();
  if (topic == "devlol/h19/fridge/reset") {
    //TODO: write to EEPROM
    zero_factor = scale.read_average();
    scale.set_offset(zero_factor);
  }
  Serial.println(topic + " = " + msg);
}

void setup() {
  Serial.begin(115200);
  delay(10);

  //TODOD: read zero_factor from EEPROM

  wifiMulti.addAP("/dev/lol", "4dprinter");

  if(wifiMulti.run() == WL_CONNECTED) {
    Serial.println("Wifi connected");
  }

  scale.set_offset(zero_factor);
}

void loop() {

  // wifi
  if(WiFi.status() != WL_CONNECTED) {
    if(wifiMulti.run() == WL_CONNECTED) {
      Serial.println("Wifi connected");
    }
  }

  // mqtt
  if (client.connected()) {
    client.loop();
    scale.set_scale(calibration_factor);
    client.publish("devlol/h19/fridge/rawsamples", (String)scale.get_units());
  } else {
    if (client.connect("fridge", "devlol/h19/fridge/online", 0, true, "false")) {
      client.publish("devlol/h19/fridge/online", "true", true);
      Serial.println("MQTT connected");
      client.set_callback(mqtt_callback);
      client.subscribe("devlol/h19/fridge/#");
    }
  }
  delay(1000);
}
