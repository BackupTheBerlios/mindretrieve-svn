"""
"""

import unittest

import pagemeter


class TestPageMeter(unittest.TestCase):

  def do_test(self, *args, **kargs):
    pm = pagemeter.PageMeter(*args)
    result = kargs['result']
    self.assertEqual(result, str(pm))


  def test0(self):
    self.do_test(  1,  0,10, result="Item 0-0/0 | prev None page 0/1 next None | Page <0-1> | page size 10")


  def test100(self):
    self.do_test( -1,100,10,2, result="Item 0-10/100 | prev None page 0/10 next 10 | Page <0-3> | page size 10")
    self.do_test(  0,100,10,2, result="Item 0-10/100 | prev None page 0/10 next 10 | Page <0-3> | page size 10")
    self.do_test(  5,100,10,2, result="Item 0-10/100 | prev None page 0/10 next 10 | Page <0-3> | page size 10")
    self.do_test(  9,100,10,2, result="Item 0-10/100 | prev None page 0/10 next 10 | Page <0-3> | page size 10")
    self.do_test( 10,100,10,2, result="Item 10-20/100 | prev 0 page 1/10 next 20 | Page <0-4> | page size 10")
    self.do_test( 50,100,10,2, result="Item 50-60/100 | prev 40 page 5/10 next 60 | Page <3-8> | page size 10")
    self.do_test( 99,100,10,2, result="Item 90-100/100 | prev 80 page 9/10 next None | Page <7-10> | page size 10")
    self.do_test(100,100,10,2, result="Item 90-100/100 | prev 80 page 9/10 next None | Page <7-10> | page size 10")


  def test105(self):
    self.do_test( -1,105,10,2, result="Item 0-10/105 | prev None page 0/11 next 10 | Page <0-3> | page size 10")
    self.do_test(  0,105,10,2, result="Item 0-10/105 | prev None page 0/11 next 10 | Page <0-3> | page size 10")
    self.do_test( 99,105,10,2, result="Item 90-100/105 | prev 80 page 9/11 next 100 | Page <7-11> | page size 10")
    self.do_test(100,105,10,2, result="Item 100-105/105 | prev 90 page 10/11 next None | Page <8-11> | page size 10")
    self.do_test(109,105,10,2, result="Item 100-105/105 | prev 90 page 10/11 next None | Page <8-11> | page size 10")
    self.do_test(110,105,10,2, result="Item 100-105/105 | prev 90 page 10/11 next None | Page <8-11> | page size 10")
    self.do_test(999,105,10,2, result="Item 100-105/105 | prev 90 page 10/11 next None | Page <8-11> | page size 10")


  def testError(self):
    self.assertRaises(ValueError, pagemeter.PageMeter, 1, -1, 10)     # negative total
    self.assertRaises(ValueError, pagemeter.PageMeter, 1, 10, 0)      # 0 page_size
    self.assertRaises(ValueError, pagemeter.PageMeter, 1, 10, 10,0)   # 0 page_window_size


if __name__ == '__main__':
    unittest.main()