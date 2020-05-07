# Community Python Scripts

* These are experimental. Never run a script you don't understand.
* Read all of the Formlabs OpenFL documentation before beginning. 
* Python 2.7 is recommended, Python 3.8 did not work properly during testing.
* You can use Windows, but it is recommended that you run Linux on a virtual machine (VM) for Python.

# How To Use

1) Read everything in this file, as well as the main [README.md](https://github.com/opensourcemanufacturing/OpenFL/)
2) Install Python 2.7
3) Clone the OpenFL git to the directory of choice on your local computer
4) Install OpenFL - follow the instructions in the main [README.md](https://github.com/opensourcemanufacturing/OpenFL/)
5) Move the script to the OpenFL-master folder
6) Read the script and make sure you understand what it does - there are comments in the scripts that describe how they work
7) Use a terminal or command line to run the script using python
* If the script fails, try power cycling the printer and reseating the USB cable before trying again
* These secripts are experimental and they do occasionally fail, don't be discouraged


# Script Descriptions:

1) [Insertz_100u.py](https://github.com/opensourcemanufacturing/OpenFL/blob/master/Community-PythonScripts/Scripts/Insertz_100u.py)

* This script will allow you to use Z lift for peeling and allow you to disable the tilt peeling. You need to run this script at a 0.1mm layer height with these ["btwnLayerRoutine"](https://github.com/opensourcemanufacturing/OpenFL/blob/Dev/Community-PythonScripts/VerticalLiftProfile.ini) settings. If you use a different layer height or the wrong "btwnLayerRoutine" the script will not work properly and may crash your printer.
* I recommend deleting all blocks that are currently on your printer before slicing with PreForm. Preform does not delete block numbers when slicing, it overwrites them. So if your current print job is 240 layers tall, and your tallest previous print was 1000 layers tall, the script will run for all 1000 blocks (layers) on your printer. [Click here for a script that will delete all blocks on the printer](https://openfl.dev)

* If the script fails due to some USB issue, make sure Preform is not running. You might want to consider using a faster SD card (the SanDisk card in my machine is very slow and crashes occasionally).

* The print restart option in Preform (File > Printers) works if you want to print the same thing more than once.

2) [ZOffset.py](https://github.com/opensourcemanufacturing/OpenFL/blob/master/Community-PythonScripts/Scripts/ZOffset.py)
* Tune your Z offset for the current print without removing your SD card.

3) [FLP_PrintAll_01_042720.py](https://github.com/opensourcemanufacturing/OpenFL/blob/master/Community-PythonScripts/Scripts/FLP_PrintAll_01_042720.py)

* READ COMMENTS IN SCRIPT BEFORE USING: This is a troubleshooting script that Writes FLP blocks to a text file. This is helpful for understanding FLP files. Read the comments in the script and edit it before running. Look at [FLPBlockDescriptions.md](https://github.com/opensourcemanufacturing/OpenFL/blob/master/Community-PythonScripts/FLPBlockDescriptions.md) for an overview of what is in an FLP block.
