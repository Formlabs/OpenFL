#Experimental! Do not use unless you understand what you're doing!
#Created by lavachemist on April 28, 20204
#This code assumes you have set your material settings exactly the way I have!
#You can crash if you make a mistake, so be careful.
#Highly suggest that you do a test with no vat and no build plate
#to make sure moves look sane!

#This script works best if you manually delete all existing FLP files from the SD card (leave everything else on the SD card) before 
#slicing, then: 1) Slice and upload to printer, but do not print 2) Close Preform and run this script, make sure it succeeeds.
#3) Press the button on the printer to begin printing. If power was removed or a print aborted, you can restart the print
#using Preform, under File > Printers there is an option to restart the last print (note that if you changed the z offset
#on your SD card, you will need to repeat steps 1 and 2 again in order for the offset to take effect since the offset is applied to the
#the block 0 FLP file by Preform during slicing.

from OpenFL import Printer, FLP

#Starting the loop at the second layer/block. This is because we still have a
#tilt move on the first layer (aka Printer.read_block_flp[0]).
p=Printer.Printer()
i = 1

#This checks the total number of blocks on the SD card and takes the value of the last block
#before running the loop below. You should delete all FLP files on  your SD card before slicing 
#and running this script. This allows us to run the while loop on the number of blocks/layers in our print job.
totalBlocks = p.list_blocks()
lastBlock = totalBlocks[-1]

#Logic behind this is that we are overwriting line 5 of each layer/block,
#setting to a z feedrate of 265 usteps per second, inserting a Z move of
#2000 usteps (5mm) on line 6 of each layer/block, and then using layer 9 to
#lower the platform -1960 usteps (40 usteps above the starting point, or 0.1mm)
#Math:
#400 usteps = 1mm (according to FLP.ZMove)
#and 400 ustep/sec = 60mm/min (1mm/second for 60 seconds)
#therefore, 265 ustep/sec = approximately 40mm/min (slightly less)

while i <= lastBlock:
    layer = p.read_block_flp(i)
    layer[5] = FLP.ZFeedRate(265)
    p.write_block(i, layer)
    layer.insert(6, FLP.ZMove(usteps=2000))
    p.write_block(i, layer)
    layer[9] = FLP.ZMove(usteps=-1960)
    p.write_block(i, layer)
    i += 1
