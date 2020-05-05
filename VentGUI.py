# Authors: Michael Madden and Atif Shazad.
# Developed for the Galway Vent Share project: www.galwayventshare.com


from PyQt5 import Qt, QtWidgets, QtCore, uic
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPalette, QIcon, QPixmap, QRegion

import pyqtgraph as pg
import sys  # We need sys so that we can pass argv to QApplication
from random import uniform
from numpy import array
import math

import serial


# =========== Overall settings and utility functions =============

# Some important overall settings
REALSENSORS=False      # if True, read data from sensors; if false, generate random numbers
interval = 50          # update interval 50ms
graphPoints = 100      # how many points to display on the graph
movingWindowPpeak = 20 # Size of the window for estimation of Ppeak
movingWindowPEEP = 5   # size of moving window for PEEP display
movingWindowVte = 5    # size of moving window for Vte display

ADDRESS = 0x01        # Address for sensor comms


# Simple utility function to round a float to a specified number of digits (defaults to 2) and convert to string
def floatToStr(value, numDigits=2):
    v = round(value, numDigits) # round to nearest value
    if (numDigits==0):
        v = int(v)  # cast to int to avoid trailing ".0" in string which we don't want
    return str(v)

# Simple average function that returns 0 if array is empty
def avg(arr):
    return 0 if (len(arr) == 0) else sum(arr)/len(arr)



# =========== Code for communication with sensors =============

if REALSENSORS:
    # The serial port access crashes in Windows - don't access it if simulating data
    ser = serial.Serial(
             port = '/dev/ttyUSB0',          #number of device, numbering starts at zero.
             baudrate=115200,            #baudrate
             bytesize=serial.EIGHTBITS,  #number of databits
             parity=serial.PARITY_NONE,  #enable parity checking
             stopbits=serial.STOPBITS_ONE,  #number of stopbits
             timeout=1,                  #set a timeout value (example only because reset takes longer)
             xonxoff=0,                  #disable software flow control
             rtscts=0,                   #disable RTS/CTS flow control
         )


def get_sw_version(address): # Get software version of cable
    command = bytearray(([address] + [0x01] + [0x00] + [0xB2]))
    ser.write(command)
    data = ser.read(7)
    return data.hex()

def get_hw_version(address): # Default hardware version
    command = bytearray(([address] + [0x02] + [0x00] + [0x9F]))
    ser.write(command)
    data = ser.read(6)
    return data.hex()

def test_command(address): # Default test command
    command = bytearray(([address] + [0x05] + [0x00] + [0x31]))
    ser.write(command)
    data = ser.read(6)
    return data.hex()

def get_pressure(address): # Get pressure value from pressure sensor
    command = bytearray(([address] + [0x07] + [0x00] + [0xE8]))
    ser.write(command)
    data = ser.read(6)
    reverse_data = data[::-1]
    pres = reverse_data[1:3]
    Dp = int(pres.hex(),16)
    P = 1.01972*(((Dp-1638)/32.7675)-200) # Apply scaling factor and convert to CM H2O
    return P

def hard_reset_board(address): # Hard reset of comm board on Nicolay cable
    command = bytearray(([address] + [0x0B] + [0x00] + [0x5C]))
    ser.write(command)
    data = ser.read(4);
    return data.hex()

def hard_reset_sensor(address): # Hard reset of sensors
    command = bytearray(([address] + [0x0C] + [0x00] + [0xF2]))
    ser.write(command)
    data = ser.read(4)
    return data.hex()

def soft_reset_sensor(address): # Soft reset of sensors
    command = bytearray(([address] + [0x0D] + [0x00] + [0x06]))
    ser.write(command)
    data = ser.read(4)
    return data.hex()

def start_flowsensor(address): # intialise flow sensor
    command = bytearray(([address] + [0x0E] + [0x00] + [0x2B]))
    ser.write(command)
    data = ser.read(4)
    if(command==data):
        return True
    else: return False

def get_flow(address): # Get flow value from flow sensor
    command = bytearray(([address] + [0x10] + [0x00] + [0x28]))
    ser.write(command)
    data = ser.read(8)
    reverse_data = data[::-1]
    flow = reverse_data[1:5]
    F = int(flow.hex(),16) # convert to decimal
    #compute two's complement (convert unsigned data to signed value)
    if F >= 2**31:  # 2**31 = 2,147,483,648
       F -= 2**32     # 2**32 = 4,294,967,296
    # convert flow to litres per minute
    F = F/1000
    return F

def get_raw_flow(address): # Get raw flow value from flow sensor
    command = bytearray(([address] + [0x11] + [0x00] + [0xDC]))
    ser.write(command)
    data = ser.read(6)
    return data.hex()

def get_flowsensor_scale(address): # Get scaling factor from flow sensor
    command = bytearray(([address] + [0x12] + [0x00] + [0xF1]))
    ser.write(command)
    data = ser.read(6)
    return data.hex()

def get_flowsensor_offset(address): # Get offset factor from flow sensor
    command = bytearray(([address] + [0x13] + [0x00] + [0x05]))
    ser.write(command)
    data = ser.read(6)
    return data.hex()

def get_heater_state(address): # Get current status of heater
    command = bytearray(([address] + [0x14] + [0x00] + [0xAB]))
    ser.write(command)
    data = ser.read(5)
    return data.hex()

def get_heater_power(address): # Get current power of heater [in percentage]
    command = bytearray(([address] + [0x15] + [0x00] + [0x5F]))
    ser.write(command)
    data = ser.read(5)
    return data.hex()

def set_heater_state(address, state): # Set current status of heater [0: OFF; 1: ON]
    if(state==0): # set heater off
       command = bytearray(([address] + [0x14] + [0x01] + [0x00] + [0xE2]))
       ser.write(command)
       data = ser.read(5)
    else: # set heater on
       command = bytearray(([address] + [0x14] + [0x01] + [0x01] + [0xD3]))
       ser.write(command)
       data = ser.read(5)

    return data.hex()

def get_temperature(address): # Get current temperatue [in Celcius]
    command = bytearray(([address] + [0x16] + [0x00] + [0x72]))
    ser.write(command)
    data = ser.read(6)
    reverse_data = data[::-1]
    temp = reverse_data[1:3]
    return temp.hex()

def get_temperature_scale(address): # Get current scaling factor for temperature
    command = bytearray(([address] + [0x18] + [0x00] + [0x1F]))
    ser.write(command)
    data = ser.read(6)
    return data.hex()

def get_temperature_offset(address): # Get current offset factor for temperature
    command = bytearray(([address] + [0x19] + [0x00] + [0xEB]))
    ser.write(command)
    data = ser.read(6)
    return data.hex()

def force_temperature_update(address): # Force update of temperature on board calculation
    command = bytearray(([address] + [0x1B] + [0x00] + [0x32]))
    ser.write(command)
    data = ser.read(6)
    reverse_data = data[::-1]
    temp = reverse_data[1:3]
    return temp.hex()


# ============== Main Vent GUI Window =================

class MainWindow(QtWidgets.QMainWindow):
    # Define signals that are emitted when there is new data from the sensors
    newPress = pyqtSignal(float)
    newFlow = pyqtSignal(float)
    newPpeak = pyqtSignal(float)
    newVte = pyqtSignal(float)
    newPEEP = pyqtSignal(float)
    # Emit data rounded to nearest int - needed for alarms window
    newPpeakInt = pyqtSignal(int)
    newVteInt = pyqtSignal(int)
    newPEEPInt = pyqtSignal(int)

    # Colour settings
    alarmStyle = ".QFrame {background-color: #ff0000; border: 4px solid white;} .QLabel {color: white;}"
    normalStyle = ".QFrame {background-color: #2a66ff; border: 0px} .QLabel {color: white;}"

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        #Load the UI Page
        uic.loadUi('mainwindow.ui', self)
        self.showFullScreen();

        # Set up button icons: logo, home screen and alarm screen
        self.gvsLogo.setPixmap(QPixmap('images/galwayventshare.jpg'))
        self.btnHomeScreen.setIcon(QIcon('images/homescreen.png'))
        self.btnHomeScreen.setIconSize(QtCore.QSize(50,50))
        self.btnAlarmScreen.setIcon(QIcon('images/alarmscreennot.png'))
        self.btnAlarmScreen.setIconSize(QtCore.QSize(50,50))

        # Set up alarm icons
        self.iconPPeakAlarm.setPixmap(QPixmap('images/alarmnotset.png'))
        self.iconVteAlarm.setPixmap(QPixmap('images/alarmnotset.png'))
        self.iconPEEPAlarm.setPixmap(QPixmap('images/alarmnotset.png'))

        # Set up a timer to get new data at fixed intervals
        self.timer = QtCore.QTimer()
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.updateData)
        self.timer.start()

        # Pen that defines the line style for the graphs
        self.linePen = pg.mkPen(color='g', width=3)

        # Initialise graphs
        self.timeData = array(range(graphPoints))*interval/1000 # time array is values in seconds
        self.pressData = [0] * len(self.timeData) # make a list of zeros the same length as the timeData list
        self.flowData = [0] * len(self.timeData) # make a list of zeros the same length as the timeData list
        self.setupPressurePlot(self.timeData, self.pressData)
        self.setupFlowPlot(self.timeData, self.flowData)

        # Alarm settings
        self.pPeakMaxAlarm = 45
        self.vteMaxAlarm = 1000
        self.vteMinAlarm = 0
        self.PEEPMaxAlarm = 25
        self.pPeakAlarmSet = False
        self.vteAlarmSet = False
        self.PEEPAlarmSet = False

        # Some additional variables to calculate stats
        # Note - moved some of these from being class variables to instance variables
        self.timeCount = 0
        self.prevFlow = 0
        self.prevPress = 0
        self.instV = 0
        self.vteTimer = 0
        self.insp = bool(False)
        self.Exp = bool(False)
        self.posPeaks = []
        self.PEEP = []
        self.expV = []
        self.xSim = 0

        # Connect up signals to slots - custom signals
        self.newPress.connect(self.plotPressure)
        self.newFlow.connect(self.plotFlow)
        self.newPpeak.connect(self.setPpeak)
        self.newVte.connect(self.setVte)
        self.newPEEP.connect(self.setPEEP)

        # Connect up signals to slots - standard UI signals
        self.btnAlarmScreen.clicked.connect(self.showAlarmSettings)

    def setupPressurePlot(self, hour, press):
        self.pressureLine = self.pressGraphWidget.plot(hour, press, pen=self.linePen)
        self.pressGraphWidget.setEnabled(False) # Disable all interaction - want output-only graph display
        self.pressGraphWidget.showGrid(x=False, y=True) # Horizontal grid lines including at y=0

    def setupFlowPlot(self, hour, flow):
        self.flowLine = self.flowGraphWidget.plot(hour, flow, pen=self.linePen)
        self.flowGraphWidget.setEnabled(False) # Disable all interaction - want output-only graph display
        self.flowGraphWidget.showGrid(x=False, y=True) # Horizontal grid lines including at y=0


    def updateData(self):
        if REALSENSORS:
            # Real mode, not simulation mode: read data from sensors
            flow = get_flow(ADDRESS)
            pressure = get_pressure(ADDRESS)
        else:
            # Simulation mode: use random numbers
            # Using cosine waves with random noise and period 2pi over 100 points
            flow = 20 * math.cos(self.xSim / 50 * math.pi) - 10 + uniform(-3,3)
            pressure = 5 * math.cos(self.xSim / 50 * math.pi) + 15 + uniform(-6,6)
            self.xSim = 0 if (self.xSim >= 99) else self.xSim + 1 # wrap around 100 -> 0

        # PEEP estimation
        if(flow>=0 and self.prevFlow<0): # Detect zero crossing: negative to positive change
            if(self.vteTimer>20): # Ignore if a cycle is too small
               if len(self.PEEP) == movingWindowPEEP:
                   self.PEEP = self.PEEP[1:] # disard old value from moving window
               self.PEEP.append(self.prevPress) # add new value
               if len(self.expV) == movingWindowVte:
                   self.expV = self.expV[1:] # disard old value from moving window
               self.expV.append(2286*(self.instV/(self.vteTimer*50))) # add new tidal volume

            self.instV = 0
            self.vteTimer = 0
            self.insp = True
            self.Exp = False

        if(flow<0 and self.prevFlow>=0): # Detect zero crossing: Postive to negative change
            self.insp = False
            self.Exp = True

        if(self.Exp == True): # for estimation of tidal volume
            self.instV += -1*flow
            self.vteTimer += 1

        self.prevPress = pressure
        self.prevFlow = flow

        # Emit messages to update pressure and flow graphs
        self.newPress.emit(pressure)
        self.newFlow.emit(flow)

        # Record last [movingWindowPpeak] peak pressure values for moving average
        if len(self.posPeaks) == movingWindowPpeak:
            self.posPeaks = self.posPeaks[1:]
        self.posPeaks.append(max(self.pressData))

        # Emit messages (float and rounded to nearest int) to update stats on every 5th call (250ms)
        self.timeCount += 1
        if(self.timeCount>5):
            e = avg(self.posPeaks)
            self.newPpeak.emit(e)
            self.newPpeakInt.emit(round(e))
            e = avg(self.expV)
            self.newVte.emit(e)
            self.newVteInt.emit(round(e))
            e = avg(self.PEEP)
            self.newPEEP.emit(e)
            self.newPEEPInt.emit(round(e))
            self.timeCount = 0

    # Update the pressure graph (slot for handling newPress signal)
    @pyqtSlot(float)
    def plotPressure(self, pressure):
        self.pressData = self.pressData[1:]  # Remove the first
        self.pressData.append(pressure)  # Add the latest pressure value
        self.pressureLine.setData(self.timeData, self.pressData)  # Update the graph with the new data.

    # Update the flow graph (slot for handling newFlow signal)
    @pyqtSlot(float)
    def plotFlow(self, flow):
        self.flowData = self.flowData[1:]  # Remove the first
        self.flowData.append(flow)  # Add the latest flow value
        self.flowLine.setData(self.timeData, self.flowData)  # Update the graph with the new data.

    # Change Ppeak value (slot for handling newPpeak signal)
    @pyqtSlot(float)
    def setPpeak(self, value):
        if self.pPeakAlarmSet:
            self.valPpeak.setText(floatToStr(value,1))
            if value > self.pPeakMaxAlarm:
                self.framePpeak.setStyleSheet(MainWindow.alarmStyle)
                self.iconPPeakAlarm.setPixmap(QPixmap('images/alarmon.png'))
            else:
                self.framePpeak.setStyleSheet(MainWindow.normalStyle)
                self.iconPPeakAlarm.setPixmap(QPixmap('images/alarmset.png'))
        else:
            self.valPpeak.setText("--")


    # Change Vte value (slot for handling newVte signal)
    @pyqtSlot(float)
    def setVte(self, value):
        self.valVte.setText(floatToStr(value,0))
        if self.vteAlarmSet:
            self.valVte.setText(floatToStr(value,0))
            if value < self.vteMinAlarm or value > self.vteMaxAlarm:
                self.frameVte.setStyleSheet(MainWindow.alarmStyle)
                self.iconVteAlarm.setPixmap(QPixmap('images/alarmon.png'))
            else:
                self.frameVte.setStyleSheet(MainWindow.normalStyle)
                self.iconVteAlarm.setPixmap(QPixmap('images/alarmset.png'))
        else:
            self.valVte.setText("---")

    # Change PEEP value (slot for handling newPEEP signal)
    @pyqtSlot(float)
    def setPEEP(self, value):
        self.valPeep.setText(floatToStr(value,1))
        if self.PEEPAlarmSet:
            self.valPeep.setText(floatToStr(value,1))
            if value > self.PEEPMaxAlarm:
                self.framePEEP.setStyleSheet(MainWindow.alarmStyle)
                self.iconPEEPAlarm.setPixmap(QPixmap('images/alarmon.png'))
            else:
                self.framePEEP.setStyleSheet(MainWindow.normalStyle)
                self.iconPEEPAlarm.setPixmap(QPixmap('images/alarmset.png'))
        else:
            self.valPeep.setText("--")

    # Quit out of the app by pressing ESC key
    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()

    # Open the alarm settings screen
    def showAlarmSettings(self):
        alarmSettings = AlarmSettings(self)
        alarmSettings.setGeometry(0,0,800,480) # Ensure initial position is 0,0
        alarmSettings.exec_()




# ============== Alarm Settings Window =================

class AlarmSettings(QtWidgets.QDialog):

    # Design settings
    barStyle = "QProgressBar { background-color: black; border: 0px solid grey; border-radius: 0px; text-align: center; } QProgressBar::chunk {background-color: white; height: 1px;}"
    whiteButtonStyle = "QPushButton { background-color: white; border: 3px solid white; border-radius: 10px;}"
    sliderMaxNotSetStyle = "QSlider::groove:vertical { background: transparent; width: 0px; margin: 0px -22px;} QSlider::handle:vertical {image: url(images/maxhollow.png); height: 30px;}"
    sliderMaxSetStyle = "QSlider::groove:vertical { background: transparent; width: 0px; margin: 0px -22px;} QSlider::handle:vertical {image: url(images/maxfilled.png); height: 30px;}"
    # NOTE for testing of slider masks, changing background to a visible colour
    sliderMinNotSetStyle = "QSlider::groove:vertical { background: red; width: 3px; margin: 0px -22px;} QSlider::handle:vertical {image: url(images/minhollow.png); height: 30px;}"
    sliderMinSetStyle = "QSlider::groove:vertical { background: orange; width: 3px; margin: 0px -22px;} QSlider::handle:vertical {image: url(images/minfilled.png); height: 30px;}"

    def __init__(self, parent):
        super().__init__()
        self.mainWin = parent

        #Load the UI Page
        uic.loadUi('alarmsettings.ui', self)
        self.showFullScreen();

        # Flags for when alarm settings are changed
        self.pPeakChanged = False
        self.PEEPChanged = False
        self.vteMinChanged = False
        self.vteMaxChanged = False

        # Set up button icons: confirm and cancel with white backgrounds
        self.btnConfirm.setIcon(QIcon('images/tick.png'))
        self.btnConfirm.setIconSize(QtCore.QSize(100,50))
        self.btnConfirm.setStyleSheet(AlarmSettings.whiteButtonStyle)
        self.btnConfirm.setEnabled(False)
        self.btnCancel.setIcon(QIcon('images/x.png'))
        self.btnCancel.setIconSize(QtCore.QSize(50,50))
        self.btnCancel.setStyleSheet(AlarmSettings.whiteButtonStyle)
        self.btnCancel.setEnabled(False)

        # Set up button icons: logo, home screen and alarm screen
        self.gvsLogo.setPixmap(QPixmap('images/galwayventshare.jpg'))
        self.btnHomeScreen.setIcon(QIcon('images/homescreennot.png'))
        self.btnHomeScreen.setIconSize(QtCore.QSize(50,50))
        self.btnAlarmScreen.setIcon(QIcon('images/alarmscreen.png'))
        self.btnAlarmScreen.setIconSize(QtCore.QSize(50,50))

        # Button signals and slots
        # Note that btnAlarmScreen does nothing as we are on that screen already

        # When Confirm button is pressed, set the alarm limits for the main window
        self.btnConfirm.clicked.connect(self.updateAlarms)
        # When Cancel button is pressed, reset alarm limits back to those from main window
        self.btnCancel.clicked.connect(self.resetAlarms)
        # When Home button is pressed, close this dialog without updating data first
        self.btnHomeScreen.clicked.connect(self.reject)

        # Configure the vertical bars and join sensor values to them
        # pPeak bar
        self.pPeakBar.setStyleSheet(AlarmSettings.barStyle)
        self.pPeakBar.setMinimum(0);
        self.pPeakBar.setMaximum(45);
        self.mainWin.newPpeakInt.connect(self.pPeakBar.setValue)
        # Vte bar
        self.vteBar.setStyleSheet(AlarmSettings.barStyle)
        self.vteBar.setMinimum(0);
        self.vteBar.setMaximum(1000);
        self.mainWin.newVteInt.connect(self.vteBar.setValue)
        # PEEP bar
        self.PEEPBar.setStyleSheet(AlarmSettings.barStyle)
        self.PEEPBar.setMinimum(0);
        self.PEEPBar.setMaximum(25);
        self.mainWin.newPEEPInt.connect(self.PEEPBar.setValue)

        # Set up pPeak slider
        self.pPeakSlider.setMinimum(self.pPeakBar.minimum())
        self.pPeakSlider.setMaximum(self.pPeakBar.maximum())
        self.pPeakSlider.setSingleStep(1)
        self.pPeakSlider.valueChanged.connect(self.changePPeak) # slot to update alarm flags and data
        # Make the label that accompanies this slider transparent for mouse events
        self.lblPPeakMax.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        # Set up PEEP slider
        self.PEEPSlider.setMinimum(self.PEEPBar.minimum())
        self.PEEPSlider.setMaximum(self.PEEPBar.maximum())
        self.PEEPSlider.setSingleStep(1)
        self.PEEPSlider.valueChanged.connect(self.changePEEP) # slot to update alarm flags and data
        # Make the label that accompanies this slider transparent for mouse events
        self.lblPEEPMax.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        # Set up Vte Min slider
        # NOTE: I am not allowing Min and Max sliders to overlap, as they interfere with mouse events of each other
        vteCrossPoint = 500
        self.vteMinSlider.setMinimum(self.vteBar.minimum())
        self.vteMinSlider.setMaximum(vteCrossPoint)
        self.vteMinSlider.setValue(20) # give it a non-zero default value so that valueChanged will be triggered correctly
        self.vteMinSlider.setSingleStep(5)
        self.vteMinSlider.valueChanged.connect(self.changeVteMin) # slot to update alarm flags and data
        # Make the label that accompanies this slider transparent for mouse events
        self.lblVteMin.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        # Set up Vte Max slider
        self.vteMaxSlider.setMinimum(vteCrossPoint)
        self.vteMaxSlider.setMaximum(self.vteBar.maximum())
        self.vteMaxSlider.setSingleStep(5)
        self.vteMaxSlider.valueChanged.connect(self.changeVteMax) # slot to update alarm flags and data
        # Make the label that accompanies this slider transparent for mouse events
        self.lblVteMax.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        # Now that the controls are configured, set initial alarm values from main window
        self.resetAlarms()


    # When a pPeak alarm setting is changed, this slot responds and updates the appropriate flag
    @pyqtSlot(int)
    def changePPeak(self, newval):
        # If this is the first time the value has been changed
        if not self.pPeakChanged:
            self.pPeakChanged = True
            self.pPeakSlider.setStyleSheet(AlarmSettings.sliderMaxSetStyle)
            self.lblPPeakMax.setStyleSheet("QLabel {color: #2a66ff;}") # label becomes blue on white background
            self.btnCancel.setEnabled(True)
            self.btnConfirm.setEnabled(True)
        # Adjust acompanying label
        self.lblPPeakMax.setText(floatToStr(newval,0))
        ypos = AlarmSettings.pixelPosFromValue(55, 355, self.pPeakSlider.minimum(), self.pPeakSlider.maximum(), self.pPeakSlider.value())
        self.lblPPeakMax.setGeometry(255,ypos,40,20)

    # When a PEEP alarm setting is changed, this slot responds and updates the appropriate flag
    @pyqtSlot(int)
    def changePEEP(self, newval):
        # If this is the first time the value has been changed
        if not self.PEEPChanged:
            self.PEEPChanged = True
            self.PEEPSlider.setStyleSheet(AlarmSettings.sliderMaxSetStyle)
            self.lblPEEPMax.setStyleSheet("QLabel {color: #2a66ff;}") # label becomes blue on white background
            self.btnCancel.setEnabled(True)
            self.btnConfirm.setEnabled(True)
        # Adjust acompanying label
        self.lblPEEPMax.setText(floatToStr(newval,0))
        ypos = AlarmSettings.pixelPosFromValue(55, 355, self.PEEPSlider.minimum(), self.PEEPSlider.maximum(), self.PEEPSlider.value())
        self.lblPEEPMax.setGeometry(670,ypos,40,20)

    # When the VteMin alarm setting is changed, this slot responds and updates the appropriate flag
    @pyqtSlot(int)
    def changeVteMin(self, newval):
        # If this is the first time the value has been changed
        if not self.vteMinChanged:
            self.vteMinChanged = True
            self.vteMinSlider.setStyleSheet(AlarmSettings.sliderMinSetStyle)
            self.lblVteMin.setStyleSheet("QLabel {color: #2a66ff;}") # label becomes blue on white background
            self.btnCancel.setEnabled(True)
            self.btnConfirm.setEnabled(True)
        # Adjust acompanying label
        self.lblVteMin.setText(floatToStr(newval,0))
        ypos = AlarmSettings.pixelPosFromValue(235, 385, self.vteMinSlider.minimum(), self.vteMinSlider.maximum(), self.vteMinSlider.value())
        self.lblVteMin.setGeometry(445,ypos,50,20)
        # Adjust the slider's mask so that mouse events are only received by the handle (note that regions are relative to slider object)
        ymask = AlarmSettings.pixelPosFromValue(0, 150, self.vteMinSlider.minimum(), self.vteMinSlider.maximum(), self.vteMinSlider.value())
        self.vteMinSlider.setMask(QRegion(0, ymask, 70, 30))

    # When the VteMax alarm setting is changed, this slot responds and updates the appropriate flag
    @pyqtSlot(int)
    def changeVteMax(self, newval):
        # If this is the first time the value has been changed
        if not self.vteMaxChanged:
            self.vteMaxChanged = True
            self.vteMaxSlider.setStyleSheet(AlarmSettings.sliderMaxSetStyle)
            self.lblVteMax.setStyleSheet("QLabel {color: #2a66ff;}") # label becomes blue on white background
            self.btnCancel.setEnabled(True)
            self.btnConfirm.setEnabled(True)
        # Adjust acompanying label
        self.lblVteMax.setText(floatToStr(newval,0))
        ypos = AlarmSettings.pixelPosFromValue(55, 205, self.vteMaxSlider.minimum(), self.vteMaxSlider.maximum(), self.vteMaxSlider.value())
        self.lblVteMax.setGeometry(445,ypos,50,20)

    # Update alarms in main window object (slot for when Confirm button is pressed)
    @pyqtSlot()
    def updateAlarms(self):
        if self.pPeakChanged:
            self.mainWin.pPeakMaxAlarm = self.pPeakSlider.value()
            self.mainWin.pPeakAlarmSet = True
        if  self.PEEPChanged:
            self.mainWin.PEEPMaxAlarm = self.PEEPSlider.value()
            self.mainWin.PEEPAlarmSet = True
        if  self.vteMinChanged or self.vteMaxChanged:
            self.mainWin.vteMinAlarm = self.vteMinSlider.value()
            self.mainWin.vteMaxAlarm = self.vteMaxSlider.value()
            self.mainWin.vteAlarmSet = True
        # Set Confirm & Cancel back to disabled
        self.btnCancel.setEnabled(False)
        self.btnConfirm.setEnabled(False)

    # Set/reset alarms from main window object: when dialog opened and slot for Cancel button
    @pyqtSlot()
    def resetAlarms(self):
        # Ppeak
        self.pPeakSlider.setValue(self.mainWin.pPeakMaxAlarm)
        self.pPeakSlider.setStyleSheet(AlarmSettings.sliderMaxNotSetStyle)
        self.lblPPeakMax.setStyleSheet("QLabel {color: white;}") # label becomes white on coloured background
        self.pPeakChanged = False
        # PEEP
        self.PEEPSlider.setValue(self.mainWin.PEEPMaxAlarm)
        self.PEEPSlider.setStyleSheet(AlarmSettings.sliderMaxNotSetStyle)
        self.lblPEEPMax.setStyleSheet("QLabel {color: white;}") # label becomes white on coloured background
        self.PEEPChanged = False
        # VteMin
        self.vteMinSlider.setValue(self.mainWin.vteMinAlarm)
        self.vteMinSlider.setStyleSheet(AlarmSettings.sliderMinNotSetStyle)
        self.lblVteMin.setStyleSheet("QLabel {color: white;}") # label becomes white on coloured background
        self.vteMinChanged = False
        # VteMax
        self.vteMaxSlider.setValue(self.mainWin.vteMaxAlarm)
        self.vteMaxSlider.setStyleSheet(AlarmSettings.sliderMaxNotSetStyle)
        self.lblVteMax.setStyleSheet("QLabel {color: white;}") # label becomes white on coloured background
        self.vteMaxChanged = False
        # Confirm & Cancel buttons
        self.btnCancel.setEnabled(False)
        self.btnConfirm.setEnabled(False)

    # Given pixel min and max values, and slider min and max values, and the current value, return its pixel position
    # Note order of maxPix, minPix: this is because of orientation of my sliders
    def pixelPosFromValue(maxPix, minPix, minVal, maxVal, value):
        pixPos = minPix + (value-minVal) * (maxPix-minPix) / (maxVal-minVal)
        return round(pixPos)


    def __del__(self):
        # This is called when the dialog is closed
        # Need to disconnect slots connected to signals before closing the dialog
        self.mainWin.newPpeakInt.disconnect(self.pPeakBar.setValue)
        self.mainWin.newPEEPInt.disconnect(self.PEEPBar.setValue)
        self.mainWin.newVteInt.disconnect(self.vteBar.setValue)



# ============== main() funcion =======================

def main():
    if REALSENSORS:
       # Check the status of port and open for communication
       if(ser.isOpen()==True):
            ser.close()
       ser.open()
       # specify the address of the RS485 adapter cable
       start_flowsensor(ADDRESS)

    # Launch the application window
    app = QtWidgets.QApplication(sys.argv)
    #QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.BlankCursor) # stop the cursor being displayed
    window = MainWindow()
    window.show()

    # Run until the exit message
    sys.exit(app.exec_())
    if REALSENSORS:
        ser.close()

if __name__ == '__main__':
    main()

