# Created by Lavachemist on April 27, 2020 - thelavachemist@gmail.com
# I don't suggest running this script as written, unless you have a very small print!!
# This script will print every block/layer of the FLP files currently loaded onto your Form 1/1+
# For reference, the small Makerook (https://www.thingiverse.com/thing:533652) has 6504 blocks when sliced at a 0.1mm layer height
# You can use this script as a starting point for exploring the inner workings of an FLP file.
# This shouldn't work if you have PreForm open, so make sure PreForm is closed.


# Import the relevant modules
import sys
from OpenFL import Printer
from OpenFL import FLP

# This p variable is for the Printer.Py file in OpenFL
p=Printer.Printer()

# This creates a text file called "testFLP_01.txt" in the current directory
sys.stdout = open("testFLP_01.txt", "w")

# This variable is equal to the number of blocks in the FLP files on your Form1/1+
sizeofList = len(p.list_blocks()) 

# The i variable represents the block number in the 'p.list_blocks' list
i = 0

# If you want to create a text file with a limited number of layers you can remove the sizeofList variable from the while loop below
# and replace it with an integer. For instance, if you wanted to create a text file with the first 5 blocks, you could replace the variable with 5
# I strongly advise that you do not run the full list, it will be very large.
 
while i < sizeofList :
    print (p.read_block_flp(block=i))
    i += 1

# This closes out the "testFLP_01.txt" file and saves it.
sys.stdout.close

# Not sure if this is necessary - I'm a noob.
exit()
