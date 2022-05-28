import unittest
import pathlib
import os
import sys

dir_path = pathlib.Path(__file__).parent.resolve()
src_dir_path = pathlib.Path.joinpath(dir_path, "../src")
sys.path.append(str(src_dir_path))

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
