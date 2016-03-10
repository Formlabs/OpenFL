#!/usr/bin/env python

import sys
import os
sys.path.append(os.path.abspath('../OpenFL'))

from OpenFL import FLP

def insert_pause_before(layer,
                        zJog_mm=100,
                        buttonPressMessage="Press to continue."):
    """
    Jog up and wait on button press then resume.
    This is done when the tilt motor is at its lowest.
    """
    import numpy as np
    tiltMoves = [x for x in layer if  isinstance(x, FLP.TiltMove)]
    bestAfter = np.argmax(np.cumsum([move.usteps for move in tiltMoves]))
    lowestTiltMove_i = layer.index(tiltMoves[bestAfter])
    insertBefore_i = None
    zSpeed_usteps_per_s = None
    zCurrent = None
    for x in layer[:lowestTiltMove_i]:
        if isinstance(x, FLP.ZFeedRate):
            zSpeed_usteps_per_s = x.feedrate
        if isinstance(x, FLP.ZCurrent):
            zCurrent = x.current

    for i in range(lowestTiltMove_i, len(layer)):
        if isinstance(layer[i], FLP.WaitForMovesToComplete):
            insertBefore_i = 1 + i
            break
    assert insertBefore_i is not None
    # Now we know where the motors are stopped and tilt is at its lowest.

    pauseCycle = FLP.Packets()
    zJog_usteps = int(zJog_mm * FLP.ZMove.usteps_up_per_mm)
    zJog_mmps = 10.0
    pauseCycle.append(FLP.ZCurrent(FLP.ZCurrent.moving_current))
    pauseCycle.append(FLP.ZFeedRate(zJog_mmps * abs(FLP.ZMove.usteps_up_per_mm)))
    pauseCycle.append(FLP.ZMove(zJog_usteps))
    pauseCycle.append(FLP.WaitForMovesToComplete())
    pauseCycle.append(FLP.WaitButtonPress(buttonPressMessage))
    pauseCycle.append(FLP.ZMove(-zJog_usteps))
    pauseCycle.append(FLP.WaitForMovesToComplete())
    # Restore settings:
    pauseCycle.append(FLP.ZCurrent(zCurrent))
    if zSpeed_usteps_per_s is not None:
        pauseCycle.append(FLP.ZFeedRate(zSpeed_usteps_per_s))
    newLayer = layer[:insertBefore_i] + pauseCycle + layer[insertBefore_i:]
    return newLayer


if __name__ == '__main__':
    import sys
    layer = FLP.fromfile(sys.argv[1])
    layer = insert_pause_before(layer)
    layer.tofile(sys.argv[2])
