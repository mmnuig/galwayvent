## This sets the ventilator programm running automatically when the Raspberry Pi is booted up.
## It does so using ~/.xsession and ~/.xsessionrc to start x-window-manager 
## and the ventilator app and nothing else
## M Madden, April 2020

echo "After running this program, it will reboot the Raspberry Pi"
echo "and the ventilator will start automatically on bootup."
echo
echo "Note: ventilator application must be in /home/pi/VentGUI/VentGUI.py"
echo "To disable the auto-start, press Ctrl-Alt-F1 on a connected keyboard, "
echo "run noautostart.sh, and it will change the configuration and reboot."

cp /home/pi/VentGUI/xsession.txt /home/pi/.xsession
cp /home/pi/VentGUI/xsessionrc.txt /home/pi/.xsessionrc

echo
echo "Rebooting in 1 minute ..."
shutdown -r 1

