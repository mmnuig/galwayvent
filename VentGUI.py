from PyQt5 import QtWidgets, QtCore, uic
import pyqtgraph as pg
import sys  # We need sys so that we can pass argv to QApplication
from random import uniform
from numpy import array
import math

import serial

# Some important overall settings
REALSENSORS=False     # if True, read data from sensors; if false, generate random numbers
interval = 50         # update interval 50ms
graphPoints = 100     # how many points to display on the graph
movingWindowSize = 20 # Size of the window for estimation of peak and mean values

# Simple utility function to round a float to a specified number of digits (defaults to 2) and convert to string
def floatToStr(value, numDigits=2):
    # if we want to round to 0 digits, convert to an int, otherwise we get trailing ".0" which we don't want
    v = int(value) if (numDigits==0) else round(value, numDigits)
    return str(v)

ADDRESS = 0x01

if REALSENSORS:
    # The serial port access crashes in Windows - don't access it if sumulating data
    ser = serial.Serial(
             port = '/dev/ttyUSB0',          #number of device, numbering starts at zero.
             baudrate=115200,            #baudrate
             bytesize=serial.EIGHTBITS,  #number of databits
             parity=serial.PARITY_NONE,  #enable parity checking
             stopbits=serial.STOPBITS_ONE,  #number of stopbits
             timeout=1,                  #set a timeout value (example only because reset
                                #takes longer)
             xonxoff=0,                  #disable software flow control
             rtscts=0,                   #disable RTS/CTS flow control
         )

# Define routines for communication with sensor

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
        

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        #Load the UI Page
        uic.loadUi('mainwindow.ui', self)
        self.showFullScreen();
        
        # Set up a timer
        self.timer = QtCore.QTimer()
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.updatePlots)
        self.timer.start()

        # Pen that defines the line style for the graphs
        self.linePen = pg.mkPen(color='g', width=3)

        # Initialise graphs
       # self.timeData = list(range(graphPoints)) # numbers 0-99
        self.timeData = array(range(graphPoints))*interval/1000 # time array is values in seconds

        self.pressData = [0] * len(self.timeData) # make a list of zeros the same length as the timeData list
        self.flowData = [0] * len(self.timeData) # make a list of zeros the same length as the timeData list
        self.setupPressurePlot(self.timeData, self.pressData)
        self.setupFlowPlot(self.timeData, self.flowData)
        
        # Some additional variables to calculate stats
        # Note - moved some of these from being class variables to instance variables
        self.timeCount = 0
        self.prevFlow = 0
        self.prevPress = 0
        self.instV = 0
        self.vteTimer = 0
        self.insp = bool(False)
        self.Exp = bool(False)
        self.posPeaks = [0] * movingWindowSize
        self.negPeaks = [0] * movingWindowSize
        self.PEEP = [0] * 5
        self.expV = [0] * 5

        if not REALSENSORS:
            self.xSim = 0

    def setupPressurePlot(self, hour, press):
        self.pressureLine = self.pressGraphWidget.plot(hour, press, pen=self.linePen)
        self.pressGraphWidget.setEnabled(False) # Disable all interaction - want output-only graph display

    def setupFlowPlot(self, hour, flow):
        self.flowLine = self.flowGraphWidget.plot(hour, flow, pen=self.linePen)
        self.flowGraphWidget.setEnabled(False) # Disable all interaction - want output-only graph display

    def updatePlots(self):
        # Update the timeline - not doing this for now
        #self.timeData = self.timeData[1:]  # Remove the first y element.
        #self.timeData.append(self.timeData[-1] + 1)  # Add a new value 1 higher than the last.

        if REALSENSORS:
            # Real mode, not simulation mode: read data from sensors
            flow = get_flow(ADDRESS)
            pressure = get_pressure(ADDRESS)
        else:
            # Simulation mode: use random numbers
            # Using cosine waves with random noise and period 2pi over 100 points
            flow = 20 * math.cos(self.xSim / 50 * math.pi) - 10 + uniform(-2,2)
            pressure = 5 * math.cos(self.xSim / 50 * math.pi) + 15 + uniform(-4,4)
            self.xSim = 0 if (self.xSim >= 99) else self.xSim + 1 # wrap around 100 -> 0

        # PEEP estimation
        if(flow>=0 and self.prevFlow<0): # Detect sero crossing: negative to positive change
            if(self.vteTimer>20): # Ignore if a cycle is too small
               self.PEEP = self.PEEP[1:]
               self.PEEP.append(self.prevPress) # PEEP
               self.expV = self.expV[1:]
               self.expV.append(2286*(self.instV/(self.vteTimer*50))) # tidal volume
               # print(self.vteTimer)
            self.instV = 0
            self.vteTimer = 0
            self.insp = True
            self.Exp = False
            
        
        if(flow<0 and self.prevFlow>=0): # Detect sero crossing: Postive to negative change
            self.insp = False
            self.Exp = True
    
            
        if(self.Exp == True): # for estimation of tidal volume
            self.instV += -1*flow
            self.vteTimer += 1
        
    
        self.prevPress = pressure    
        self.prevFlow = flow

        # Update the pressure graph
        self.pressData = self.pressData[1:]  # Remove the first
        self.pressData.append(pressure)  # Add the latest pressure value
        self.pressureLine.setData(self.timeData, self.pressData)  # Update the graph with the new data.
        self.pressGraphWidget.showGrid(x=False, y=True) # Horizontal grid lines including at y=0

        # Update the flow graph
        self.flowData = self.flowData[1:]  # Remove the first
        self.flowData.append(flow)  # Add the latest flow value
        self.flowLine.setData(self.timeData, self.flowData)  # Update the graph with the new data.
        self.flowGraphWidget.showGrid(x=False, y=True) # Horizontal grid lines including at y=0
        
        # Record last 20 peak pressure values and average
        self.posPeaks = self.posPeaks[1:]
        self.posPeaks.append(max(self.pressData))
        
        self.timeCount += 1

        # Update stats
        if(self.timeCount>5): # update every 5th call (250ms)
           self.setPpeak(sum(self.posPeaks)/movingWindowSize)
           self.setVte(sum(self.expV)/5)
           self.setPEEP(sum(self.PEEP)/5)
           self.timeCount = 0
    
    # Change Ppeak value
    def setPpeak(self, value):
        self.valPpeak.setText(floatToStr(value,1))

    # Change Vte value
    def setVte(self, value):
        self.valVte.setText(floatToStr(value,1))

    # Change PEEP value
    def setPEEP(self, value):
        self.valPeep.setText(floatToStr(value,1))



    # Quit out of the app by pressing ESC key
    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()

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
    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.BlankCursor) # stop the cursor being displayed

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    ser.close()

if __name__ == '__main__':
    main()

