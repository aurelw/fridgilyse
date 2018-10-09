/**
 * Blink
 *
 * Turns on an LED on for one second,
 * then off for one second, repeatedly.
 */

#include "Arduino.h"
#include <HX711.h>

#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <PubSubClient.h>

#include "wifi_credentials.h"

/* pin out */
#define DOUT 2
#define CLK 4

/* scale */
int zero_factor = 8458217;
float calibration_factor = 11600;
int light;
int light_treshold = 50;
bool door_open = false;
bool b;

HX711 scale(DOUT, CLK);
/***********/

/* Network */
ESP8266WiFiMulti wifiMulti;
IPAddress MQTTserver(158, 255, 212, 248);
WiFiClient wclient;
PubSubClient client(MQTTserver, 1883, wclient);
/***********/

/* inefficient but i see no better way atm */
inline String byteArrayToString(byte* array, unsigned int length) {
  char chars[length+1];
  for (unsigned int i=0; i<length; i++) {
    chars[i] =  (char) array[i];
  }
  chars[length] = '\0';
  return chars;
}

void check_light() {
  light = analogRead(A0);
  Serial.println(light);
  b = light > light_treshold;
  for (int i = 0; i++; i < 10) {
    delay(10);
    light = analogRead(A0);
    Serial.println(light);
    if (b != (light > light_treshold)){
      return;
    }
  }
  if (b != door_open) {
    door_open = b;
    if (door_open) {
      client.publish("devlol/h19/fridge/door", "OPEN");
    } else {
      client.publish("devlol/h19/fridge/door", "CLOSE");
    }
  }
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {

  String msg = byteArrayToString(payload, length);
  if (topic == "devlol/h19/fridge/reset") {
    zero_factor = scale.read_average();
    scale.set_offset(zero_factor);
  }

}

void setup() {
  //Serial.println("setup");
  // initialize LED digital pin as an output.

  //Serial.begin(115200);
  delay(1000);

  for (int i=0; i<NUM_WIFI_CREDENTIALS; i++) {
    wifiMulti.addAP(WIFI_CREDENTIALS[i][0], WIFI_CREDENTIALS[i][1]);
  }

  if(wifiMulti.run() == WL_CONNECTED) {
    //Serial.println("Wifi connected.");
  } else {
    //Serial.println("Wifi not connected!");
  }

  scale.set_offset(zero_factor);
}

void loop() {
  static bool wifiConnected = false;

  //Serial.println("loop");
  //Serial.println(counter);
  delay(1000);
#if 1
  /* reconnect wifi */
  if(wifiMulti.run() == WL_CONNECTED) {
    if (!wifiConnected) {
      //Serial.println("Wifi connected.");
      wifiConnected = true;
    }
  } else {
    if (wifiConnected) {
      //Serial.println("Wifi not connected!");
      wifiConnected = false;
    }
  }

  /* MQTT */
  if (client.connected()) {
    client.loop();
    scale.set_scale(calibration_factor);
    String scale_units = String(scale.get_units(), 3);
    client.publish("devlol/h19/fridge/rawsamples", scale_units.c_str(), true);
  } else {
    if (client.connect("fridge", "devlol/h19/fridge/online", 0, true, "false")) {
      client.publish("devlol/h19/fridge/online", "true", true);
      //Serial.println("MQTT connected");
      client.setCallback(mqtt_callback);
      client.subscribe("devlol/h19/fridge/#");
    }
  }
#endif
  yield();

  //Serial.println("endloop");
}
