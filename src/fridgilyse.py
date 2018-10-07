#!/usr/bin/python3

##
# Copyright 2015, Aurel Wildfellner.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#


import statistics
import argparse
import time

import mosquitto


MQTT_BASE_TOPIC = "devlol/h19/fridge"



mqtttopics = {
        "rawsamples" : MQTT_BASE_TOPIC + "/rawsamples",
        "door" : MQTT_BASE_TOPIC + "/door",
        "bottlesout" : MQTT_BASE_TOPIC + "/bottles/out",
        "bottlesin" : MQTT_BASE_TOPIC + "/bottles/in",
        "fridgilysestatus" : MQTT_BASE_TOPIC + "/fridgilysestatus"
}


class FridgeAnalys:

    class State:
        START = 0
        INIT_WEIGHT = 1
        CLOSED_STABLE = 2
        OPENED = 3
        CLOSED_UNSTABLE = 4


    def __init__(self, nsamples=10):
        self._cstate = self.State.START

        self._samples = []

        self._nsamples = nsamples
        self._stableDeviation = 0.015
        self._bottleWeight = 0.88
        self._maxBottleDeviation = 0.1

        self._currentWeight = -1.0

        self._bottlesOut = []
        self._bottlesIn = []


    def onOpen(self):
        if self._cstate == self.State.CLOSED_STABLE:
            self._cstate = self.State.OPENED
        elif self._cstate == self.State.INIT_WEIGHT:
            self._cstate = self.State.START


    def onClose(self):
        if self._cstate == self.State.START:
            self._cstate = self.State.INIT_WEIGHT
        elif self._cstate == self.State.OPENED:
            self._cstate = self.State.CLOSED_UNSTABLE


    def onStableMeasure(self, val):
        if self._cstate == self.State.INIT_WEIGHT:
            print("Initializing current fridge weight:", str(val))
            self._cstate = self.State.CLOSED_STABLE
            self._updateWeight(val)
        elif self._cstate == self.State.CLOSED_UNSTABLE:
            self._cstate = self.State.CLOSED_STABLE
            self._calculateBottles(val)
        elif self._cstate == self.State.CLOSED_STABLE:
            self._updateWeight(val)


    def onSingleMeasure(self, val):
        self._samples.insert(0, val)
        self._samples = self._samples[0:self._nsamples]
        if len(self._samples) == self._nsamples:
            stdev = statistics.stdev(self._samples)
            mean = statistics.mean(self._samples)
            if stdev < self._stableDeviation:
                self.onStableMeasure(mean)


    def _calculateBottles(self, val):
        diff = self._currentWeight - val
        if diff > 0:
            bottlesTaken = round(diff/self._bottleWeight)
            dev = abs(diff - bottlesTaken*self._bottleWeight)
            if dev <= self._maxBottleDeviation:
                if bottlesTaken > 0:
                    print("Bottles Taken: ", bottlesTaken)
                    self._bottlesOut.insert(0, bottlesTaken)
        else:
            # invert diff to a postiv value
            diff *= -1
            bottlesInserted = round(diff/self._bottleWeight)
            dev = abs(diff - bottlesInserted*self._bottleWeight)
            if dev <= self._maxBottleDeviation:
                if bottlesInserted > 0:
                    print("Bottles Inserted: ", bottlesInserted)
                    self._bottlesIn.insert(0, bottlesInserted)

        pass


    def _updateWeight(self, val):
        self._currentWeight = val


    def publishBottlesOut(self, client):
        while len(self._bottlesOut) > 0:
            botout = self._bottlesOut.pop()
            client.publish(mqtttopics['bottlesout'], str(botout))
        while len(self._bottlesIn) > 0:
            botbin = self._bottlesIn.pop()
            client.publish(mqtttopics['bottlesin'], str(botin))




def on_message(client, fridgelyse, msg):
    #print("message: t:", msg.topic, " pl:", msg.payload)
    payload = msg.payload.decode("utf-8")

    if msg.topic == mqtttopics['rawsamples']:
        try:
            sample = float(payload)
            fridgelyse.onSingleMeasure(sample)
        except ValueError:
            return

    elif msg.topic == mqtttopics['door']:
        if payload == "OPEN":
            fridgelyse.onOpen()
        elif payload == "CLOSE":
            fridgelyse.onClose()


def on_disconnect(client, userdate, foo):
    connected = False
    while not connected:
        try:
            client.reconnect()
            connected = True
            # resubscribe to the topics
            client.subscribe(mqtttopics['rawsamples'])
            client.subscribe(mqtttopics['door'])
            print("Reconnected to broker!")
        except:
            print("Faied to reconnect...")
            time.sleep(1)

def on_connect(client,userdate,foo):
    client.publish(mqtttopics['fridgilysestatus'],'online',qos=0,retain=True)

def main():

    ## Command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.8.2")
    args = parser.parse_args() 
    brokerHost = args.host

    fridgelyse =  FridgeAnalys(nsamples=4)

    ## setup MQTT client
    client = mosquitto.Mosquitto()
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.on_connect = on_connect
    client.user_data_set(fridgelyse)
    client.will_set(mqtttopics['fridgilysestatus'],'offline',qos=0,retain=True)
    client.connect(brokerHost)
    client.subscribe(mqtttopics['rawsamples'])
    client.subscribe(mqtttopics['door'])


    while True:
        client.loop()
        fridgelyse.publishBottlesOut(client)


if __name__ == "__main__":
    main()


