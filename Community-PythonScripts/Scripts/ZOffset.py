from OpenFL import FLP, Printer
p=Printer.Printer()

# Initialize first - it seems to increase success rate of the script.
# Initializing stops any operations that are current running,
# and re homes the Z and tilt motors.
print ("initializing")
p.initialize()

# This adds a Z Offset. User will be prompted for an offset value.
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
if ZoffsetMirrored != "":
    print("Z Offset Set To " + ZoffsetMirrored)
else:
    print("Z Offset Unchanged Because You Chose to Skip")
p.initialize()
exit()
