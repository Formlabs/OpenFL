# Community Python Scripts

* These are experimental. Never run a script you don't understand.
* Read all of the Formlabs OpenFL documentation before beginning. 
* Python 2.7 is recommended, Python 3.8 did not work properly during testing.
* You can use Windows, but it is recommended that you run Linux on a virtual machine (VM) for Python.


# Script Descriptions:

1) [Insertz_100u.py](https://github.com/opensourcemanufacturing/OpenFL/blob/master/Community-PythonScripts/Scripts/Insertz_100u.py)

* This script will allow you to use Z lift for peeling and allow you to disable the tilt peeling. You need to run this script at a 0.1mm layer height with these ["btwnLayerRoutine"](https://github.com/opensourcemanufacturing/OpenFL/blob/Dev/Community-PythonScripts/VerticalLiftProfile.ini) settings. If you use a different layer height or the wrong "btwnLayerRoutine" the script will not work properly and may crash your printer. 

* If the script fails due to some USB issue, make sure Preform is not running. You might want to consider using a faster SD card (the SanDisk card in my machine is very slow and crashes occasionally).

* The print restart option in Preform (File > Printers) works if you want to print the same thing more than once.

2) [ZOffset.py](https://github.com/opensourcemanufacturing/OpenFL/blob/master/Community-PythonScripts/Scripts/ZOffset.py)
* Tune your Z offset for the current print without removing your SD card.

3) [FLP_PrintAll_01_042720.py](https://github.com/opensourcemanufacturing/OpenFL/blob/master/Community-PythonScripts/Scripts/FLP_PrintAll_01_042720.py)

* READ COMMENTS IN SCRIPT BEFORE USING: This is a troubleshooting script that Writes FLP blocks to a text file. This is helpful for understanding FLP files. Read the comments in the script and edit it before running. Look at [FLPBlockDescriptions.md](https://github.com/opensourcemanufacturing/OpenFL/blob/master/Community-PythonScripts/FLPBlockDescriptions.md) for an overview of what is in an FLP block.
