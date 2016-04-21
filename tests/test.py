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

if __name__ == '__main__':
    unittest.main()
