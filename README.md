# Galway VentShare Software
This reads and displays data from sensors for volume and pressure for individual patients on shared ventilators. Part of GalwayVentShare.com project.
http://galwayventshare.com/

The GalwayVentShare software is written in Python with PythonQT, and can run on Windows, MacOS or Linux. However, the current version of the sensor interface code is intended for use on a Raspberry Pi with the correct sensors attached. 

# How to Install and Run the Software on a Raspberry Pi
You can clone this repository or download the code as a ZIP file and then unzip it on the Raspberry Pi. Copy all of the files into a directory called /home/pi/VentGUI. That’s the installation finished!

By default, it displays synthetic data. If you have the correct sensors attached, you can display real data from them. To enable this, edit VentGUI.py with a text editor, and change Line 21 to 
```python
REALSENSORS=True
```
To run the software, enter these commands:
```shell
cd /home/pi/VentGUI
python3 VentGUI.py
```
While it is running, you don’t need the mouse and keyboard, as it has a touchscreen interface. To exit out of the software, press **Esc** on the keyboard.
To set the Raspberry Pi to run the software automatically every time it powers up, run this command:
```shell
/home/pi/VentGUI/autostart.sh
```
To disable this auto-start behaviour when the Pi is already running the software, press **Ctrl-Alt-F1** to bring up a new terminal window, then run
```shell
/home/pi/VentGUI/noautostart.sh
```

![Picture of software running](https://github.com/mmnuig/galwayvent/blob/master/photo06.jpg)
