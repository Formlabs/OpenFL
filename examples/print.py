#!/usr/bin/env python
"""
This is a Python script that prints an FLP
"""

import OpenFL.Printer as P

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Print a .flp")
    parser.add_argument('input', metavar='input', type=str,
                        help='source flp file')
    args = parser.parse_args()

    p = P.Printer()
    p.initialize()
    p.write_block(0, args.input)
    p.start_printing(0)
