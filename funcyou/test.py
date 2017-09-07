import unittest

from . import LAMBDA as _, Pipe

class Test(unittest.TestCase):
    def test_lambda(self):
        at = self.assertTrue

        at((_  <   1)(0))
        at((1  >   _)(0))
        at((-1 <   _)(0))
        at((_  <   1)(0))
        at((0  >=  _)(0))
        at((_  >=  0)(0))
        at((_  <=  0)(0))
        at((0  <=  _)(0))
        at((0  ==  _)(0))
        at((_  ==  0)(0))
        at((1  !=  _)(0))
        at((_  !=  1)(0))

        ae = self.assertEqual

        ae((_ * 2)(1), 2)
        ae((2 * _)(1), 2)
        ae((2 + _)(1), 3)
        ae((_ + 2)(1), 3)
        ae((_ - 1)(1), 0)
        ae((1 - _)(1), 0)
        ae((1 - _)(-1), 2)
        ae((5 // _)(2), 2)
        ae((_ // 2)(5), 2)
        ae((5 /  _)(2), 2.5)
        ae((_ /  2)(5), 2.5)

    def test_pipe(self):
        from itertools import product
        res = Pipe() | range(1,6) | product
        self.assertTrue(res(), product(range(1,6)))
