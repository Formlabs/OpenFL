from OpenFL import FLP, Printer
p=Printer.Printer()

# Initialize first - it seems to increase success rate of the script.
# Initializing stops any operations that are current running,
# and re homes the Z and tilt motors.
print ("initializing")
p.initialize()

# This section adds a Z Offset. User will be prompted for an offset value.
# Positive values = build plate closer to vat
# Negative values = build plate further from vat
print ("Z offset.")
print ("Positive = down, negative = up")
x = 0
while x == 0:
        ZoffsetMirrored = raw_input("Enter Z Offset OR Press Enter to Skip:")
        try:
                if ZoffsetMirrored != "":
                        print ("Z Offset will be set to " + str(ZoffsetMirrored))
                        Zoffset = (float(ZoffsetMirrored) * (-400.0))
                        print ("saving Z Offset to printer")
                        blockNum = 0
                        layer = p.read_block_flp(blockNum)
                        layer[16] = FLP.ZMove(int(-66924 + Zoffset))
                        p.write_block(blockNum, layer)
                        x = 1
                else:
                        x = 1
        except ValueError:
                print ("You must enter a number or press Enter to continue")
                continue
                        
# This section sets the starting point of the loop to block 1 (layer 2)
# finds the number of the blocks (layers) on your Form1/1+
# and uses the highest block number as the stopping point for the script.
blockNum = 1
totalBlocks = p.list_blocks()
lastBlock = totalBlocks[-1]

# This loop changes two lines and adds a third line in each
# block (layer) on the printer. It checks to see if the value has already
# been set before trying to change it. So, if the script hangs, you should
# be able to run it again without overwriting the changes from the first
# attempt.
# Summary of changes:
# 1) First, it changes the Z feed rate in line 5
# 2) Next, it inserts a positive Z move of 2000 usteps (5mm)
# 3) Lastly, it changes the Z move in layer 9 to -1960 (-4.9mm)
# Note that in this case, positive values move the build plate away from
# the vat, and negative values move the build plate closer to the vat.
# loop continues until it gets to the last block on the printer and then it ends.
print ("starting loop")
while blockNum <= lastBlock:

        layer = p.read_block_flp(blockNum)

        if str(layer[5]) != '0x04 ZFeedRate '+str(267):
                try:
                        layer[5] = FLP.ZFeedRate(267)
                except:
                        break
        if str(layer[6]) != '0x03 ZMove '+str(2000):
                try:
                        layer.insert(6, FLP.ZMove(usteps=(2000)))
                except:
                        break
        if str(layer[9]) != '0x03 ZMove '+str(-1960):
                try:
                        layer[9] = FLP.ZMove(usteps=(-1960))
                except:
                        break
        p.write_block(blockNum, layer)
        print ("Layer " + str(blockNum) +" finished")
        blockNum += 1

print ("script ended at layer " + str(blockNum) +" out of " + str(lastBlock))
p.initialize()
exit()

