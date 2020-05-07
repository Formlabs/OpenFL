from OpenFL import FLP, Printer

print ("Easy Z Offset Adjustment!")
p=Printer.Printer()

print ("about to initialize")
p.initialize()

print ("Enter your desired Z offset.")
print ("Positive numbers result in a lower Z offset,")
print ("Negative numbers result in a higher Z offset")
ZoffsetMirrored = raw_input("Enter Z Offset:")
print ("Z Offset will be set to " + str(ZoffsetMirrored))
Zoffset = (float(ZoffsetMirrored) * (-400.0))

print ("saving Z Offset to printer")
blockNum = 0
layer = p.read_block_flp(blockNum)
layer[16] = FLP.ZMove(int(-66924 + Zoffset))
p.write_block(blockNum, layer)
