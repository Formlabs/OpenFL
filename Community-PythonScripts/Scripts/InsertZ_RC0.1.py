from OpenFL import FLP, Printer

print ("This could take a while, pour yourself a drink, you've earned it!")
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

print ("setting block number")
blockNum += 1

print ("checking for highest layer number")
totalBlocks = p.list_blocks()
lastBlock = totalBlocks[-1]

print ("starting loop")
while blockNum <= lastBlock:

        layer = p.read_block_flp(blockNum)

        if str(layer[5]) != '0x04 ZFeedRate 265':
                try:
                        layer[5] = FLP.ZFeedRate(265)
                        p.write_block(blockNum, layer)
                        print ("progress: setting Z Feed Rate for layer number " + str(blockNum))
                except:
                        print ("Failed at block " + str(blockNum) + " layer[5]")
                        break
        if str(layer[6]) != '0x03 ZMove 2000':
                try:
                        layer.insert(6, FLP.ZMove(usteps=2000))
                        p.write_block(blockNum, layer)
                        print ("progress: setting Z Lift for layer number " + str(blockNum))
                except:
                        print ("Failed at block " + str(blockNum) + " layer[6]")
                        break
        if str(layer[9]) != '0x03 ZMove -1960':
                try:
                        layer[9] = FLP.ZMove(usteps=-1960)
                        p.write_block(blockNum, layer)
                        print ("progress: setting Z Drop for layer number " + str(blockNum))
                except:
                        print ("Failed at block " + str(blockNum) + " layer[9]")
                        break

        print ("Layer " + str(blockNum) +" finished")
	blockNum += 1

print ("Z Lift batch complete, woohoo!")
exit()

