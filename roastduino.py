import matplotlib
matplotlib.use('TkAgg')

from winreg import *

import matplotlib.pyplot as plt
import serial
from serial.tools.list_ports_windows import comports
import time
import datetime
import random
from tkinter import messagebox
import tkinter as tk
from tkinter import simpledialog
from matplotlib.widgets import Button
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import AutoMinorLocator

from matplotlib.ticker import FormatStrFormatter

#commands need to be 4 characters with  first character of +
GET_REALTIME = "+GA "
GET_PROFILE = "+GB "
GET_ACTIVERUN = "+GC "
GET_REALTIMEALL = "+GD "
ACTION_START = "+AS "
ACTION_STOP = "+AE "
ACTION_FAN = "+AF "
ACTION_CLEAR_IS = "+AC "
ACTION_REFRESH = "+AR "
ACTION_TOGGLE_ROAST = "+AT "


testmode = "False"
logconsole = "True"
#testmode = "True"
#These are partial commands...an integer needs to be appended to the end
ACTION_I_ALL = "+IA"
ACTION_D_ALL = "+DA"
ACTION_I = "+I"
ACTION_D = "+D"
ACTION_I_TIME = "+IT"
ACTION_D_TIME = "+DT"
ACTION_I_INTEGRAL = "+II"
ACTION_D_INTEGRAL = "+DI"
ACTION_I_GAIN = "+IG"
ACTION_D_GAIN = "+DG"

LogFileName = datetime.datetime.now().strftime('log_%Y_%m_%d') + ".log"
ComPort = serial.Serial()

LastRunningTemp = 100
LastRunningMinutes = 12.1

currenttemptime = 0

def FindHC05BlueToothPort():
    logme = "False"
    kHKLM = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
    kBTPORTDevices = OpenKey(kHKLM, r"SYSTEM\ControlSet001\Services\BTHPORT\Parameters\Devices")
    r = QueryInfoKey(kBTPORTDevices)
    #print("  " + r"SYSTEM\ControlSet001\Services\BTHPORT\Parameters\Devices")
    for i in range(0,(r[0] )):
        devicename = EnumKey(kBTPORTDevices, i)
        if logme == "True": print ("    " + devicename)
        kDevice = OpenKey(kBTPORTDevices, devicename)
        r2 = QueryInfoKey(kDevice)
        for i2 in range(0,(r2[0] )):
            deviceSubKeyName = EnumKey(kDevice, i2)
            if str(deviceSubKeyName).startswith("ServicesFor"):
                if logme == "True": print ("      " + deviceSubKeyName)
                kdeviceSub = OpenKey(kDevice, deviceSubKeyName)
                guid = EnumKey(kdeviceSub, 0)
                aKey4 = OpenKey(kdeviceSub,guid)
                keyname5 = EnumKey(aKey4, 0)
                if logme == "True": print ("             " + keyname5)
                aKey5 = OpenKey(aKey4, keyname5)
                val = QueryValueEx(aKey5,"PriLangServiceName")
                valstr = val[0].decode("utf-8")
                if (valstr.startswith("Dev B")):
                    if logme == "True": print("            PrimLangServiceName:" + valstr)
                    strNextKye = str(guid) + "_LOCALMFG"
                    if logme == "True": print ("              " + strNextKye)
                    kBTHENUM = OpenKey(kHKLM, r"SYSTEM\\ControlSet001\\Enum\\BTHENUM")
                    if logme == "True": print ("")
                    if logme == "True": print("  " + r"SYSTEM\\ControlSet001\\Enum\\BTHENUM")

                    r3 = QueryInfoKey(kBTHENUM)
                    for i3 in range(0, (r3[0] )):
                        key6name = EnumKey(kBTHENUM, i3)
                        if str(key6name).startswith(strNextKye):
                            kKey6 = OpenKey(kBTHENUM, key6name)
                            key7name = EnumKey(kKey6, 0)
                            if str(key7name).upper().find(str(devicename).upper())>0:
                                if logme == "True": print("    " +  str(key7name))
                                aKey7 = OpenKey(kKey6, key7name)
                                key8name = EnumKey(aKey7, 0)
                                if logme == "True": print ("      "  + key8name)
                                kKey8 = OpenKey(aKey7, key8name)
                                val3 = QueryValueEx(kKey8, "PortName")
                                if logme == "True": print ("         " + str(val3[0]))
                                Log("HC05 Dev B comport found in registry:" + str(val3[0]))
                                return(str(val3[0]))

def maxminutes():
    return float(setpoints[5][1])

def maxtemp():
    return int(setpoints[5][2])

def endminutes():
    return float(setpoints[endsetpoint][1])

def endtemp():
    return int(setpoints[endsetpoint][2])

def firstminutes():
    return float(int(setpoints[1][1]) + int(setpoints[2][1]))/2

def firsttemp():
    print ("here3")
    print(str(setpoints[1][2]))
    print(str(setpoints[2][2]))
    print(str(setpoints[1][2] + setpoints[2][2]))
    return int(int(setpoints[1][2]) + int(setpoints[1][2]))/2

def Log(line):
    with open(LogFileName, "a") as myfile:
        ts = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
        if (logconsole == "True"):
            print(ts + " " + str(line))
        myfile.write(ts + " " + str(line) + '\n')

def PlaceSetPointAnnotation():
    annotateendpoint.set_x(float(setpoints[endsetpoint][1]) - .5)
    annotateendpoint.set_y(float(setpoints[endsetpoint][2]) + int(zoomhoroffset))
    annotateendpoint.set_text(str(setpoints[endsetpoint][2]) + "@" + str(setpoints[endsetpoint][0]))

testingstate = "Stopped"
endsetpoint = 4
test_endsetpoint = 4
setpoints = [[0, 2, 100], [1, 5, 300], [2, 6, 400], [3, 10, 450], [4, 12, 500], [5, 17, 550]]
zoomhoroffset = 10
application_window = tk.Tk()
application_window.wm_title("RoastDuino")
laststate = "unk"
polling = "False"
commandlist = ["",""]
commandlist.clear()

def submitadhoccommand(command):
    global commandlist
    print(command)
    if not (command.startswith('+')):
        print ("command did not start with +")
        return "Error"
    if polling == "True":
        Log("Add command to polling list:" + str(command))
        commandlist.append(command)
        r = "PendingPoll:" + ",".join(commandlist)
        labelCommands.configure(text=r, width=len(r))
    else:
        msg = "Pending:" + command
        Log("Submit non polling command:" + str(command))
        labelCommands.configure(text=msg, width=len(msg))
        rrr = ""
        rrr = sendcommandtocomport(command)
        return procescommandresult(command, rrr)

def pollingevent():
     global commandlist

     for x in commandlist:
         Log("Submit polling list command:" + str(x))
         if (str(x)).startswith("+"):
            print ("doing command in list:" + str(x))
            r = sendcommandtocomport(x)
            procescommandresult(x, r)
         else:
             print ("found bad command in que:'" + str(x) + "'")
     commandlist.clear()
     labelCommands.configure(text="", width=5)
     rr = ""
     Log("Submit polling command:" + str(GET_REALTIME))
     rr = sendcommandtocomport(GET_REALTIME)
     procescommandresult(GET_REALTIME, rr)

class pollingTimer:
    def start(self, timerlabel):
        # variable storing time
        global polling
        global ComPort
        self.count = 0
        self.label = timerlabel
        polling = "True"
        pollingevent()
        self.label.configure(text="GO")
        self.label.after(2000, self.refresh_label)

    def refresh_label(self):
        self.count += 1
        Log("poll event fired")
        pollingevent()
        global polling
        if polling == 'True':
            self.label.configure(text=(str(self.count)))
            Log("Set next poll event")
            self.label.after(2000, self.refresh_label)
        else:
            self.label.configure(text=(str(self.count)))
            self.label.configure(bg="pink")
            Poll_button.label.set_text("Connect")
            canvas.draw()

def pollingFalse():
    global polling
    if polling == "True":
        polling = "False"
        Log(" Stopping polling")

def closecomport():
    global ComPort
    r = ""
    try:
        if ComPort.isOpen():
            r = "closing open comport"
            ComPort.close()
        else:
            r = "ComPort not open"
    except Exception as e:
        r = "Error closing comport . Error was:" + str(e)
    Log(str(r))
    return r

def sendcommandtocomport(command):
    global polling
    global ComPort
    if testmode == "True":
        return "testing"
    if not ComPort.isOpen():
        try:
            comportname = FindHC05BlueToothPort()
            if comportname == "":
                messagebox.showinfo(" Err opening comport ", "No comport entered")
                pollingFalse()
                return "Error"
                comportname = simpledialog.askstring("Enter a Comport", portcsv, parent=application_window)
                if comportname == "":
                    messagebox.showinfo(" Err opening comport ", "No comport entered")
                    pollingFalse()
                    return "Error"
            Log("opening  port " + comportname)
            ComPort = serial.Serial(comportname)  # open COM24
            ComPort.baudrate = 9600  # set Baud rate to 9600
            ComPort.bytesize = 8  # Number of data bits = 8
            ComPort.parity = 'N'  # No parity
        except Exception as e:
            pollingFalse()
            Log("Err opening " + str(comportname) + " Error was:" + str(e))
            messagebox.showinfo("Err opening " + str(comportname), "Error was:" + str(e))
            ComPort.close()
            return "Error"
        try:
            ComPort.write_timeout = 1
            Log("Write known bad command:'test'" )
            testcommand = "test"
            ComPort.flushInput()  # flush input buffer, discarding all its contents
            ComPort.flushOutput()  # flush output buffer, aborting current output
            ComPort.write(testcommand.encode())
            ComPort.timeout = 1
            ComPort.write_timeout=0
            testresult = ComPort.readline()
            Log(" Received:'" + str(testresult) + "'")
            print("Success!")
            canvas.draw()
        except Exception as e:
            pollingFalse()
            Log("Err sending test msg to " + comportname + " Error was:" + str(e))
            messagebox.showinfo("Err sending msg to " + comportname, "Error was:" + str(e))

            ComPort.close()
            return "Error"

        labelcomport.config(text=comportname)
        if not (ComPort.isOpen()):
            messagebox.showinfo("Could not open " + comportname)
            pollingFalse()
            ComPort.close()
            return "Error"
    #ComPort.flushInput()  # flush input buffer, discarding all its contents
    #ComPort.flushOutput()  # flush output buffer, aborting current output
    retry = 0
    ComPort.timeout = 5
    result = ""
    labelcomport.config(bg="darkblue")
    canvas.draw()
    while retry <= 1:
        Log("WriteToCom:'" + str(command) + "'")
        try:
            ComPort.flushInput()  # flush input buffer, discarding all its contents
            ComPort.flushOutput()  # flush output buffer, aborting current output
            ComPort.write(command.encode())
        except Exception as e:
            Log(" Err sending data to comport. Error was:" + str(e))
            pollingFalse()
            messagebox.showerror("Err sending data to comport", "Error was:" + str(e))
            return "Error"
        commandtrim = command.replace("+", "").replace(" ","")
        result = ""
        result = ComPort.readline()
        Log(" ReadFromCom:" + str(result))
        resultstr = result.decode("utf-8").rstrip("\r\n")
        Log(" Decoded :" + str(resultstr))

        if not (resultstr.startswith(commandtrim)):
            Log(" Cmd not found at start of return. Looking for cmd '" + str(commandtrim) + "' Retry #:" + str(retry))
            if retry == 0:
                Log("   Retry/Sleep 1 second")
                time.sleep(1)
                retry = retry + 1
            else:
                Log("   change result to 'Error'")
                resultstr = "Error"
        else:
            resultstr = resultstr.replace(commandtrim, '', 1)
            retry = 100
    labelcomport.config(bg="white")
    canvas.draw()
    return resultstr

def procescommandresult(command,result):
    global currenttemptime
    global endsetpoint
    global test_endsetpoint
    global setpoints
    global testingstate
    #print (str(command))
    if result == "Error":
        Log("Skipping Processing Command Result:'Error'")
        return ""
    Log("Processing Command Result:'" + str(result) +"'")
    commandtrim = command
    #print ("Processcommandresult")
    #print (command)
    #print (result)
    if commandtrim == GET_REALTIME:
        if result == "testing":
            #print ("creating dummy data")
            result = "Running:index:Time:Avg:T1:T2:5:6:7:8:9:9:9"
            #state,endsetpoint,Roastinutes,tbeanrolling,mean,tbean1,tbean2,cfan,cheat1,cheat2
            parts = str(result).split(":")
            parts[0] = "Roasting" #testingstate
            if parts[0] != "Stopped":
                currenttemptime = currenttemptime + 1
                if currenttemptime > 300:
                    print ("dummy stop")
                    parts[0] = "Stopped"
            parts[1] = test_endsetpoint
            parts[2] = currenttemptime / 10
            parts[3] = (currenttemptime * 4) + random.randint(-5,5)
            parts[4] = (currenttemptime * 4) + random.randint(-50,50)
            parts[5] = (currenttemptime * 4) + random.randint(-50,50)
            parts[6] = "2.1"
            parts[7] = "1.0"
            parts[8] = "8.0"
            parts[12] = float(random.randint(1,10))/10
        elif result == "testing":
            parts = "Stopped: 5 :0.00: 56.60:59: 51:-1: 0.33:0.88: 0.99:0: 0:0.00:0".split(":")
        else:
            parts = str(result).split(":")
        if len(parts) < 12:
            Log("Incomplete " + GET_REALTIME + " Should be 12. Was:" + str(len(parts)))
            return "Error"
        endsetpoint = int(parts[1])
        if str(parts[1]) == str(5):
            End4or5_button.label.set_text("End@4")
        else:
            End4or5_button.label.set_text("End@5")

        if (float(parts[12]) > 1):
            parts[12] = 1.0
        if (float(parts[12]) < 0):
            parts[12] = 0.0

        statemsg = "State:" + str(parts[0]) + " sp:" + str(parts[1]) + " Roast Time:" + str(parts[2]) +  "  Remaining:"  + \
                   str("{0:.2f}".format(float(endminutes()) - float(parts[2])))
        labelState.config(text=statemsg)
        detailsmsg = "Fan: " + str(parts[7]) + "A  Coil1: " + str(parts[8]) + "A  Coil2: " + str(parts[9]) + "A  Duty:" + str(parts[12]) + "  err:" + str(parts[10]) + "  I:" + str(parts[11])
        labelStats.config(text=detailsmsg)
        msgEnd = "End sp:" + str(endsetpoint) + " Temp:" + str(endtemp()) + "F or " + str(endminutes()) + " minutes"
        labelEndPoint.config(text=msgEnd)
        PlaceSetPointAnnotation()
        if parts[0] == "Roasting":
            LastRunningTemp = float(parts[3])
            LastRunningMinutes = float(parts[2])
            labelCurrentTemp.config(text="Run Time:" + str(parts[2]) + " Temp:" + str(parts[3]))
        if parts[0] != "Stopped":
            yduty.append(float(parts[12]))
            #print (float(parts[12]))
            xduty.append(float(parts[2]))
            ytemp1.append(int(parts[4]))
            xtemp1.append(float(parts[2]))
            lineduty.set_xdata(xduty)
            lineduty.set_ydata(yduty)
            linetemp1.set_xdata(xtemp1)
            linetemp1.set_ydata(ytemp1)
            ytemp2.append(int(parts[5]))
            xtemp2.append(float(parts[2]))
            linetemp2.set_xdata(xtemp2)
            linetemp2.set_ydata(ytemp2)
            ytemp.append(float(parts[3]))
            xtemp.append(float(parts[2]))
            linetemp.set_xdata(xtemp)
            linetemp.set_ydata(ytemp)
        fig.canvas.draw()
    if (commandtrim == GET_PROFILE or commandtrim.startswith("+I") or commandtrim.startswith("+D")):
        global lineprofile
        if result == "testing":
            result = "0: 0:150!1: 3:380!2: 5:413!3: 13:433!4: 14:458!5: 16:461"
        if (result == "OK"):
            return "OK";
        profile = result.split("!")
        if len(profile) != 6:

            Log("Incomplete " + GET_PROFILE + " Should be 6.  Was:" + str(len(profile)))

            return "Error"
        #lineprofile.remove()

        xprofile.clear()
        yprofile.clear()
        xsetpoint.clear()
        ysetpoint.clear()
        setpoints.clear()
        #lineprofile, = axGraph.plot(xprofile, yprofile, 'r-')
        canvas.draw()
        #print (result)
        for i in range(0, len(profile)):
            #print ("start setpoint " + str(i))
            global linesetpoint
            #linesetpoint.remove()
            #linesetpoint, = axGraph.plot(xsetpoint, ysetpoint, 'ro')
            xy = profile[i].split(":")
            # 0 - is setpoint number, 1 is setpoint minute, 2 is setpoint temp
            xy[1] = int(xy[1].strip())
            xy[0] = int(xy[0].strip())
            setpoints.append(xy)
            xsetpoint.append(int(xy[1]))
            ysetpoint.append(int(xy[2]))
            linesetpoint.set_xdata(xsetpoint)
            linesetpoint.set_ydata(ysetpoint)
            if i < (len(profile) - 1):
                #print (str(i) + " of " + str(len(profile)))
                xyNext = profile[i + 1].split(":")
                dtime = float(xyNext[1]) - int(xy[1])
                dtemp = float(xyNext[2]) - int(xy[2])
                ratio = dtemp / dtime
                for j in range(int(xy[1]), int(xyNext[1])):
                    tm = int(xy[2]) + ((j - int(xy[1])) * ratio)
                    #print(str(j) + "  " + str(tm))
                    xprofile.append(float(j))
                    yprofile.append(float(tm))
                    lineprofile.set_xdata(xprofile)
                    lineprofile.set_ydata(yprofile)
            else:
                    #print(str(xy[1]) + "  " + str(xy[2]))
                    xprofile.append(float(xy[1]))
                    yprofile.append(float(xy[2]))
                    lineprofile.set_xdata(xprofile)
                    lineprofile.set_ydata(yprofile)
        # use any set_ function to change all the properties
        msgEnd = "End sp:" + str(endsetpoint) + " Temp:" + str(endtemp()) + "F or " + str(endminutes()) + " minutes"
       # print (endsetpoint)
        labelEndPoint.config(text=msgEnd)
        PlaceSetPointAnnotation()
        canvas.draw()
        return "OK"
    if commandtrim == GET_ACTIVERUN:
        #print ("in active run")
        if result == "testing":
            #activerun = "0.00:58!0.50:100!1.00:150!2.00:305!4.00:400!5.00:420".split("!")
            activerun = "".split("!")
            currenttemptime = 0
        if result == "":
            Log("No " + GET_ACTIVERUN + " data to plot")
            return "OK"
        else:
            activerun = result.split("!")
        yduty.clear()
        xduty.clear()
        ytemp.clear()
        xtemp.clear()
        xtemp1.clear()
        ytemp1.clear()
        xtemp2.clear()
        ytemp2.clear()
        xtempA.clear()
        ytempA.clear()
        canvas.draw()
        if (len(activerun) > 1 ):
            #print("GetActiveRunA")
            #print(result)
            for i in range(0, len(activerun)):
                #print("  GetActiveRunB" + str(i) + " " + str(activerun[i]))
                if str(activerun[i]).find(":") > 0:
                    xy = activerun[i].split(":")
                    ytempA.append(float(xy[1]))
                    xtempA.append(float(xy[0]))
                else:
                    print("skipping active run value  .. missing a :")
            fig.canvas.draw()
        else:
            Log("Incorrect " + GET_ACTIVERUN + " Did not contain any '!'")
        return "OK"
    return "OK"

def AddRunStats():
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    #textstr = '\n'.join((
    #    r'$\mu=%.2f$' % ("A", ),
    #    r'$\mathrm{median}=%.2f$' % ("B", ),
    #    r'$\sigma=%.2f$' % ("C", )))
    textstr = 'hello'
    axGraph.text(0.05, 0.95, textstr, transform=axGraph.transAxes, fontsize=14, verticalalignment='top', bbox=props)
    canvas.draw()

def GetSetpointDialoug():
    setpoint = simpledialog.askstring("Enter Setpoint", "Number 1-5:", parent=application_window)
    if "12345".find(setpoint) < 0 or setpoint == "":
        messagebox.showinfo("Invalid Setpoint", "You entered:'" + setpoint + "'  Should be 1,2,3,4 or 5")
        return
    return setpoint

def GetTempChangeDialoug():
    tempchangeraw = simpledialog.askstring("Input Temp Change", "Number (-9 to 9):", parent=application_window)
    if str(tempchangeraw).startswith("-"):
        tempchange = str(tempchangeraw)[1:2]
    else:
        tempchange = tempchangeraw
    if "123456789".find(tempchange) < 0 or not len(tempchange) == 1:
        messagebox.showinfo("Invalid amount", "You entered:'" + tempchangeraw + "'  Should be -9 to 9")
        return -1
    return int(tempchangeraw)

class ButtonClickAction(object):
    ind = 0
    def poll(self, event):
        self.ind += 1
        global Poll_button
        rr = Poll_button.label.get_text()
        if (rr == "Connect"):
            if submitadhoccommand(GET_PROFILE) != "OK":
                return
            if submitadhoccommand(GET_ACTIVERUN) != "OK":
                return
            print ("Starting polling...")
            time.sleep(1)
            timer = pollingTimer()
            timer.start(labeltimer)
            Poll_button.label.set_text("DisCon")
        else:
            #print ("turning off polling")
            global polling
            pollingFalse()
        canvas.draw()
        return
    def start(self, event):
        self.ind += 1
        global testingstate
        testingstate = "Running"
        submitadhoccommand(ACTION_START)
        return
    def end(self, event):
        self.ind += 1
        submitadhoccommand(ACTION_STOP)
        global testingstate
        testingstate = "Stopped"
    def fan(self, event):
        self.ind += 1
        submitadhoccommand(ACTION_FAN)
        global testingstate
        testingstate = "Fan"
        return
    def refresh(self, event):
        self.ind += 1
        submitadhoccommand(GET_PROFILE)
        submitadhoccommand(GET_ACTIVERUN)
    def ACTION_TIME_Root(self, event):
        self.ind += 1
        setpoint = GetSetpointDialoug()

        if setpoint == "":
            return

        minutesraw = simpledialog.askstring("Enter Minutes", "Number -1 or 1:", parent=application_window)
        if not (minutesraw == '-1' or minutesraw == '1'):
            messagebox.showinfo("Invalid amount", "You entered:'" + minutesraw + "'  Should be -1 or 1")
            return

        if str(minutesraw).startswith("-"):
            action = ACTION_D_TIME + setpoint
        else:
            action = ACTION_I_TIME + setpoint

        submitadhoccommand(action)
    def Integral (self, event):
        self.ind += 1

        intchange = GetTempChangeDialoug()

        if intchange < 0:
            action = ACTION_D + "I" + str(abs(intchange))
        else:
            action = ACTION_I + "I" + str(intchange)

        submitadhoccommand(action)
    def ACTION_ALL_ROOT (self, event):
        self.ind += 1

        tempchange = GetTempChangeDialoug()

        if tempchange < 0:
            action = ACTION_D + "A" + str(abs(tempchange))
        else:
            action = ACTION_I + "A" + str(tempchange)

        submitadhoccommand(action)
    def ACTION_One_Root (self, event):
        self.ind += 1

        setpoint = simpledialog.askstring("Enter Setpoint", "Number 1-5:", parent=application_window)
        if "12345".find(setpoint) < 0 or setpoint == "":
            messagebox.showinfo("Invalid Setpoint", "You entered:'" + setpoint + "'  Should be 1,2,3,4 or 5")
            return

        tempchange = GetTempChangeDialoug()

        if tempchange < 0:
            action = ACTION_D + setpoint + str(abs(tempchange))
        else:
            action = ACTION_I + setpoint + str(tempchange)

        submitadhoccommand(action)
    def End4or5(self,event):
        self.ind += 1
        global test_endsetpoint
        rr = End4or5_button.label.get_text()
        if rr == "End@4":
            test_endsetpoint = 4
            End4or5_button.label.set_text("End@5")

        else:
            End4or5_button.label.set_text("End@4")
            test_endsetpoint = 5
        submitadhoccommand(ACTION_TOGGLE_ROAST)
        canvas.draw()
    def Zoom (self, event):
        self.ind += 1
        global zoomhoroffset
        global annotateendpoint
        rr = Z_button.label.get_text()
        if rr == "Z+":
            axGraph.set_ylim(int(setpoints[0][2]), int(endtemp()) + 50)
            axGraph.set_xlim(float(setpoints[0][1]), (endminutes() + 1))
            Z_button.label.set_text("Z++")
            zoomhoroffset = 9
            annotateendpoint.set_y(float(setpoints[endsetpoint][2]) + zoomhoroffset)
        elif rr == "Z++":
            axGraph.set_ylim(firsttemp(), int(endtemp()) + 10)
            axGraph.set_xlim(firstminutes(), (endminutes() + 1))
            Z_button.label.set_text("Z-")
            zoomhoroffset = 2
            annotateendpoint.set_y(float(setpoints[endsetpoint][2]) + zoomhoroffset)

        else:
            zoomhoroffset = 10

            axGraph.set_ylim(0, int(maxtemp() + 50))
            axGraph.set_xlim(0, maxminutes() + 1)
            Z_button.label.set_text("Z+")

            annotateendpoint.set_y(float(setpoints[endsetpoint][2]) + zoomhoroffset)

        canvas.draw()
    def ComPort (self, event):
        self.ind += 1
        comport = simpledialog.askstring("Enter Comport", "example COM6", parent=application_window)
        if comport != "":
            COMPORT_button.label.set_text(comport)
        canvas.draw()
    def AnyCmd (self, event):
        self.ind += 1
        command = simpledialog.askstring("Enter command", "+[I,D][I,G,S][1-9]\nRR", parent=application_window)
        r = sendcommandtocomport(command)
        messagebox.showinfo("",r)
    def Save (self, event):
        self.ind += 1
        bean = simpledialog.askstring("Bean Name", "Bean name", parent=application_window)
        t = datetime.datetime.now()
        line = str(bean) + "," + str(t.month) + "-" + str(t.day) + "-" + str(t.year) + "," + str(t.hour) + ":" + str(t.minute) + "," + str(LastRunningMinutes) + "," + str(LastRunningTemp) + "," + str(endsetpoint)

        for sp in setpoints:
            line = line + "," + str(sp[0]) + ":" + str(sp[1]) + ":" + str(sp[2])

        print(line)
        with open("roasthistory.csv", "a") as myfile:
            myfile.write(line + '\n')
    def CloseCom (self, event):
        self.ind += 1
        messagebox.showinfo("Closing comport", closecomport())
print ("Logfilename:" + LogFileName)
Log("   ")
Log("*******************************STARTUP******************************************")
plt.ion()
axis_color = 'black'
# fig = plt.figure()
fig = Figure(figsize=(8, 5), dpi=100)
xprofile = []
yprofile = []
xprofileT = []
yprofileT = []

xtemp = []
ytemp = []
xtemp1 = []
ytemp1 = []
xtemp2 = []
ytemp2 = []
xtempA = []
ytempA = []

xduty = []
yduty = []

xsetpoint = []
ysetpoint = []
xsetpointT = []
ysetpointT = []

axGraph = fig.add_subplot(111)
axGraph.grid()
axGraph.set_ylim(0, 600)
axGraph.set_xlim(0, 17)
axGraph.minorticks_on()
axGraph.grid(which='major', linestyle='-', linewidth='1', color='grey')
axGraph.grid(which='minor', alpha=1.0, linestyle='-', linewidth='0.3', color='grey')
axGraph.tick_params(axis='y', which='minor', labelsize='x-small')
axGraph.yaxis.set_minor_formatter(FormatStrFormatter("%.0f"))


minorLocator = AutoMinorLocator(4)
axGraph.yaxis.set_minor_locator(minorLocator)

axGraph2 = axGraph.twinx()
axGraph2.set_ylim(-.5, 5)

lineprofile, = axGraph.plot(xprofile, yprofile, 'r-',linewidth=2.00)
linetemp2, = axGraph.plot(xtemp2, ytemp2, 'c-', linewidth=.5)
linetemp1, = axGraph.plot(xtemp1, ytemp1, 'm-', linewidth=.5)
linetemp, = axGraph.plot(xtemp, ytemp, 'b-', linewidth=1.25)
linetempA, = axGraph.plot(xtempA, ytempA, 'y-', linewidth=1.25)
linesetpoint, = axGraph.plot(xsetpoint, ysetpoint, 'ro')
annotateendpoint = axGraph.annotate(xy=(6, 400), s="SP:500", fontsize='8')
lineduty, = axGraph2.plot(xduty, yduty, 'g-', linewidth=1.0)
axGraph2.axhline(y=0, linewidth=1, linestyle='--', color='g')
axGraph2.axhline(y=0.5, linewidth=1, linestyle='--', color='g')
axGraph2.axhline(y=1, linewidth=1, linestyle='--', color='g')

#annotateendpoint.set_bbox(dict(facecolor = 'white', alpha=0.6,edgecolor='white'))
#annotateendpoint.set_bbox(dict(facecolor='red', alpha=0.5, edgecolor='red'))

canvas = FigureCanvasTkAgg(fig, master=application_window)
canvas.draw()
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
labels = [item.get_text() for item in axGraph2.get_yticklabels()]

for i in range(3, len(labels)):
    labels[i] = ''


axGraph2.set_yticklabels(labels)
for ticklabel in axGraph2.get_yticklabels():
    print (ticklabel.get_text())
    ticklabel.set_text('A')

#label = axGraph2.yaxis.get_major_ticks()[2].label
#label.set_text('A')
#canvas.draw()
lblHO = .02
lblH = .04

#far left top
labeltimer = tk.Label(application_window, text="0 s", font="Arial 8", width=8)
labeltimer.place(relx=.00, y=0)
labelcomport = tk.Label(application_window, text="port?", font="Arial 10", width=6)
labelcomport.place(relx=.00, y=20)



labelState = tk.Label(application_window ,text="Stopped", font="Arial 10", width=50,height = 1,justify="left",anchor="nw")
labelState.place(relx=.07, rely=(lblHO + (lblH * 1)))
labelStats = tk.Label(application_window, text="   ", font="Arial 10", width=45,height = 1,justify="left",anchor="nw")
labelStats.place(relx=.07, rely=(lblHO + (lblH * 2)))
labelCurrentTemp = tk.Label(application_window, text="000 F", font="Arial 10", width=20,height = 1,justify="left",anchor="nw")
labelCurrentTemp.place(relx=.07, rely=(lblHO + (lblH * 3)))
labelCommands = tk.Label(application_window, text="Stopped", font="Arial 10", width=15,height = 1,justify="left",anchor="nw")
labelCommands.place(relx=.07, rely=(lblHO + (lblH * 4)))


labelEndPoint = tk.Label(application_window, text="   ", font="Arial 10", width=30,height = 1,justify="left",anchor="nw")
labelEndPoint.place(relx=.6, rely=(lblHO + (lblH * 1)))


fig.tight_layout(rect=(0,.00,1,.9))


callback = ButtonClickAction()
# horizonal buttons
hboffset = .02
hbheight = .05
hbwidth = .07
hbwidthT = hbwidth * .97

Poll_button = Button(fig.add_axes([hboffset + (hbwidth * 1), 1-hbheight, hbwidthT, hbheight]), 'Connect', color='yellow')
Poll_button.on_clicked(callback.poll)
Start_button = Button(fig.add_axes([hboffset + (hbwidth * 2), 1-hbheight, hbwidthT, hbheight]), 'Start', color='pink')
Start_button.on_clicked(callback.start)
End_button = Button(fig.add_axes([hboffset + (hbwidth * 3), 1-hbheight, hbwidthT, hbheight]), 'Off', color='pink')
End_button.on_clicked(callback.end)
Fan_button = Button(fig.add_axes([hboffset + (hbwidth * 4), 1-hbheight, hbwidthT, hbheight]), 'Fan', color='pink')
Fan_button.on_clicked(callback.fan)
Ref_button = Button(fig.add_axes([hboffset + (hbwidth * 5), 1-hbheight, hbwidthT, hbheight]), 'Refresh', color='pink')
Ref_button.on_clicked(callback.refresh)
Z_button = Button(fig.add_axes([hboffset + (hbwidth * 6), 1-hbheight, hbwidthT, hbheight]), 'Z+')
Z_button.on_clicked(callback.Zoom)
One_button = Button(fig.add_axes([hboffset + (hbwidth * 7), 1-hbheight, hbwidthT, hbheight]), '+-SP', color='aqua')
One_button.on_clicked(callback.ACTION_One_Root)
All_button = Button(fig.add_axes([hboffset + (hbwidth * 8), 1-hbheight, hbwidthT, hbheight]), '+-4sp', color='aqua')
All_button.on_clicked(callback.ACTION_ALL_ROOT)
T_button = Button(fig.add_axes([hboffset + (hbwidth * 9), 1-hbheight, hbwidthT, hbheight]), '+-Tsp', color='aqua')
T_button.on_clicked(callback.ACTION_TIME_Root)
End4or5_button = Button(fig.add_axes([hboffset + (hbwidth * 10), 1-hbheight, hbwidthT, hbheight]), 'End@5', color='aqua')
End4or5_button.on_clicked(callback.End4or5)
testcommand_button = Button(fig.add_axes([hboffset + (hbwidth * 11), 1-hbheight, hbwidthT, hbheight]), 'cmd')
testcommand_button.on_clicked(callback.AnyCmd)
Save_button = Button(fig.add_axes([hboffset + (hbwidth * 12), 1-hbheight, hbwidthT, hbheight]), 'Save')
Save_button.on_clicked(callback.Save)
CloseComport_button = Button(fig.add_axes([hboffset + (hbwidth * 13), 1-hbheight, hbwidthT, hbheight]), 'CCom')
CloseComport_button.on_clicked(callback.CloseCom)





#vertical buttons
vboffset = .08
vbheight = .075
vbwidth = .05
#A_button = Button(fig.add_axes([.999 - vbwidth, vboffset + (vbheight * 0), vbwidth, vbheight]), '+-All', color="yellow", hovercolor="Yellow")
#A_button.on_clicked(callback.ACTION_ALL_ROOT)
#One_button = Button(fig.add_axes([.999 - vbwidth, vboffset + (vbheight * 1), vbwidth, vbheight]), '+-One', color="yellow", hovercolor="Yellow")
#One_button.on_clicked(callback.ACTION_One_Root)
#T_button = Button(fig.add_axes([.999 - vbwidth, vboffset + (vbheight * 2), vbwidth, vbheight]), '+-Time', color="yellow", hovercolor="Yellow")
#T_button.on_clicked(callback.ACTION_TIME_Root)



tk.mainloop()





