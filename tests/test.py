# -*- coding: utf-8 -*-

from context import FLP, Printer
import unittest

import numpy as np

class FLPTestSuite(unittest.TestCase):
    def test_makeFile(self):
        flp = FLP.Packets()
        flp.append(FLP.Dwell(1))
        from hashlib import sha224
        self.assertEqual(sha224(flp.tostring()).hexdigest(),
                         'fdd67607eea14ff08c1cbc8eaa1e840424911848275211fff21b6f01')
        self.checkTostringFromstring(flp)

    def checkTostringFromstring(self, flp):
        s = flp.tostring()
        flp1 = FLP.fromstring(s)
        self.assertEqual(flp, flp1)
        self.assertEqual(s, flp1.tostring())

class PrinterTestSuite(unittest.TestCase):
    def test_mm_to_galvo(self):
        p = Printer.DummyPrinter()
        self.assertTrue(np.all(p.mm_to_galvo([1,2,3], [3,2,1]) ==
                               [[ 33479.5,32987.25,32495.],[ 33227.44921875,33712.453125,34197.63671875]]))
        self.assertTrue(np.all(p.mm_to_galvo([0], [0]) == [[ 32026.],[ 32748.]]))
        self.assertTrue(np.all(p.mm_to_galvo(0, 0) == [32026., 32748.]))


class ExampleTestSuite(unittest.TestCase):
    def test_image_to_flp(self):
        image = np.array([[1, 0.5, 0],
                          [1, 1.0, 0],
                          [0,   0, 1]])
        from examples.image_to_laser_moves import image_to_laser_moves_xy_mm_dt_s_mW
        result = image_to_laser_moves_xy_mm_dt_s_mW(image, M=np.eye(3),
                                                    mmps=294, powerThreshold_mW=0.0,
                                                    doFilter=True,
                                                    max_seg_length_mm=5.0)
        self.assertEqual(result.shape, (9,4))
        reference = np.array([[  0.00000000e+00,   0.00000000e+00,   0.00000000e+00, 0.00000000e+00],
                              [ -5.00000000e-01,   0.00000000e+00,   1.70068027e-03, 0.00000000e+00],
                              [  5.00000000e-01,   0.00000000e+00,   1.70069011e-03, 1.00000000e+00],
                              [  1.50000000e+00,   0.00000000e+00,   5.10204410e-03, 5.00000000e-01],
                              [  1.50000000e+00,  -1.00000000e+00,   3.40136054e-03, 0.00000000e+00],
                              [ -5.00000000e-01,  -1.00000000e+00,   9.97080200e-03, 1.00000000e+00],
                              [  1.50000000e+00,  -2.00000000e+00,   7.60567339e-03, 0.00000000e+00],
                              [  2.50000000e+00,  -2.00000000e+00,   1.67687791e-02, 1.00000000e+00],
                              [  0.00000000e+00,   0.00000000e+00,   0.00000000e+00, 0.00000000e+00]])
        self.assertTrue(np.max(np.abs(result - reference)) < 1e-10)

if __name__ == '__main__':
    unittest.main()
