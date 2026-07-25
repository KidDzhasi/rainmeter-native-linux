#!/bin/bash
# Kill any existing instances to prevent duplicates
pkill -x rainmeter-native

# Launch the engine detached from the terminal, silencing all terminal output
nohup /home/remember/Documents/GitHub/rainmeter-native/build/rainmeter-native \
/home/remember/.config/rainmeter-native/Skins/PopNative/Desktop/Desktop.ini > /dev/null 2>&1 &
