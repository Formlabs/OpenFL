# -*- coding: utf-8 -*-
"""
FLP.py

A library to read, modify, and write Formlabs FLP files for Form 1 and Form 1+.

Copyright 2016 Formlabs

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import division
import struct
import inspect
import sys

class Packet(object):
    """
    Parent class of all flp packets.
    CMD is the command number
    COUNT is the number of items
    dtype is the struct format
    data is the contents; if COUNT is zero, data is None.
    """
    CMD = None
    COUNT = 1
    dtype = 'B'

    def __init__(self):
        self.data = self.DEFAULT_DATA

    def __eq__(self, other):
        return (self.CMD == other.CMD and
                self.COUNT == other.COUNT and 
                self.dtype == other.dtype and 
                self.data == other.data)

    @property
    def DEFAULT_DATA(self):
        if self.COUNT == 0:
            return None
        elif self.COUNT == 1:
            return 0
        else:
            s = struct.Struct(self.dtype * self.COUNT)
            return s.unpack('\0' * s.size)

    @classmethod
    def fromstring(cls, data):
        self = cls()
        self._make_fromstring(data)
        return self
    def _make_fromstring(self, data):
        if self.COUNT == 0:
            self.data = None
            return self
        if False and hasattr(self, 'dtype') and self.dtype:
            s = struct.Struct('<{}'.format(self.dtype))
            self.data = s.unpack_from(s.pack(data))
            if len(self.data) == 0:
                self.data = self.data[0]
        else:
            if 's' in self.struct.format: # It's a string.
                assert len(data) == 1
                assert len(data[0]) == self.struct.size
                data = data[0]
            self.data = data
        return self

    @classmethod
    def fromfile(PacketType, fileHandle):
        s = PacketType.struct
        data = s.unpack_from(fileHandle.read(s.size))
        if PacketType.COUNT == 1:
            data = data[0]
        return PacketType.fromstring(data)

    def tostring(self):
        """Convert to binary string."""
        result = struct.pack('B', self.CMD)
        if self.data is not None:
            if self.COUNT == 1:
                return result + self.struct.pack(self.data)
            return result + self.struct.pack(*self.data)

        return result

    def __str__(self):
        return '0x{:>02x} {} {}'.format(self.CMD,
                                        self.__class__.__name__,
                                        self.data if self.data is not None else '')
    def _reprContents(self):
        """
        Override this to provide something else
        in the repr represention of the thing.
        """
        if self.data is None:
            return ''
        return self.data

    def __repr__(self):
        return '<{}({}) at 0x{:x}>'.format(self.__class__.__name__,
                                           self._reprContents(),
                                           id(self))

class MotorCommand(Packet):
    """Parent class for all motor commands"""
    pass

class LaserCommand(Packet):
    """Parent class for all laser commands"""
    pass

class SliceCommand(Packet):
    """Parent class for layer start and layer done."""
    pass

class XYMove(LaserCommand):
    """
    A sequence of laser moves.
    """
    __slots__ = '_points'
    CMD = 0x00
    dtype = 'H'
    rowstruct = struct.Struct('<HHH')

    def __init__(self, xyticks=[]):
        for row in xyticks:
            if len(row) != 3:
                raise TypeError('All rows must be x, y, dt (ticks); got {}'.format(repr(row)))
        self.points = [(int(x), int(y), int(ticks)) for x, y, ticks in xyticks]

    def _make_fromstring(self, data):
        self = super(XYMove, self)._make_fromstring(data)
        self._points = []
        return self

    def _reprContents(self):
        return '{} points'.format(len(self.points))

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, points):
        self._points = points
        self.data = len(points)

    @property
    def npoints(self):
        return len(self.points)

    @classmethod
    def fromfile(PacketType, fileHandle):
        s = PacketType.struct
        data = s.unpack_from(fileHandle.read(s.size))
        assert PacketType.COUNT == 1
        data = data[0]
        packet = PacketType.fromstring(data)

        packet.points = tuple(packet.rowstruct.unpack(fileHandle.read(packet.rowstruct.size))
                              for i in range(packet.data))

        return packet

    def tostring(self):
        """Convert to binary string."""
        assert self.data == self.npoints
        return (super(XYMove, self).tostring() +
                ''.join(self.rowstruct.pack(*row) for row in self.points))

    def __str__(self):
        result = super(XYMove, self).__str__()
        return result + '\n'.join(str(p) for p in self.points)

    def _addPointFromFile(self, fileHandle):
        self.points.append(self.rowstruct.unpack(fileHandle.read(self.rowstruct.size)))


class LaserPowerLevel(LaserCommand):
    """
    A command to change the laser power in laser power units.
    """
    CMD = 0x01
    dtype = 'H'

    def __init__(self, power_ticks = 0):
        self.data = int(power_ticks)

    @property
    def power(self):
        return self.data


class XYMoveClockRate(LaserCommand):
    """
    The clock rate for the laser commands in Hz.
    This should always be 60,000.
    """
    CMD = 0x02
    dtype = 'I'
    DEFAULT_DATA = 60000 # This is the only supported clock rate.

    @staticmethod
    def moverate_Hz(): 
        return XYMoveClockRate.DEFAULT_DATA

    def _reprContents(self):
        return '{} Hz'.format(self.moverate_Hz)

class MotorMoveCommand(MotorCommand):
    """
    Command the {} motor to move the
    given number of usteps at its predetermined feedrate.
    """
    dtype = 'i'
    def __init__(self, usteps=0):
        if not int(usteps) == usteps:
            raise TypeError('usteps must be an integer, otherwise you are asking for round')
        self.usteps = int(usteps)

    @property
    def usteps(self):
        return self.data

    @usteps.setter
    def usteps(self, usteps):
        self.data = int(usteps)

    def _reprContents(self):
        return '{} usteps'.format(self.usteps)

class MotorFeedRate(MotorCommand):
    """Update the {} feed rate in microsteps per second."""
    dtype = 'I'
    def __init__(self, usteps_per_s=0):
        self.usteps_per_s = usteps_per_s

    @property
    def feedrate(self):
        return self.data

    @property
    def usteps_per_s(self):
        return self.data

    @usteps_per_s.setter
    def usteps_per_s(self, usteps_per_s):
        self.data = int(usteps_per_s)

    def _reprContents(self):
        return '{} usteps/s'.format(self.feedrate)

class MotorCurrent(MotorCommand):
    """Change the {} motor current."""
    dtype = 'B'
    moving_current = 80
    idle_current = 40

    def __init__(self, current=None, moving=None):
        if current is not None and moving is not None:
            raise TypeError('Must be constructed with either a current or moving=True or moving=False.')
        if current is None:
            current = MotorCurrent.moving_current if moving else MotorCurrent.idle_current
        self.current = current

    @property
    def current(self):
        return self.data

    @current.setter
    def current(self, current):
        self.data = int(current)

class ZMove(MotorMoveCommand):
    __doc__ = MotorMoveCommand.__doc__.format('z')
    usteps_up_per_mm = 400.0
    CMD = 0x03

class ZFeedRate(MotorFeedRate):
    __doc__ = MotorFeedRate.__doc__.format('z')
    CMD = 0x04

class ZCurrent(MotorCurrent):
    __doc__ = MotorCurrent.__doc__.format('z')
    CMD = 0x05

class TiltMove(MotorMoveCommand):
    __doc__ = MotorMoveCommand.__doc__.format('tilt')
    CMD = 0x06

class TiltFeedRate(MotorFeedRate):
    __doc__ = MotorFeedRate.__doc__.format('tilt')
    CMD = 0x07

class TiltCurrent(MotorCurrent):
    __doc__ = MotorCurrent.__doc__.format('tilt')
    CMD = 0x08


class Dwell(Packet):
    """
    Pause execution (sleep) for the given number of milliseconds.
    In-progress motor moves are not interrupted.
    """
    CMD = 0x09
    dtype = 'I'

    def __init__(self, ms=None, s=None):
        if ms is not None:
            self.data = int(ms)
            assert s is None
        elif s is not None:
            self.data = int(s * 1000)
        else:
            self.data = int(0)

    @property
    def duration_ms(self):
        return self.data

    @property
    def duration_s(self):
        return self.duration_ms / 1000.0

    def _reprContents(self):
        return '{} ms'.format(self.duration_ms)

class WaitForMovesToComplete(MotorCommand):
    """Block until all moves finish."""
    CMD = 0x0a
    dtype = None
    COUNT = 0

class LaserCalibration(LaserCommand):
    # FIXME: What does this do?
    CMD = 0x0b
    dtype = 'H'
    COUNT = 3
    
    @property
    def laserCal(self):
        return self.data

class LayerStart(SliceCommand):
    """
    Note that a new layer is starting.
    """
    CMD = 0x10
    dtype = 'I'

    def __init__(self, layernumber=None):
        if layernumber is None:
            s = struct.Struct(self.dtype * self.COUNT)
            layernumber, = s.unpack('\xff' * s.size)
        self.data = layernumber

    @property
    def layernumber(self): return self.data

class LayerDone(SliceCommand):
    """
    Note that the current layer is finished.
    """
    CMD = 0x11
    dtype = None
    COUNT = 0

class TimeRemaining(Packet):
    """
    Update the time remaining.
    """
    CMD = 0x12
    dtype = 'I'
    DEFAULT_DATA = 0

    def __init__(self, timeremaining_s=None):
        if timeremaining_s is None:
            timeremaining_s = self.DEFAULT_DATA
        self.data = int(timeremaining_s)

    @property
    def timeremaining_s(self): return self.data # FIXME: Units?

    def _reprContents(self):
        return '{} s'.format(self.timeremaining_s)

class WaitButtonPress(Packet):
    """
    Display three 24-byte lines of text and wait for button press.
    """
    CMD = 0x13
    COUNT = 24 * 3
    dtype = 's'
    def __init__(self, string=''):
        self.string = string
    @property
    def data(self):
        result = self.string[:self.COUNT]
        return result + '\0' * (self.COUNT - len(result))
    @data.setter
    def data(self, string):
        assert len(string) <= self.COUNT
        self.string = string

    def tostring(self):
        return struct.pack('B', self.CMD) + self.data

class ShakeTimer(Packet):
    CMD = 0x14
    dtype = 'I'
    count = 2

class CalibrationThreshold(Packet):
    CMD = 0x20
    dtype = 'H'

    @property
    def thresh(self): return self.data

class AbstractStringCommand(Packet):
    """There are two commands that both contain one 64-byte string."""
    dtype = 's'
    COUNT = 64

    def __init__(self, string=''):
        if len(string) > self.COUNT:
            raise TypeError('String too long {} > {}'.format(len(string), self.COUNT))
        self.data = string + '\0' * (self.COUNT - len(string))

    @property
    def string(self): return self.rawstring.strip('\0')

    @property
    def rawstring(self):
        return self.data

    def tostring(self):
        return struct.pack('B', self.CMD) + self.data

    def __str__(self):
        return '0x{:>02x} {} {}'.format(self.CMD,
                                        self.__class__.__name__,
                                        repr(self.string.strip('\0')))

    def _reprContents(self):
        return repr(self.string)



class SerialPrintCommand(AbstractStringCommand):
    """Print a string to the serial header."""
    CMD = 0x22

class NopCommand(AbstractStringCommand):
    """
    Do nothing.
    This allows adding comments, tags, debugging output, etc. to flp files.
    """
    CMD = 0x23

class SerialPrintClockCommand(Packet):
    """
    Print the current system clock time to the serial header.
    This allows compensating for clock drift between the
    printer and a computer gathering data.
    The serial output will look like "clock: 328756936\n" 
    where the time is in ms.
    """
    CMD = 0x24
    dtype = None
    COUNT = 0

class WaitOnPinCommand(Packet):
    """
    Like Dwell: suspend execution until input pin goes high.
    Right now only pin 17 is supported.
    """
    CMD = 0x25
    dtype = 'B'
    COUNT = 1
    DEFAULT_DATA = 17



def __setupNumToPacket():
    """This is a function to avoid leaking temproaries into this module."""
    # See:
    # http://stackoverflow.com/questions/1796180/python-get-list-of-all-classes-within-current-module
    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    # packet lists all Packet classes:
    packets = [cls for _, cls in clsmembers if issubclass(cls, Packet)]
    for p in packets:
        p.struct = struct.Struct('<{}{}'.format(p.COUNT, p.dtype)
                                 if p.dtype else '')

    numToPacketDict = dict((p.CMD, p) for p in packets if p.CMD is not None)
    # Now convert it to a tuple for faster indexing. (This was profiled and really does help.)
    ntp = [None] * (1 + max(numToPacketDict.keys()))
    for k, v in numToPacketDict.items():
        if isinstance(k, int):
            ntp[k] = v
    return tuple(ntp)

numToPacket = __setupNumToPacket()

def parsePacket(fh):
    """
    Given an open file handle, read out the next flp Packet.
    """
    try:
        cmd = ord(fh.read(1))
    except TypeError:
        raise EOFError # ord raises TypeError when called on empty string.
    try:
        PT = numToPacket[cmd]
    except IndexError:
        raise IndexError('Invalid command: {} (0x{:x})'.format(cmd, cmd))
    return PT.fromfile(fh)


class Packets(list):
    """
    A list of packets. This represents a file or collection of files.
    """
    def __init__(self, *a, **k):
        super(Packets, self).__init__(*a, **k)
        for packet in self:
            if not isinstance(packet, Packet):
                raise TypeError('Packets must all be FLP Packets. Got {}'.format(type(packet)))

    def __getslice__(self, *a, **k):
        return Packets(super(Packets, self).__getslice__(*a, **k))
    def __add__(self, *a, **k):
        return Packets(super(Packets, self).__add__(*a, **k))

    def gen_packets(self, types=object):
        """Generate packets matching the given type."""
        for p in self:
            assert isinstance(p, Packet)
            if isinstance(p, types):
                yield p
    def moves(self):
        """Generate all xy moves."""
        for p in self.gen_packets(XYMove):
            yield p
    def __str__(self):
        return '\n'.join(str(packet) for packet in self)

    @staticmethod
    def fromstring(string):
        """Load all the packets in a string buffer."""
        import StringIO
        return fromfile(StringIO.StringIO(string))

    @staticmethod
    def fromfile(fileHandle):
        """Load all the Packets in the given file."""
        if isinstance(fileHandle, basestring):
            import os
            extension = os.path.splitext(fileHandle)[1].lower()
            assert extension == '.flp', ('Packets.fromfile takes a file ' +
                                         'handle or a .flp file name, not ' +
                                         'a {} file name.').format(extension)
            with open(fileHandle, 'rb') as fh:
                return Packets.fromfile(fh)
        flp = Packets()
        while fileHandle:
            try:
                flp.append(parsePacket(fileHandle))
            except EOFError: break
        return flp

    def tostring(self):
        """Stringify all Packets for serialization."""
        return ''.join(cmd.tostring() for cmd in self)

    def tofile(self, fileHandle):
        """Write to a file."""
        if isinstance(fileHandle, basestring):
            with open(fileHandle, 'wb') as fh:
                self.tofile(fh)
        else:
            fileHandle.write(self.tostring())



def makeHomingSequence():
    """Return Packets that home the motors."""
    # SET MOTORS TO MOVING CURRENT
    result = Packets()
    result.append(TiltCurrent(moving=True))
    result.append(ZCurrent(moving=True))

    # LEVEL tank

    # send tank all the way up
    result.append(TiltFeedRate(usteps_per_s=1600))
    result.append(TiltMove(usteps=-6000))
    #page.setString(Page::BOTTOM_ROW, "Moving tank up...");
    result.append(WaitForMovesToComplete())

    # make sure tank is really all the way up
    result.append(TiltFeedRate(usteps_per_s=94))
    result.append(TiltMove(usteps=-157))
    result.append(WaitForMovesToComplete())

    #// skip peel/raise/unpeel procedure if platform is already raised

    # Note: we have to move the tilt motor up first so we don't drive the screw out of the motor.
    # NICE SLOW PEEL
    result.append(TiltFeedRate(usteps_per_s=400))
    result.append(TiltMove(usteps=4000))
    result.append(WaitForMovesToComplete())

    # RAISE PLATFORM

    # Raise the platform
    result.append(ZFeedRate(usteps_per_s=10000))
    result.append(ZMove(usteps=200000))
    result.append(WaitForMovesToComplete())
    # Wait until the Z motor hits the upper stop or times out

    # PUT tank BACK UP

    # send tank go all the way up
    result.append(TiltFeedRate(usteps_per_s=1600))
    result.append(TiltMove(usteps=-6000))
    result.append(WaitForMovesToComplete())

    # make sure tank is really all the way up
    result.append(TiltFeedRate(usteps_per_s=94))
    result.append(TiltMove(usteps=-157))
    result.append(WaitForMovesToComplete())
    return result
 

def mergeFLPs(motorAndLaserMoves, *otherMoves):
    """Given two or more Packets objects,
    return a new Packet object containing the first
    one with all laser moves of the others injected after
    the last laser move."""
    result = Packets()
    try:
        lastMoveCmd = max(i for i, cmd in enumerate(motorAndLaserMoves) if isinstance(cmd, XYMove))
    except ValueError:
        lastMoveCmd = -1 # No XYMove commands => end of file
    result.extend(motorAndLaserMoves[:lastMoveCmd + 1])
    for flp in otherMoves:
        result.extend(cmd for cmd in flp if isinstance(cmd, LaserCommand))
    result.extend(motorAndLaserMoves[lastMoveCmd + 1:])
    return result

def getLaserCommands(*motorAndLaserMoves):
    result = Packets()
    for flp in motorAndLaserMoves:
        for cmd in flp:
            if isinstance(cmd, (LaserCommand, SliceCommand)):
                result.append(cmd)
    return result


def fromfile(f):
    """Load all the Packets in the given file."""
    return Packets.fromfile(f)


def fromstring(string):
    """Load all the packets in a string buffer."""
    return Packets.fromstring(string)
