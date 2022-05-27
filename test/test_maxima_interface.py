import unittest
import os
import sys

sys.path.append(os.path.realpath(".."))
from maxima_interface import MaximaInterface


class TestMaximaInterface(unittest.TestCase):
    def setUp(self) -> None:
        self.mi = MaximaInterface()

    def tearDown(self) -> None:
        self.mi.close()

    def testRawCommand(self):
        result = self.mi.raw_command("a: 1;")
        result = self.mi.raw_command("a;")
        self.assertEqual("1", result)

    def testReset(self):
        result = self.mi.raw_command("a: 1;")
        self.mi.reset()
        result = self.mi.raw_command("a;")
        self.assertEqual("a", result)
