from OpenFL import FLP, Printer
p=Printer.Printer()

# Initialize first - it seems to increase success rate of the script.
# Initializing stops any operations that are current running,
# and re homes the Z and tilt motors.
print ("initializing")
p.initialize()
                        
# This section sets the starting point of the loop to block 1 (layer 2)
# finds the number of the blocks (layers) on your Form1/1+
# and uses the highest block number as the stopping point for the script.

totalBlocks = p.list_blocks()

if str(totalBlocks) != "()":
        print("Deleting Blocks")
        lastBlock = totalBlocks[-1]
        p.delete_block(0, lastBlock)
        print("All Blocks Deleted")
else:
        print("All Blocks Deleted")

p.shutdown()
p.initialize()
exit()

