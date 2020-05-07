# FLP Block Content Examples

The tables below are an example of what is inside of FLP blocks in a Form1/1+ print. 
* Block 0 is the first layer of the print. It includes the initial homing sequence
* Block 1 is the second layer of the print. Subsequent layers will be similar.
* No galvo moves are included below - A table explaining those will be added soon.

## Block 0 (layer 1)


FLP Packet  | Purpose | Description
-------------------- | -------------------- |-------------
0x12 TimeRemaining 2264 | |
0x02 XYMoveClockRate 60000 | |
0x01 LaserPowerLevel 0 | |
0x05 ZCurrent 80 | Fast Z homing Sequence | stepper current (Z motor)
0x04 ZFeedRate 5999 | Fast Z homing Sequence | ~15mm/s (no idea the significance of the one missing microstep, probably a rounding error)
0x03 ZMove 78670 | Fast Z homing Sequence | +196mm (stops at endstop)
0x0a WaitForMovesToComplete  | Fast Z homing Sequence | Equivalent to M400
0x04 ZFeedRate 6000 | Retract 1mm | 15mm/s
0x03 ZMove -400 | Retract 1mm | -1mm
0x0a WaitForMovesToComplete  | Retract 1mm | Equivalent to M400
0x04 ZFeedRate 200 | Slow Z homing Sequence | 0.5mm/s
0x03 ZMove 78670 | Slow Z homing Sequence | +196mm (stops at endstop)
0x0a WaitForMovesToComplete  | Slow Z homing Sequence | Equivalent to M400
0x05 ZCurrent 40 | These seem redundant | turn Z stepper current down…
0x05 ZCurrent 80 | These seem redundant | …turn Z stepper current back up again
0x04 ZFeedRate 4000 | Rapid Z move | 10mm/s 
0x03 ZMove -65484 | Rapid Z move | -16.46mm drop before resetting vat tilt (this is where Z offset is applied modify this number to change Z offset)
0x0a WaitForMovesToComplete  | Rapid Z move | Equivalent to M400
0x08 TiltCurrent 80 | Tilt vat down | stepper current (peel motor)
0x07 TiltFeedRate 3149 | Tilt vat down | peel motor current in microsteps per second
0x06 TiltMove 3150 | Tilt vat down | move peel motor down 3150 microsteps
0x03 ZMove -8000 | Z move for first layer | This is always -8000. This number + line 17 = Z sensor heght (derrived from "read_zsensor_height" function in Printer.py
0x0a WaitForMovesToComplete  | Z move for first layer | Equivalent to M400
0x07 TiltFeedRate 314 | Tilt vat up | peel motor current in microsteps per second
0x06 TiltMove -3150 | Tilt vat up | move peel motor up 3150 microsteps
0x0a WaitForMovesToComplete  | Tilt vat up | Equivalent to M400
0x07 TiltFeedRate 3149 | Tilt vat up even more | peel motor current in microsteps per second
0x06 TiltMove -160 | Tilt vat up even more | move peel motor up 160 microsteps (I believe this pushes until it skips - makes sure vat is all the way up)
0x0a WaitForMovesToComplete  | Tilt vat up even more | Equivalent to M400
0x08 TiltCurrent 40 | peel motor current | sets low current for peel motor (for holding position)
0x05 ZCurrent 40 | Z motor current | sets low current for Z motor (for holding position)
0x09 Dwell 2000 |  | dwell for 2000 units of time (microseconds?)
0x04 ZFeedRate 4000 | Set Z feedrate | 
0x10 LayerStart 0 |  | marker for first layer beginning
Below this are all of the galvo moves for the first layer |  | 

## Block 1 (layer 2)


FLP Packet  | Purpose | Description | Notes
---------------------------- | -------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------
0x09 Dwell 1000 |  |  | 
0x12 TimeRemaining 2220 |  |  | 
0x02 XYMoveClockRate 60000 |  |  | 
0x11 LayerDone  |  |  | 
0x05 ZCurrent 80 |  |  | 
0x08 TiltCurrent 80 | Peel Move |  | All of this can be removed by zeroing out fields in the custom material file
0x07 TiltFeedRate 314 |  |  | All of this can be removed by zeroing out fields in the custom material file
0x06 TiltMove 3150 |  |  | All of this can be removed by zeroing out fields in the custom material file
0x0a WaitForMovesToComplete  |  | Equivalent to M400 | All of this can be removed by zeroing out fields in the custom material file
0x04 ZFeedRate 1000 | Move Z up for layer 2 |  | 
0x03 ZMove 40 |  | 0.1mm lift | 
0x0a WaitForMovesToComplete  |  | Equivalent to M400 | 
0x07 TiltFeedRate 1259 | Tilt vat up |  | All of this can be removed by zeroing fields in the custom material file
0x06 TiltMove -3150 |  |  | All of this can be removed by zeroing fields in the custom material file
0x0a WaitForMovesToComplete  |  |  | All of this can be removed by zeroing fields in the custom material file
0x07 TiltFeedRate 3149 | Tilt vat up even more |  | 
0x06 TiltMove -160 |  |  | 
0x0a WaitForMovesToComplete  |  | Equivalent to M400 | 
0x09 Dwell 2000 |  |  | 
0x05 ZCurrent 40 |  |  | 
0x08 TiltCurrent 40 |  |  | 
0x10 LayerStart 1 |  |  | 
0x01 LaserPowerLevel 0 |  |  | 
0x00 XYMove 6 |  |  | 
Below this are all of the galvo moves for the second layer |  |  | 

