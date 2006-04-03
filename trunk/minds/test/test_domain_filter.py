"""
"""

import unittest

from minds.safe_config import cfg as testcfg
from minds import domain_filter


class TestDomainFilter(unittest.TestCase):

    def setUp(self):
        self.domain0 = testcfg.get('filter.domain.0', '')
        self.domain1 = testcfg.get('filter.domain.1', '')
        self.domain2 = testcfg.get('filter.domain.2', '')
        self.domain3 = testcfg.get('filter.domain.3', '')
        self.domain4 = testcfg.get('filter.domain.4', '')
        testcfg.set('filter.domain.0', '.xyz.com')           # domain start by '.'
        testcfg.set('filter.domain.1', ' abc.com , , def ')  # whitespaces, nothing between ,,
        testcfg.set('filter.domain.2', ',')                  # lone ,
        testcfg.set('filter.domain.3', '')                   # blank
        testcfg.set('filter.domain.4', '')


    def tearDown(self):
        testcfg.set('filter.domain.0', self.domain0)
        testcfg.set('filter.domain.1', self.domain1)
        testcfg.set('filter.domain.2', self.domain2)
        testcfg.set('filter.domain.3', self.domain3)
        testcfg.set('filter.domain.4', self.domain4)


    def testLoad0(self):
        testcfg.set('filter.domain.0', '')
        testcfg.set('filter.domain.1', '')
        testcfg.set('filter.domain.2', '')
        testcfg.set('filter.domain.3', '')
        testcfg.set('filter.domain.4', '')
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
        testcfg.set('filter.domain.0', '')
        testcfg.set('filter.domain.1', '')
        testcfg.set('filter.domain.2', '')
        testcfg.set('filter.domain.3', '')
        testcfg.set('filter.domain.4', '')
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