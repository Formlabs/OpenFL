# -*- coding: utf-8 -*-

from context import FLP, Printer
import unittest

import numpy as np

class FLPTestSuite(unittest.TestCase):
    def test_makeFile(self):
        flp = FLP.Packets()
        flp.append(FLP.Dwell(1))

class PrinterTestSuite(unittest.TestCase):
    def test_mm_to_galvo(self):
        p = Printer.DummyPrinter()
        p.mm_to_galvo([1,2,3], [3,2,1])

if __name__ == '__main__':
    unittest.main()
