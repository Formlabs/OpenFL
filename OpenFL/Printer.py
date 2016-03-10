from __future__ import division
import ctypes
import errno
import io
import struct
import time

try:    # Python 2
    import ConfigParser as configparser
except ImportError:
    import configparser

import usb.core
import numpy as np
import scipy.interpolate

from OpenFL import FLP

################################################################################

class DecodeError(RuntimeError):
    pass
class BadResponse(RuntimeError):
    pass
class LaserPowerError(RuntimeError):
    pass

class Printer(object):
    """ Instantiation of a printer object
    """
    # VID and PID for the Form 1 and Form 1+
    VID = 0x16d0
    PID = 0x07eb

    # Endpoint numbers for TX and RX
    TX_EP = 0x81    # Printer -> computer
    RX_EP = 0x03    # Computer -> printer

    SOF = 0xFF  # Special character marking the beginning of a transmission
    EOF = 0xFE  # Special character marking the end of a transmission
    ESCAPE = 0xFD   # Character used to escape special characters in a bytestring

    AUDIT_LASER_POWER = True
    LASER_POWER_MAX_MW = 62

    def __init__(self, connect=True):
        if connect:
            self.dev = usb.core.find(idVendor=self.VID, idProduct=self.PID)
            if self.dev is None:
                raise RuntimeError("Could not find printer")
            self.dev.default_timeout = 100
            try:
                self.dev.set_configuration()
            except usb.USBError as e:
                e.strerror += ". Be sure PreForm is closed."
                raise
        self.incoming = []
        self.packet = bytearray()

        # These values are loaded from the printer as-needed
        self._laser_table = None
        self._grid_table = None

    def _read(self, bufsize=1024):
        """ Reads raw data from the printer's usual endpoint
        """
        return bytearray(self.dev.read(self.TX_EP, bufsize))

    def _write(self, data):
        """ Writes raw data to the printer's usual endpoint
        """
        return self.dev.write(self.RX_EP, data)

    @classmethod
    def _decode(cls, received):
        """ Strips the escape characters from streamed data
        """
        out = b''
        escaping = False
        for byte in received:
            if escaping:
                out += bytearray([byte + cls.ESCAPE])
                escaping = False
            elif byte == cls.ESCAPE:
                escaping = True
            else:
                out += bytearray([byte])
        return out

    @classmethod
    def _encode(cls, payload):
        """ Protects a stream of data with escape characters
            The payload should be a bytestring
        """
        out = b''
        for byte in payload:
            if byte >= cls.ESCAPE:
                out += bytearray([cls.ESCAPE])
                byte = ctypes.c_uint8(byte - cls.ESCAPE).value
            out += bytearray([byte])
        return out

    @classmethod
    def _interpret(cls, cmd, data):
        """ Applies a command-specific interpretation to the data
                cmd is a Command object
                data is a decoded packet
        """
        if cmd == Command.CMD_MACHINE_STATE:
            return State(data[0])

        # Layer and block done return the layer / block number
        elif cmd in [Command.STATUS_LAYER_DONE, Command.STATUS_BLOCK_DONE]:
            return struct.unpack('<I', data)[0]

        # Assume one-byte responses to be a standard error code
        # (unless specified above)
        elif len(data) == 1:
            return Response(data[0])
        else:
            return data if data else None

    def _process_raw(self, data):
        """ Processes a stream of raw data, breaking it into packets
            Packets are stored as (Command, Payload) tuples in self.incoming
        """
        self.packet += data

        # Trim data off the front until we find a SOF character
        while self.packet[0] != self.SOF:
            self.packet.pop(0)

        # Process the packet, loading data into self.incoming
        while self.packet:
            cmd = Command(self.packet[1])

            # If the packet contains an EOF character, then read in the
            # full packet and store it in the incoming buffer
            try:
                p, self.packet = self.packet[2:].split(bytearray([self.EOF]), 1)
            except ValueError:
                break
            else:
                self.incoming.append(
                        (cmd, self._interpret(cmd, self._decode(p))))

    def _command(self, cmd, payload=b'', wait=True, expect_success=False):
        """ Transmits a command to the printer
            The command is wrapped in the form SOF, cmd, encode(payload), EOF

            If wait is true, waits for the acknowledgment
                (in the form of a returned packet with cmd)
            wait can also be a list of valid returned packet Commands
                (for commands with multiple return options)

            If expect_success is True and the returned response is not SUCCESS,
            raises a BadResponse error with the Response code.
        """
        self._write(bytearray([self.SOF, cmd.value])
                    + self._encode(payload) + bytearray([self.EOF]))
        if wait is True:
            wait = [cmd]

        if wait:
            r = self._wait_for_packet(wait)
            if expect_success and r != Response.SUCCESS:
                raise BadResponse(r)
            return r
        else:
            return None

    def _wait_for_packet(self, cmd, verbose=True):
        """ Waits for a returned packet of the given type(s).
                Returns the packet's payload.
                If verbose is True, prints all packets received while waiting
        """
        if isinstance(cmd, Command):
            cmd = [cmd]
        while True:
            p = self.poll()
            if verbose and p is not None:
                # Truncate bytearrays to prevent huge printouts
                if type(p[1]) is bytearray:
                    print("(%s, <%i byte payload>)" % (p[0], len(p[1])))
                else:
                    print(p)
            if p is not None and p[0] in cmd:
                return p[1]

    def poll(self, bufsize=1024):
        """ Returns the next received packet as a tuple (command, payload)
            If there are no packets pending, returns None
        """
        # Attempt to load data from USB and push it into the incoming buffer
        while not self.incoming:
            try:
                raw = self._read(bufsize)
            except usb.core.USBError as e:
                # The only acceptable USB errors are timeout errors
                # (when the device hasn't sent us any new data)
                if e.errno != errno.ETIMEDOUT:
                    raise e
                break
            else:
                self._process_raw(raw)

        # Return the oldest packet or None
        return self.incoming.pop(0) if self.incoming else None

    def initialize(self):
        """ Runs the printer through its initialization sequence:
                Stops any print or operation
                Resets the machine
                Sets laser current to zero
                Sets galvo position to 0, 0
                Homes Z axis against limit switch and rams tilt against hard stop
                Sets feed rates to default values
        """
        self._command(Command.CMD_INITIALIZE, expect_success=True)

    def shutdown(self):
        """ Turns off all parts of the printer other than the processor
        """
        self._command(Command.CMD_SHUTDOWN, expect_success=True)

    def list_blocks(self):
        """ Lists blocks on the printer, returning an array of integers
        """
        data = self._command(Command.CMD_LIST_BLOCKS)
        num = struct.unpack('<I', data[:4])[0]
        return struct.unpack('<%iI' % num, data[4:])

    def delete_block(self, block, end=None):
        """ Removes a block by number
            If end is given, deletes from block to end (inclusive)
        """
        if end is None:
            end = block
        self._command(Command.CMD_DELETE_BLOCKS,
                      bytearray(struct.pack('<II', block, end)),
                      expect_success=True)

    def read_block(self, block):
        """ Reads a block by number
        """
        data = self._command(Command.CMD_READ_BLOCK,
                bytearray(struct.pack('<I', block)),
                wait=[Command.CMD_READ_BLOCK, Command.CMD_READ_BLOCK_DATA])

        # If we got a response code, return it immediately
        if isinstance(data, Response):
            return data

        # Extract block and count from the returned data
        block_received, count = struct.unpack('<II', data[:8])

        # Sanity-check responses
        if block_received != block:
            raise BadResponse("Block received was not block requested")
        elif count != len(data) - 12:
            raise BadResponse("Didn't receive enough data in the block")

        # Return the data section of the block, stripping the trailing CRC
        return data[8:-4]

    def read_block_flp(self, block):
        return FLP.fromstring(self.read_block(block))

    @staticmethod
    def _fletcher32(data):
        """ As it turns out, the firmware doesn't implement CRC checking.
        """
        return 0

    def audit_laser_power_flp(self, flp):
        """ Raise if the FLP has unsafe powers.
        """
        for p in flp:
            if isinstance(p, FLP.LaserPowerLevel):
                self.check_laser_ticks(p.power)

    def check_laser_ticks(self, power):
        """ Raises if the power (in laser ticks) is above our safe threshold
        """
        mW = self.ticks_to_mW(power)
        if mW > self.LASER_POWER_MAX_MW:
            raise LaserPowerError('Requested power is dangerously high.')

    def write_block(self, block, data, skip_audit=False):
        """ Writes a block.
                block is an integer
                data is a bytearray, filename, or FLP.Packets object
        """
        if isinstance(data, FLP.Packets):
            assert skip_audit == False
            return self.write_block_flp(block, data)
        if not isinstance(data, bytearray):
            data = bytearray(open(data, 'rb').read())

        # Check to see that laser power is always acceptable,
        # raising an exception if the power is too high
        if self.AUDIT_LASER_POWER and not skip_audit:
            flp = FLP.fromstring(data)
            self.audit_laser_power_flp(flp)

        header = bytearray(
                struct.pack('<III', block, len(data), self._fletcher32(data)))
        self._command(Command.CMD_LOAD_PRINT_DATA_BLOCK, header + data,
                      expect_success=True)

    def write_block_flp(self, block, flp):
        """ Writes FLP data to a block.
                block is an integer
                flp is a FLP.Packets object
        """
        if not isinstance(flp, FLP.Packets):
            raise TypeError("flp must be a FLP.Packets instance; got a {}.".format(type(flp)))
        if self.AUDIT_LASER_POWER:
            self.audit_laser_power_flp(flp)
        self.write_block(block, bytearray(flp.tostring()), skip_audit=True)

    def block_size(self, block):
        """ Returns block size (in bytes) of the target block
        """
        data = self._command(Command.CMD_BLOCK_INFORMATION,
            bytearray(struct.pack('<I', block)))
        block_received, size, crc = struct.unpack('<III', data)
        if block_received != block:
            raise BadResponse("Block received was not block requested")
        return size

    def _read_cal_field(self, cmd):
        """ Reads a calibration field from the printer
            command must be CMD_READ_LASER_TABLE, CMD_READ_GRID_TABLE, or
            CMD_READ_ZSENSOR_HEIGHT
        """
        data = self._command(cmd)

        if isinstance(data, Response):
            return data

        # Extract block and count from the returned data
        count = struct.unpack('<I', data[:4])[0]

        # Sanity-check responses
        if count != len(data) - 8:
            raise BadResponse("Didn't receive enough data in the block")

        # Return the data section of the block, stripping the trailing CRC
        # and evaluating to get a list of lists
        return eval(str(data[4:-4]))

    def read_laser_table(self):
        """ Reads the printer's laser table
        """
        return self._read_cal_field(Command.CMD_READ_LASER_TABLE)

    def read_grid_table(self):
        """ Reads the printer's laser table
        """
        return self._read_cal_field(Command.CMD_READ_GRID_TABLE)

    def read_zsensor_height(self):
        """ Reads the printer's Z height
        """
        return self._read_cal_field(Command.CMD_READ_ZSENSOR_HEIGHT)

    def state(self):
        """ Checks the printer's state, returning a State object
        """
        return self._command(Command.CMD_MACHINE_STATE)

    def _wait_for_state(self, state=None, dt=0.1):
        """ Blocks until the printer's state machines the input state
                state is a State or list of States
                dt is the polling interval
        """
        if state is None:
            state = State.MACHINE_READY_TO_PRINT
        if not hasattr(state, '__iter__'):
            state = [state]
        while self.state() not in state:
            time.sleep(dt)

    def start_printing(self, block, end=None):
        """ Begins printing from the given block, returning immediately

            The printer may receive the following packets while printing:
                STATUS_LAYER_DONE
                STATUS_LAYER_NON_FATAL_ERROR
                STATUS_BLOCK_DONE
                STATUS_PRINT_DONE
        """
        if end is None:
            end = block + 1
        if end <= block:
            raise RuntimeError("end must be > block")
        self._command(Command.CMD_START_PRINTING,
                      bytearray(struct.pack('<II', block, end)),
                      expect_success=True)

    def stop_printing(self):
        """ Stops a print in progress
            Turns the laser off and stops any in-progress galvo and motor moves
        """
        self._command(Command.CMD_STOP_PRINTING, expect_success=True)

    def pause_printing(self):
        """ Sets the pause flag on the printer.

            When the pause flag is set, the printer will pause at the next
            layer end command.

            A paused printer stops executing its current block and waits for
            debug commands
        """
        self._command(Command.CMD_PAUSE_PRINTING, expect_success=True)

    def unpause_printing(self):
        """ Clears the pause flag on the printer.
        """
        self._command(Command.CMD_UNPAUSE_PRINTING, expect_success=True)

    def move_z(self, steps, feedrate, current=80):
        """ Moves the Z stepper a certain number of steps
                steps is a signed number of microsteps to move
                feedrate is speed in microsteps per second
                current is the current value (at a scale of 80 per amp)

            The motor driver will current-limit and turn off if the current
            is too high (about 160)
        """
        self._command(Command.CMD_MOVE_Z_STEPPER_INCREMENTAL,
            bytearray(struct.pack('<iIB', steps, feedrate, current)),
            expect_success=True)

    def set_laser_uint16(self, x, y, power=25000):
        """ Sets the position and laser power level
                x and y are unsigned 16-bit values (0 to 0xffff)
                    (with 0 at the corner of the platform)
                power is an unsigned 16-bit integer

            Setting power too high can damage your diode!
        """
        if self.AUDIT_LASER_POWER:
            self.check_laser_ticks(power)
        self._command(Command.CMD_POSITION_LASER,
            bytearray(struct.pack('<HHH', x, y, power)),
            expect_success=True)

    def set_laser_sint16(self, x, y, power=25000):
        """ Sets the position and laser power level
                x and y are signed 16-bit values (-32768 to 32767)
                    (with 0 at the center of the platform)
                power is an unsigned 16-bit integer

            Setting power too high can damage your diode!
        """
        return self.set_laser_uint16(x + round(0xffff/2), y + round(0xffff/2), power)

    def set_laser_mm_mW(self, x_mm, y_mm, mW=10):
        """ Sets the laser position in mm and power in mW.
            Position (0, 0) is the center of the field.
        """
        x, y = self.mm_to_galvo(x_mm, y_mm)
        return self.set_laser_uint16(x, y, self.mW_to_ticks(mW))

    def ticks_to_mW(self, ticks):
        """ Given a power number, return the power in mW

            This conversion depends on per-printer calibration.
        """
        if self._laser_table is None:
            self._laser_table = np.asarray(self.read_laser_table())

        return np.interp(ticks,
                         self._laser_table[:,0] * float(0xffff) / 3.3,
                         self._laser_table[:,1])


    def mW_to_ticks(self, mW):
        """ Converts a power in mW to arbitrary laser units

            This conversion depends on per-printer calibration.
            Raises an exception if the desired power is out of range.
        """
        if self._laser_table is None:
            self._laser_table = np.asarray(self.read_laser_table())

        if mW > max(self._laser_table[:,1]):
            raise LaserPowerError(
                    'Requested power (%.2f mW) exceeds max power (%.2f mW)' %
                    (mW, max(self._laser_table[:,1])))

        # Convert to power values with linear interpolation
        result = np.interp(mW, self._laser_table[:,1],
                               self._laser_table[:,0] * float(0xffff) / 3.3)
        if result < 0 or result > 0xffff:
            raise LaserPowerError(
                    'Requested power is not a uint16.  Check power table.')

        return result


    def mm_to_galvo(self, x, y):
        """ Given one or many points in mm space, map them to galvo space.
            e.g.,
            >>> Printer.mm_to_galvo(0, 0) # -> galvo ticks for middle of build area.
            >>> Printer.mm_to_galvo([[0, 1, 2], [0, 0, 0]]) # -> A three-segment line along the x axis.
            The returned array is 2xN, where N is the number of source points
        """
        if self._grid_table is None:
            grid = np.array(self.read_grid_table())
            assert grid.shape == (5, 5, 2)

            pts_mm = np.linspace(-64, 64, 5) # Grid positions in mm

            # Interpolators for X and Y values (mm to galvo ticks)
            fit_x = scipy.interpolate.interp2d(pts_mm, pts_mm, grid[:,:,0])
            fit_y = scipy.interpolate.interp2d(pts_mm, pts_mm, grid[:,:,1])
            self._grid_table = (fit_x, fit_y)

        if np.shape(x) != np.shape(y):
            raise TypeError('x and y shapes must match. Got x.shape: {}, y.shape: {}'.format(np.shape(x), np.shape(y)))

        x = np.atleast_1d(x)
        y = np.atleast_1d(y)

        x_ = [self._grid_table[0](a, b) for a, b in zip(x, y)]
        y_ = [self._grid_table[1](a, b) for a, b in zip(x, y)]

        return np.hstack([x_, y_]).T

    @staticmethod
    def mm_to_galvo_approx(x, y=None):
        """ Given one or many points in mm space, map them to galvo space.
            e.g.,
            >>> Printer.mm_to_galvo(0, 0) # -> galvo ticks for middle of build area.
            >>> Printer.mm_to_galvo([[0, 1, 2], [0, 0, 0]]) # -> A three-segment line along the x axis.
        """
        xy = x
        if y is not None:
            if np.shape(x) != np.shape(y):
                raise TypeError('x and y shapes must match. Got x.shape: {}, y.shape: {}'.format(np.shape(x), np.shape(y)))
            xy = np.array([x, y]) # Allows calling with just an x and a y.
        # These polynomials are a fit to all Form 1/1+s.
        Px = np.array([  3.27685507e+04,   4.80948842e+02,  -1.22079970e-01,
                         -2.88953161e-03,   6.08478254e-01,  -8.81889894e-02,
                         -2.20922460e-05,   4.41734858e-07,   6.76006698e-03,
                         -1.02093319e-05,  -1.43020804e-06,   2.03140758e-08,
                         -6.71090318e-06,  -4.36026159e-07,   2.62988209e-08,
                         8.32187652e-11])
        Py = np.array([  3.27661362e+04,   5.69452975e-01,  -2.39793282e-03,
                         9.83778919e-06,   4.79035581e+02,  -8.13031539e-02,
                         -2.66499770e-03,  -4.40219799e-07,  -1.06247442e-01,
                         5.18419181e-05,   1.47754740e-06,  -1.60049118e-09,
                         -2.44473912e-03,  -1.31398011e-06,   1.83452740e-08,
                         3.16943985e-10])

        xy = np.asarray(xy, dtype=float)
        if xy.shape[0] != 2:
            raise TypeError('xy must be a two-vector or 2xn or 2xmxn... not shape {}.'.format(xy.shape))
        shp = xy.shape[1:] # polyval2d wants vector inputs, not multidimensional.
        return np.array([polyval2d(P, *xy.reshape(2,-1)).reshape(shp) for P in (Px, Py)])

def polyval2d(m, x, y):
    """ From http://stackoverflow.com/a/7997925/874660
    """
    import itertools
    order = int(np.sqrt(len(m))) - 1
    ij = itertools.product(range(order+1), range(order+1))
    z = np.zeros_like(x)
    for a, (i,j) in zip(m, ij):
        z += a * x**i * y**j
    return z

################################################################################

class DummyPrinter(Printer):
    """ DummyPrinter lets you test some functionality without a printer connected.
    """
    def __init__(self):
        super(DummyPrinter, self).__init__(connect=False)
        self._laser_xypower = [0, 0, 0]
        self._blocks = dict()
        self._state = State.MACHINE_OFF

    def poll(self):
        raise NotImplementedError()

    def initialize(self):
        self._state = State.MACHINE_READY_TO_PRINT
        self._zpos_usteps = 0 # FIXME: Need to know where z starts.
        self._zcurrent = 40
        self._zspeed_usteps_per_s = 0
        self._tiltpos_usteps = 0
        self._tiltcurrent = 40
        self._tiltspeed_usteps_per_s = 0

    def shutdown(self):
        self._state = State.MACHINE_OFF

    def list_blocks(self):
        return self._blocks.keys()

    def delete_block(self, block, end=None):
        if end is None:
            end = block
        for i  in range(block, end+1):
            if i in self._blocks:
                del self._blocks[i]

    def read_block(self, block):
        return self._blocks[block]

    def block_size(self):
        return len(self._blocks[block])

    def _command(self, cmd, payload=b'', wait=True, expect_success=False):
        header = struct.Struct('<III')
        block, length, checksum = header.unpack(payload[:header.size])
        if cmd == Command.CMD_LOAD_PRINT_DATA_BLOCK:
            data = payload[header.size:]
            assert len(data) == length
            self._blocks[block] = data
        elif cmd == Command.CMD_MACHINE_STATE:
            return self._state
        elif cmd == Command.CMD_MOVE_Z_STEPPER_INCREMENTAL:
            s = struct.Struct('<iIB')
            steps, feedrate, current = s.unpack(payload[header.size:])
            self._zpos_usteps += steps
            self._zspeed_usteps_per_s = feedrate

    def set_laser_uint16(self, x, y, power=25000):
        """ Sets the position and laser power level
                x and y are unsigned 16-bit values (0 to 0xffff)
                    (with 0 at the corner of the platform)
                power is an unsigned 16-bit integer
            Setting power too high can damage your diode!
        """
        if self.AUDIT_LASER_POWER:
            # This raises if the power is too high:
            self.check_laser_ticks(power)
        self._laser_xypower = [x, y, power]

    def read_laser_table(self):
        return np.array([[0, 0, 0], [0.0, 0.0, 1.0], [0.1, 0.01, 2.0], [0.2, 0.01, 2.0], [0.3, 0.02, 3.0], [0.4, 0.02, 4.0], [0.5, 0.03, 6.0], [0.6, 0.03, 7.0], [0.7, 0.04, 8.0], [0.8, 0.06, 10.0], [0.9, 0.11, 12.0], [1.0, 1.16, 40.0], [1.1, 5.27, 144.0], [1.2, 9.37, 239.0], [1.3, 13.42, 339.0], [1.4, 17.68, 441.0], [1.5, 21.91, 543.0], [1.6, 26.08, 645.0], [1.7, 30.48, 747.0], [1.8, 34.73, 853.0], [1.9, 38.86, 958.0], [2.0, 43.18, 1061.0], [2.1, 47.67, 1169.0], [2.2, 51.93, 1276.0], [2.3, 56.1, 1381.0], [2.4, 60.61, 1489.0], [2.5, 65.06, 1589.0], [2.6, 69.01, 1702.0], [2.7, 73.45, 1798.0], [2.8, 77.69, 1907.0], [2.9, 82.51, 2021.0]])

    def read_grid_table(self):
        return np.array([[[ 2302, 2736], [ 2251, 17532], [ 2141, 32820], [ 1972, 47937], [ 1757, 62382]],
                         [[16833, 2212], [16744, 17245], [16608, 32800], [16420, 48168], [16207, 62848]],
                         [[32294, 2003], [32182, 17099], [32026, 32748], [31840, 48228], [31621, 62979]],
                         [[47858, 2131], [47740, 17142], [47592, 32705], [47406, 48093], [47146, 62737]],
                         [[62745, 2589], [62624, 17351], [62469, 32651], [62258, 47773], [62017, 62194]]])

################################################################################

from enum import Enum
class Response(Enum):
    """ Response codes returned by many commands
    """
    SUCCESS = 0
    ERROR_MALFORMED_REQUEST = 0x01
    ERROR_OUT_OF_MEMORY = 0x02

    ERROR_CRC_ERROR = 0x03
    ERROR_INPUT_VOLTAGE_TOO_LOW = 0x04
    ERROR_INPUT_VOLTAGE_TOO_HIGH = 0x05
    ERROR_COVER_OPEN = 0x06
    ERROR_PAUSE_BUTTON_PRESSED = 0x07
    ERROR_TIMEOUT_ON_Z_STEPPER_HOME = 0x08
    ERROR_ALREADY_PRINTING = 0x09
    ERROR_FAT = 0x10
    ERROR_COVER_CLOSE = 0x11

    STATUS_PRINT_STOPPED_DUE_TO_STOP = 0x12
    STATUS_PRINT_STOPPED_DUE_TO_ABORT = 0x13
    ERROR_NOT_PRINTING = 0x14
    STATUS_PRINTING_RESUMED_FROM_PAUSE = 0x15

    ERROR_INVALID_JOB = 0x16
    ERROR_SERIAL_WRITE_UNSUCCESSFUL = 0x17
    ERROR_INVALID_BLOCK_NUMBER = 0x18
    ERROR_PRINTER_OFF = 0x19
    ERROR_INVALID_MEMORY_ADDRESS = 0x1A
    ERROR_JOB_ALREADY_RUNNING = 0x1B
    ERROR_SD_CARD = 0x1C
    ERROR_LASER_ALREADY_CALIBRATING = 0x1D

    ERROR_FILE_NOT_FOUND = 0x1E
    ERROR_FILE_ALREADY_EXISTS = 0x1F
    ERROR_NOT_A_DIRECTORY = 0x20
    ERROR_NOT_A_FILE = 0x21
    ERROR_FILE_ERROR = 0x22

    ERROR_UNIMPLEMENTED = 0x97
    ERROR_MISC = 0x98
    ERROR_USB_TIMEOUT = 0x99


class Command(Enum):
    """ Big list of commands
    """
    CMD_MACHINE_INFORMATION  = 0x01
    CMD_INITIALIZE  = 0x02
    CMD_SHUTDOWN  = 0x03
    CMD_SET_TIME  = 0x04
    CMD_DROP_TO_BOOTLOADER  = 0x05
    CMD_PRINTER_STATUS  = 0x06
    CMD_MACHINE_STATE = 0x07
    CMD_REQUIRED_PREFORM_VERSION = 0x08
    CMD_READ_CPU_INFORMATION = 0x09

    CMD_JOB_START  = 0x10
    CMD_JOB_LOAD_BLOCK  = 0x11
    CMD_JOB_INFORMATION  = 0x12
    CMD_JOB_STOP  = 0x13

    CMD_LOAD_PRINT_DATA_BLOCK  = 0x20
    CMD_START_PRINTING  = 0x21
    CMD_BLOCK_INFORMATION  = 0x22
    CMD_DELETE_BLOCKS  = 0x23
    CMD_LIST_BLOCKS  = 0x24
    CMD_STOP_PRINTING  = 0x25
    CMD_PAUSE_PRINTING  = 0x26
    CMD_UNPAUSE_PRINTING  = 0x27
    CMD_READ_BLOCK  = 0x28
    CMD_READ_BLOCK_DATA  = 0x29
    CMD_FORMAT_SDCARD  = 0x2A

    CMD_MOVE_Z_STEPPER_INCREMENTAL  = 0x30
    CMD_MOVE_TILT_STEPPER_INCREMENTAL  = 0x31
    CMD_POSITION_LASER  = 0x32
    CMD_MOVE_Z_STEPPER_TO_LIMIT_SWITCH  = 0x33

    CMD_READ_LASER_TABLE  = 0x44
    CMD_READ_GRID_TABLE  = 0x45
    CMD_READ_ZSENSOR_HEIGHT  = 0x46

    CMD_WRITE_DIO  = 0x50
    CMD_READ_DIO  = 0x51
    CMD_READ_ADC_INPUT  = 0x52

    CMD_INIT_SD_STORAGE  = 0x60
    CMD_CLOSE_SD_STORAGE  = 0x61
    CMD_READ_FILE = 0x62
    CMD_WRITE_FILE = 0x63
    CMD_DELETE_FILE = 0x64
    CMD_CREATE_DIRECTORY = 0x65
    CMD_READ_DIRECTORY = 0x67
    CMD_DELETE_DIRECTORY = 0x66
    CMD_GET_FILE_INFORMATION = 0x68

    STATUS_LAYER_DONE  = 0x80
    STATUS_LAYER_NON_FATAL_ERROR  = 0x81
    STATUS_BLOCK_DONE  = 0x84
    STATUS_PRINT_DONE  = 0x82

    DEBUG_STRING  = 0x90

class State(Enum):
    MACHINE_OFF = 0
    MACHINE_POWERING_UP = 1
    MACHINE_RAISING_PLATFORM = 2
    MACHINE_READY_TO_PRINT = 3
    MACHINE_PRINTING = 4
    MACHINE_PRINTING_PAUSE_PENDING = 5
    MACHINE_PRINTING_PAUSED = 6
    MACHINE_STOPPING_PRINT = 7
    MACHINE_SHUTTING_DOWN = 8
    MACHINE_ERROR = 9
    MACHINE_HARD_ERROR = 10
    MACHINE_STATE_NONE = 11
