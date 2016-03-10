#!/usr/bin/env python
from __future__ import division
import sys
import os
sys.path.append(os.path.abspath('../OpenFL'))

import numpy as np

def image_to_laser_moves(image, M, mmps=500.0, powerThreshold_mW=0.0, doFilter=False):
    """
    Given an image and a transform, rasterize the image.
    Return an FLX.FLXIdealLaserSegments object.
    """
    image = np.asarray(image)
    M = np.asarray(M)
    assert image.ndim == 2
    assert M.shape == (3, 3)
    # Transform so image (0, 0) sits at the origin and 
    # image is in quadrant IV (+x,-y):
    M = M.dot([[0,1,0],
               [-1,0,0],
               [0,0,1]])
    # We need to add zeros at the ends of rows
    # and we want to scan back and forth:
    image = image.copy()
    image = np.hstack([np.zeros((image.shape[0],1)), image])
    ij = np.indices(np.shape(image), dtype=float)
    # Shift segments so they wind around.
    ij[1,:] -= 0.5
    # Serpentine path
    ij[1,1::2] = ij[1,1::2,::-1] 
    image[1::2] = np.roll(image[1::2], -1)
    image[1::2] = image[1::2,::-1]
    image = image.flatten()
    ij = ij.reshape(2,-1)
    ij1 = np.vstack([ij, np.ones_like(ij[:1])])
    xy = M.dot(ij1)
    xy = xy[:-1] / xy[-1:] # Perspective divide.
    # Not sure how to deal with energy density... for now let's ignore it.
    result = []
    result.append((0.0, 0.0, 0.0, 0.0))
    for i, (xy_mm, mW) in enumerate(zip(xy.T, image)):
        prev_xy_mm = result[-1][1:3]
        direction = xy_mm - prev_xy_mm
        dist_mm = np.linalg.norm(direction)
        dt_s = dist_mm / mmps
        result.append((dt_s, xy_mm[0], xy_mm[1], mW))

    xy_mm = np.array((0.0, 0.0))
    dist_mm = np.linalg.norm(xy_mm - result[-1][1:3])
    dt_s = dist_mm / mmps
    result.append((dt_s, xy_mm[0], xy_mm[1], 0.0))
    # Filter result to exclude straight lines.
    normalized = lambda x: np.asarray(x) / np.linalg.norm(x)
    if len(result) <= 3 or not doFilter:
        return np.array(result), xy, image

    filtered = [result[0]]
    sum_dt_s = 0.0
    mW = result[0][3]
    for seg_i in range(1, len(result)):
        # Include seg_i if it is a different power than the last seg included.
        sum_dt_s += result[seg_i-1][0]
        # See if this segment has a different power.
        if abs(result[seg_i][3] - mW) > powerThreshold_mW:
            # This segment has a different power, so add the first
            # point of this segment, with the last power and the sum time.
            # That constitutes the previous-power line segment.
            # Now start summing up the new segment.
            if mW == 0.0:
                dist_mm = np.linalg.norm(np.array(filtered[-1][1:3]) - result[seg_i-1][1:3])
                sum_dt_s = dist_mm / mmps
            filtered.append((sum_dt_s,) + tuple(result[seg_i-1][1:3]) + (mW,))
            sum_dt_s = 0.0
            mW = result[seg_i][3]

    filtered.append((sum_dt_s,) + tuple(result[-1][1:3]) + (mW,))
    return np.array(filtered), xy, image


def samplesToFLP(dtxypower):
    clock_Hz = 60e3
    xytickspmm = float(0xffff) / 125
    lastPower = None
    xyticks = []
    from OpenFL import FLP
    result = FLP.Packets()
    import numpy as np
    tickspmm = float(0xffff)/125.0
    midticks = float(0xffff)/2
    xyToTicks = np.array([[tickspmm, 0, midticks],
                          [0, tickspmm, midticks],
                          [0, 0, 1]])
    for dt_s, x_mm, y_mm, power in dtxypower:
        if power != lastPower:
            if xyticks:
                result.append(FLP.XYMove(xyticks))
                xyticks = []
            result.append(FLP.LaserPowerLevel(power))
            lastPower = power
        xy_ticks = xyToTicks.dot((x_mm, y_mm, 1))
        x_ticks, y_ticks = xy_ticks[:2] / xy_ticks[-1]
        dt_ticks = dt_s * clock_Hz
        # Deal with potential that the move takes too long to fit in one step:
        for i in range(int(dt_ticks // 0xffff)):
            alpha = (i+1) * 0xffff / dt_ticks 
            x = np.interp(alpha, [0.0, 1.0], [lastxy_ticks[0], x_ticks])
            y = np.interp(alpha, [0.0, 1.0], [lastxy_ticks[1], y_ticks])
            xyticks.append((x, y, 0xffff))
        dt_ticks %= 0xffff # Now we just have to do the last little bit.
        xyticks.append((x_ticks, y_ticks, dt_ticks))
        lastxy_ticks = xy_ticks
    if xyticks:
        result.append(FLP.XYMove(xyticks))
    return result


def image_to_flp(imagefilename, flpfilename):
    from scipy.ndimage import imread
    image = imread(imagefilename)
    if image.ndim == 3:
        image = image.mean(axis=-1)
    image /= image.max()
    image[image < 0.25] = 0 # Throw out noise/edges, etc.
    image *= 0xffff/2
    M = np.diag((0.1,.1,1))+[[0,0,0.1],[0,0,0.05],[0,0,0]]
    result, xy, imflat = image_to_laser_moves(image, M, mmps=5e2, doFilter=True)
    # Center:
    lo = result[:,1:3].min(axis=0)
    hi = result[:,1:3].max(axis=0)
    result[:,1:3] -= [(lo + hi)/2]
    data = samplesToFLP(result)
    data.tofile(flpfilename)


def plotResults(result):
    from pylab import figure, hold, show
    from matplotlib import collections  as mc
    figure()
    hold(True)
    lines = []
    mWs = []
    for seg_i in range(1, len(result)):
        lines.append([result[seg_i-1][1:3], result[seg_i][1:3]])
        mWs.append(result[seg_i][3])

    norm = mpl.colors.Normalize(vmin=0, vmax=150)
    colorMapper = cm.ScalarMappable(norm=norm, cmap=cm.jet)
    lc = mc.LineCollection(lines, linewidths=2, colors=colorMapper.to_rgba(mWs))
    ax = gca()
    ax.add_collection(lc)
    ax.autoscale()
    ax.margins(0.1)
    ax.axis('equal')

    #plot(result[:,2], result[:,1])
    #scatter(result[:,2], result[:,1], c=result[:,3],vmin=0, vmax=150)
    #colorbar(colorMapper)
    show()


if __name__ == '__main__':
    import sys
    png, flp = sys.argv[1], sys.argv[2]
    assert png.endswith('.png')
    assert flp.endswith('.flp')
    image_to_flp(png, flp)
