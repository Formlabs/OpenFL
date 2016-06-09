#!/usr/bin/env python
from __future__ import division
import sys
import os
import inspect
from os.path import dirname

# Add parent directory to sys.path so we find OpenFL.
sys.path.append(dirname(dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))

from context import FLP, Printer

GERBER_EXTENSIONS = ('.gbl', '.gbs', '.gtl')

import numpy as np

def image_to_laser_moves_xy_mm_dt_s_mW(image, M, 
                                       mmps=294.0, 
                                       powerThreshold_mW=0.0, 
                                       doFilter=False,
                                       max_seg_length_mm=5.0):
    """
    Given an image and a transform, rasterize the image.
    Returns an array of shape nx4 where each row is dt_s, x_mm, y_mm, mW.
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
    result_mm_s_mW = []
    result_mm_s_mW.append((0.0, 0.0, 0.0, 0.0))
    for i, (xy_mm, mW) in enumerate(zip(xy.T, image)):
        prev_xy_mm = result_mm_s_mW[-1][:2]
        direction = xy_mm - prev_xy_mm
        dist_mm = np.linalg.norm(direction)
        dt_s = dist_mm / mmps
        result_mm_s_mW.append((xy_mm[0], xy_mm[1], dt_s, mW))

    xy_mm = np.array((0.0, 0.0))
    dist_mm = np.linalg.norm(xy_mm - result_mm_s_mW[-1][:2])
    dt_s = dist_mm / mmps
    result_mm_s_mW.append((xy_mm[0], xy_mm[1], dt_s, 0.0))
    # Filter result_mm_s_mW to exclude straight lines.
    normalized = lambda x: np.asarray(x) / np.linalg.norm(x)
    if len(result_mm_s_mW) <= 3 or not doFilter:
        return np.array(result_mm_s_mW)

    filtered_mm_s_mW = [result_mm_s_mW[0]]
    sum_dt_s = 0.0
    mW = result_mm_s_mW[0][3]
    for seg_i in range(1, len(result_mm_s_mW)):
        # Include seg_i if it is a different power than the last seg included.
        sum_dt_s += result_mm_s_mW[seg_i-1][2]
        # See if this segment has a different power.
        seg_mm = np.linalg.norm(np.array(filtered_mm_s_mW[-1][:2]) - result_mm_s_mW[seg_i-1][:2])
        if abs(result_mm_s_mW[seg_i][3] - mW) > powerThreshold_mW or seg_mm > max_seg_length_mm:
            # This segment has a different power, so add the first
            # point of this segment, with the last power and the sum time.
            # That constitutes the previous-power line segment.
            # Now start summing up the new segment.
            if mW == 0.0:
                dist_mm = np.linalg.norm(np.array(filtered_mm_s_mW[-1][:2]) - result_mm_s_mW[seg_i-1][:2])
                sum_dt_s = dist_mm / mmps
            filtered_mm_s_mW.append(tuple(result_mm_s_mW[seg_i-1][:2]) + (sum_dt_s, mW))
            sum_dt_s = 0.0
            mW = result_mm_s_mW[seg_i][3]

    filtered_mm_s_mW.append(tuple(result_mm_s_mW[-1][:2]) + (sum_dt_s, mW))
    return np.array(filtered_mm_s_mW)


def __samplesToFLP(dtxypower, xymmToDac=None):
    clock_Hz = 60e3
    xytickspmm = float(0xffff) / 125
    lastPower = None
    xyticks = []
    import numpy as np
    dtxypower = np.asarray(dtxypower)
    result = FLP.Packets()
    result.append(FLP.TimeRemaining(int(sum(dtxypower[:,0]))))
    import numpy as np
    if xymmToDac is None:
        tickspmm = float(0xffff)/125.0
        midticks = float(0xffff)/2
        xyToTicks = np.array([[tickspmm, 0, midticks],
                              [0, tickspmm, midticks],
                              [0, 0, 1]])
        def xymmToDac(x_mm, y_mm):
            xy_ticks = xyToTicks.dot((x_mm, y_mm, 1))
            x_ticks, y_ticks = xy_ticks[:2] / xy_ticks[-1]
            return x_ticks, y_ticks
    xydtmW = Printer.sample_line_segment_mm_s(start_xy_mm=dtxypower[0,1:3],
                                              xys_mm=dtxypower[1:,1:3],
                                              dts_s=dtxypower[1:,0],
                                              mW=dtxypower[1:,3])
    # Use the starting row, then interpolate elsewhere.
    dtxypower = np.vstack([dtxypower[:1],
                           np.hstack([xydtmW[:,2], xydtmW[:,:2], xydtmW[:,3]])
                          ])
    for dt_s, x_mm, y_mm, power in dtxypower:
        if power != lastPower:
            if xyticks:
                result.append(FLP.XYMove(xyticks))
                xyticks = []
            result.append(FLP.LaserPowerLevel(power))
            lastPower = power
        xy_ticks = xymmToDac(x_mm, y_mm)
        dt_ticks = dt_s * clock_Hz
        # Deal with potential that the move takes too long to fit in one step:
        for i in range(int(dt_ticks // 0xffff)):
            alpha = (i+1) * 0xffff / dt_ticks 
            x = np.interp(alpha, [0.0, 1.0], [lastxy_ticks[0], xy_ticks[0]])
            y = np.interp(alpha, [0.0, 1.0], [lastxy_ticks[1], xy_ticks[1]])
            xyticks.append((x, y, 0xffff))
        dt_ticks %= 0xffff # Now we just have to do the last little bit.
        xyticks.append(tuple(xy_ticks) + (dt_ticks,))
        lastxy_ticks = xy_ticks
    if xyticks:
        result.append(FLP.XYMove(xyticks))
    return result


def png_to_flp(pngfilename, flpfilename, printer, pixel_mm=0.1, mmps=295.0, mW=31.0,
               invert=False,
               tile=(1,1)):
    from scipy.ndimage import imread
    if isinstance(pngfilename, basestring):
        image = imread(pngfilename)
        if image.ndim == 3:
            image = image.mean(axis=-1)
    else:
        image = np.array(pngfilename)
        if image.ndim != 2:
            raise TypeError('pngfilename must be a 2D image or a filename.')
    image /= image.max()
    image[image < 0.5] = 0.0 # Throw out noise/edges, etc.
    image[image >= 0.5] = 1.0
    if invert:
        image = 1.0 - image
    image *= mW
    M = np.diag((pixel_mm,pixel_mm,1))+[[0,0,0.1],[0,0,0.05],[0,0,0]]
    image = np.tile(image, tile)
    result_xy_mm_dt_s_mW = image_to_laser_moves_xy_mm_dt_s_mW(image, M, mmps=mmps, doFilter=True)
    # Center:
    lo = result_xy_mm_dt_s_mW[:,:2].min(axis=0)
    hi = result_xy_mm_dt_s_mW[:,:2].max(axis=0)
    result_xy_mm_dt_s_mW[:,:2] -= [(lo + hi)/2]
    data = printer.samples_to_FLP(xy_mm_dts_s_mW=result_xy_mm_dt_s_mW)
    data.tofile(flpfilename)
    return data, result_xy_mm_dt_s_mW, image


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


def gerberToPNG(filename, png, pixel_mm=0.1):
    """
    Convert to png.
    Return pixel size in mm.
    """
    import gerber
    from gerber.render import GerberCairoContext

    # Read gerber and Excellon files
    data = gerber.read(filename)
    data.to_metric()
    
    # Rendering context
    ctx = GerberCairoContext(scale=1.0/pixel_mm) # Scale is pixels/mm

    # Create SVG image
    data.render(ctx)
    ctx.dump(png)
    return png, np.mean(data.size) / np.mean(ctx.size_in_pixels)

def convertToTmpPNG(filename, png, pixel_mm=0.1):
    """
    Convert this image file to a temporary .png.
    Return the file name and pixel size in mm.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext in GERBER_EXTENSIONS:
        return gerberToPNG(filename, png, pixel_mm=pixel_mm)
    raise Exception('Unsupported file type: {} in {}'.format(ext, filename))
    

def image_to_flp(imagefilename, flpfilename, pixel_mm=0.1, **kwargs):
    import sys
    isGerber = os.path.splitext(imagefilename.lower())[1] in GERBER_EXTENSIONS
    if not imagefilename.endswith('.png'):
        import tempfile
        fh = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        imagefilename, pixel_mm = convertToTmpPNG(imagefilename, fh.name, pixel_mm=pixel_mm)
    assert flpfilename.endswith('.flp')
    return png_to_flp(imagefilename, flpfilename, pixel_mm=pixel_mm, **kwargs)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Convert an image to a single-layer flp file.')
    parser.add_argument('inImageFilename', nargs=1)
    parser.add_argument('outFLPFilename', nargs=1)
    args = parser.parse_args()

    inImageFilename = args.inImageFilename
    outFlpFilename = args.outFLPFilename
    try:
        p = Printer.Printer()  
    except RuntimeError:
        sys.stderr.write('Failed to connect to a printer. \n' + 
                         'A printer is required to have a laser calibration.\n')
        sys.exit(1)

    image_to_flp(inImageFilename, outFlpFilename,
                 printer=p)
