"""
"""

import unittest

from config_help import cfg
from minds import domain_filter


class TestDomainFilter(unittest.TestCase):

    def setUp(self):
        self.domain0 = cfg.set('filter.domain.0', '')
        self.domain1 = cfg.set('filter.domain.1', '')
        self.domain2 = cfg.set('filter.domain.2', '')
        self.domain3 = cfg.set('filter.domain.3', '')
        self.domain4 = cfg.set('filter.domain.4', '')
        cfg.set('filter.domain.0', '.xyz.com')           # domain start by '.'
        cfg.set('filter.domain.1', ' abc.com , , def ')  # whitespaces, nothing between ,,
        cfg.set('filter.domain.2', ',')                  # lone ,
        cfg.set('filter.domain.3', '')                   # blank
        cfg.set('filter.domain.4', '')


    def tearDown(self):
        cfg.set('filter.domain.0', self.domain0)
        cfg.set('filter.domain.1', self.domain1)
        cfg.set('filter.domain.2', self.domain2)
        cfg.set('filter.domain.3', self.domain3)
        cfg.set('filter.domain.4', self.domain4)


    def testLoad0(self):
        cfg.set('filter.domain.0', '')
        cfg.set('filter.domain.1', '')
        cfg.set('filter.domain.2', '')
        cfg.set('filter.domain.3', '')
        cfg.set('filter.domain.4', '')
        domain_filter.load()
        self.assertEqual(0, len(domain_filter.g_exdm))


    def testLoad(self):
        domain_filter.load()
        exdms = domain_filter.g_exdm
        self.assertEqual(3, len(exdms))
        self.assert_('.xyz.com' in exdms)
        self.assert_('abc.com' in exdms)
        self.assert_('def' in exdms)


    def testFilter0(self):
        cfg.set('filter.domain.0', '')
        cfg.set('filter.domain.1', '')
        cfg.set('filter.domain.2', '')
        cfg.set('filter.domain.3', '')
        cfg.set('filter.domain.4', '')
        domain_filter.g_exdm = None                                 # force reload
        self.assertEqual(None, domain_filter.match(''))
        self.assertEqual(None, domain_filter.match('http://abc'))


    def testFilter1(self):
        domain_filter.g_exdm = None                                 # force reload

        self.assertEqual(None,       domain_filter.match(''))

        # exact domain match
        self.assertEqual('abc.com',  domain_filter.match('http://abc.com/'))
        self.assertEqual(None,       domain_filter.match('http://www.abc.com/'))
        self.assertEqual('abc.com',  domain_filter.match('http://abc.com/index.html?a=b#c'))
        self.assertEqual('abc.com',  domain_filter.match('http://u:p@abc.com/index.html?a=b#c'))
        self.assertEqual('def',      domain_filter.match('http://def/'))
        self.assertEqual(None,       domain_filter.match('http://www.def.com/'))

        # suffix domain match
        self.assertEqual(None,       domain_filter.match('http://xyz.com/'))
        self.assertEqual('.xyz.com', domain_filter.match('http://www.xyz.com/'))
        self.assertEqual('.xyz.com', domain_filter.match('http://www.xyz.com/index.html?a=b#c'))
        self.assertEqual('.xyz.com', domain_filter.match('http://u:p@www.xyz.com/index.html?a=b#c'))


if __name__ == '__main__':
    unittest.main()