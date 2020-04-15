## This undoes the effect of autostart.sh, which sets the ventilator programm running automatically when the Raspberry Pi is booted up.
## M Madden, April 2020

echo "After running this program, it will reboot the Raspberry Pi and "
echo "the ventilator will no longer start on bootup."
echo
echo "To get it back to automatically starting on bootup, run autostart.sh"
rm /home/pi/.xsession
rm /home/pi/.xsessionrc

echo "Rebooting in 1 minute..."
shutdown -r 1

