# Automated Battery Test Application
# Florian Uhlemann (C) 2022   

import serial, sys, glob
from threading import Thread
from time import sleep
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pushnotifier import PushNotifier as pn




global comportList, instanceCounter, connectPacket, disconnectPacket, stopCommandPacket, dischargeCmdPacket, chargeCmdPacket, token, bucket, org, pn, serialDevices


token = "2CrdAjVGcuw7XTnTSHXUq-rqOvL8A_QAudkWgOeX2kWLAIW5oWLxWdMIT4Bo-_8XOvV6zZQE9nITqbUxrxMoDg=="
bucket = "BatteryTesterBucket"
org = "BatteryTesterName"

pn = pn.PushNotifier('florianuhlemann', 'Karlmarx2711a', 'batterytester', '8E7D6C3VEV46BV46BV4663CVB5LO6575BETKFFBFBF')

pnDevices = pn.get_all_devices()
print(pnDevices)
# pn.send_text('App started...', silent=False, devices=pnDevices)
# pn.send_notification('BatteryTester starting...', 'https://www.google.de', devices=pnDevices, silent=False)


comportList = []
serialDevices = [None, None, None, None]
instanceCounter = 1
connectPacket      = b'\xfa\x05\x00\x00\x00\x00\x00\x00\x05\xf8'
disconnectPacket   = b'\xfa\x06\x00\x00\x00\x00\x00\x00\x06\xf8'
stopCommandPacket  = b'\xfa\x02\x00\x00\x00\x00\x00\x00\x02\xf8'
#dischargeCmdPacket = b'\xfa\x01\x0d\x50\x01\x0a\x00\x00\x57\xf8' #normal 32A
dischargeCmdPacket = b'\xfa\x01\x0d\x50\x01\x0a\x00\x3c\x6b\xf8' #normal 32A for 60min only
chargeCmdPacket    = b'\xfa\x21\x0d\x50\x01\x7d\x00\x0a\x0a\xf8' #normal 32A
# dischargeCmdPacket = b'\xfa\x01\x10\xa0\x01\x58\x00\x00\xe8\xf8' #testing
# dischargeCmdPacket = b'\xfa\x01\x10\xa0\x01\x0a\x00\x00\xba\xf8' #normal 40A
# chargeCmdPacket    = b'\xfa\x21\x0c\x78\x01\x7d\x00\x0a\x23\xf8' #normal 30A
# chargeCmdPacket    = b'\xfa\x21\x0c\x78\x01\x62\x03\x50\x65\xf8' #testint



def serial_ports():
    global comportList
    ports = glob.glob('/dev/ttyUSB*')
    comportList = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            comportList.append(port)
        except Exception as e:
            print("ERROR: {}".format(e))
    return comportList



def sendToInflux(data):
    global token, org, bucket
    print("sendToInflux: {}".format(data))
    with InfluxDBClient(url="http://192.168.1.197:8086", token=token, org=org) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        try:
            write_api.write(bucket, org, data)
        except Exception as e:
            print("ERROR: {}".format(e))
        client.close()
    pass



def startLoop():
    while True:
        #do nothing
        pass



def startInstanceLoop():
    global comportList, instanceCounter, connectPacket, disconnectPacket, stopCommandPacket, dischargeCmdPacket, chargeCmdPacket

    connectedState = False
    chargedState = False
    chargingState = False
    dischargedState = False
    dischargingState = False
    chargingStartedState = False
    isCancelledState = False

    currentState = "Idle"
    timeCounter = 0
    instanceId = instanceCounter
    print("Starting Test Loop #{}".format(instanceId))
    instanceCounter += 1
    messageBuf = []

    serialPort = comportList[0]
    comportList.pop(0)
    print(comportList)
    try:
        serialDevices[instanceId-1] = serial.Serial(port=serialPort, baudrate=9600, parity=serial.PARITY_ODD)
        # ser = serial.Serial(port=serialPort, baudrate=9600, parity=serial.PARITY_ODD)
        sleep(0.5)
        print("connect", end="")
        serialDevices[instanceId-1].write(connectPacket)
        sleep(0.25)
        serialDevices[instanceId-1].write(connectPacket)
        print("ed!")
        sleep(0.25)

        while True:
            if (serialDevices[instanceId-1].inWaiting() > 0):
                messageBuf.append(int.from_bytes(serialDevices[instanceId-1].read(),byteorder='big',signed=False))
                if messageBuf[0] == 250:
                    if len(messageBuf) > 1:
                        if (len(messageBuf) == 19) and (messageBuf[len(messageBuf)-1] == 248):
                            current = float((messageBuf[2] * 240 + messageBuf[3]) / 100.0)
                            voltage = float((messageBuf[4] * 240 + messageBuf[5]) / 1000.0)
                            capacity = int((messageBuf[6] * 240 + messageBuf[7]))

                            if (messageBuf[6] > 139):
                                capacity = (capacity - 32768) * 10
                                # print("NEED TO SCALE", end="")

                            if voltage == 0.0:
                                print("STATE_1_ ", end="")
                                connectedState = False
                                currentState = "Idle"
                                if isCancelledState == False:
                                    isCancelledState = True
                                    serialDevices[instanceId-1].write(stopCommandPacket)
                                    serialDevices[instanceId-1].write(stopCommandPacket)
                                timeCounter = 0
                            elif ((voltage > 0.0) and (connectedState == False)):
                                print("STATE_2_ ", end="")
                                if timeCounter < 5:
                                    timeCounter += 1
                                else:
                                    timeCounter = 0
                                    connectedState = True
                                    chargedState = False
                                    chargingStartedState = False
                                    chargingState = False
                                    dischargedState = False
                                    dischargingStartedState = False
                                    dischargingState = False
                            elif ((voltage > 0.0) and (connectedState == True) and (chargingState == False) and (chargingStartedState == False) and (chargedState == False) and (current == 0.0)):
                                print("STATE_3_ ", end="")
                                isCancelledState = False
                                serialDevices[instanceId-1].write(chargeCmdPacket)
                                serialDevices[instanceId-1].write(chargeCmdPacket)
                                currentState = "Charging"
                                print("charging started in InstanceID{}...".format(instanceId), end="")
                                chargingStartedState = True
                            elif ((voltage > 0.0) and (connectedState == True) and (chargingState == False) and (chargingStartedState == True) and (chargedState == False) and (current == 0.0)):
                                print("STATE_4_ ", end="")
                                #waiting for charging to start...
                                pass
                            elif ((voltage > 0.0) and (connectedState == True) and (chargingState == False) and (chargingStartedState == True) and (chargedState == False) and (current > 0.0)):
                                print("STATE_5_ ", end="")
                                chargingStartedState = False
                                chargingState = True
                            elif ((voltage > 0.0) and (connectedState == True) and (chargingState == True) and (chargingStartedState == False) and (chargedState == False) and (current > 0.0)):
                                print("STATE_6_ ", end="")
                                #print("charging...")
                                pass
                            elif ((voltage > 0.0) and (connectedState == True) and (chargingState == True) and (chargingStartedState == False) and (chargedState == False) and (current == 0.0)):
                                print("STATE_7_ ", end="")
                                if timeCounter < 5:
                                    timeCounter += 1
                                else:
                                    timeCounter = 0
                                    chargedState = True
                                    chargingState = False
                                    currentState = "Charged"
                                    serialDevices[instanceId-1].write(stopCommandPacket)
                                    serialDevices[instanceId-1].write(stopCommandPacket)
                                    isCancelledState = True
                            elif ((voltage > 0.0) and (connectedState == True) and (chargedState == True) and (dischargingState == False) and (dischargingStartedState == False)):
                                print("STATE_8_ ", end="")
                                isCancelledState = False
                                serialDevices[instanceId-1].write(dischargeCmdPacket)
                                serialDevices[instanceId-1].write(dischargeCmdPacket)
                                dischargingStartedState = True
                                currentState = "Discharging"
                                print("discharging started in InstanceID{}...".format(instanceId), end="")
                            elif ((voltage > 0.0) and (connectedState == True) and (chargedState == True) and (dischargingState == False) and (dischargingStartedState == True) and (dischargedState == False) and (current == 0.0)):
                                print("STATE_9_ ", end="")
                                #waiting for discharging to start
                                pass
                            elif ((voltage > 0.0) and (connectedState == True) and (chargedState == True) and (dischargingState == False) and (dischargingStartedState == True) and (dischargedState == False) and (current > 0.0)):
                                print("STATE_10_ ", end="")
                                dischargingStartedState = False
                                dischargingState = True
                            elif ((voltage > 0.0) and (connectedState == True) and (chargedState == True) and (dischargingState == True) and (dischargingStartedState == False) and (dischargedState == False) and (current > 0.0)):
                                print("STATE_11_ ", end="")
                                #discharging
                            elif ((voltage > 0.0) and (connectedState == True) and (chargedState == True) and (dischargingState == True) and (dischargingStartedState == False) and (dischargedState == False) and (current == 0.0)):
                                print("STATE_12_ ", end="")
                                #discharge completed
                                dischargedState = True
                                currentState = "Discharged"
                                serialDevices[instanceId-1].write(stopCommandPacket)
                                serialDevices[instanceId-1].write(stopCommandPacket)
                                isCancelledState = True
                                pn.send_text("Batterie #{} ist fertig vermessen! {:.2f}Ah Kapazität! Bitte tauschen!".format(instanceId, capacity / 1000.0), silent=False, devices=pnDevices)
                            elif ((voltage > 0.0) and (connectedState == True) and (dischargedState == True)):
                                print("STATE_13_ ", end="")
                                # waiting for battery to be disconnected...
                                # print("SENDING ALERT! COMPLETED", end="")
                                pass
                            else:
                                print("ERROR: unknown state")
                                print("connectedState={}  ".format(connectedState), end="")
                                print("chargedState={}  ".format(chargedState), end="")
                                print("chargingState={}  ".format(chargingState), end="")
                                print("chargingStartedState={}  ".format(chargingStartedState), end="")
                                print("dischargedState={}  ".format(dischargedState), end="")
                                print("dischargingState={}  ".format(dischargingState), end="")
                                #print("={}".format(), end="")


                            # data = "bat{} voltage={},current={},capacity={},state={}".format(instanceId,voltage,current,capacity,currentState)
                            data = "bat{} voltage={:.3f},current={:.2f},capacity={}".format(instanceId,voltage,current,capacity)
                            sendToInflux(data)
                            messageBuf = []
                        elif len(messageBuf) > 19:
                            messageBuf = []
                    # all good, continue
                else:
                    messageBuf = []
            sleep(0.01) 

            pass
    except Exception as e:
        print("ERROR: InstanceID{} with {}".format(instanceId, e))






# Python Main Routine
if __name__ == "__main__":
    print("Starting Automated Testing...")
    print("Found serial ports: {}".format(serial_ports()))
    threads = list()
    # print("len = {}".format(len(comportList)))
    for each in range(len(comportList)): #startUi
        # print("trying to start...")
        x = Thread(target=startInstanceLoop)
        threads.append(x)
        x.start()
        sleep(0.25)
    for each in threads:
        each.join()
        pass
    print("ERROR: all threads stopped...")
    exit()
    pass
