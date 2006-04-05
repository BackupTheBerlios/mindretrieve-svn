import datetime
import sys
import unittest

from minds.safe_config import cfg as testcfg
from minds import upgrade_checker as uc


TEST_FEED1 = \
"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">

  <title>MindRetrieve Upgrade Notification</title>
  <link href="http://www.mindretrieve.net/"/>
  <id>http://www.mindretrieve.net/release/upgrade.xml</id>
  <updated>2006-03-29T04:43:40Z</updated>

  <entry>
    <title>Version 0.8.0</title>
    <id>http://www.mindretrieve.net/release/0.8.0</id>
    <updated>2006-01-18T17:00:00Z</updated>
    <modified>2006-01-18T17:00:00Z</modified>
    <link href="https://developer.berlios.de/project/showfiles.php?group_id=2905&amp;release_id=8737"/>
    <summary>New features added: web library, tag based categorization, etc</summary>
  </entry>

  <entry>
    <title>Version 0.4.2</title>
    <id>http://www.mindretrieve.net/release/0.4.2</id>
    <updated>2005-02-21T17:00:00Z</updated>
    <modified>2005-02-21T17:00:00Z</modified>
    <link href="https://developer.berlios.de/project/showfiles.php?group_id=2905&amp;release_id=4867"/>
    <summary>Maintenance release with minor enhancement</summary>
  </entry>

</feed>
"""

TEST_FEED0 = \
"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">

  <title>MindRetrieve Upgrade Notification</title>
  <link href="http://www.mindretrieve.net/"/>
  <id>http://www.mindretrieve.net/release/upgrade.xml</id>
  <updated>2006-03-29T04:43:40Z</updated>

  <entry>
    <title>Version 0.4.2</title>
    <id>http://www.mindretrieve.net/release/0.4.2</id>
    <updated>2005-02-21T17:00:00Z</updated>
    <modified>2005-02-21T17:00:00Z</modified>
    <link href="https://developer.berlios.de/project/showfiles.php?group_id=2905&amp;release_id=4867"/>
    <summary>Maintenance release with minor enhancement</summary>
  </entry>

</feed>
"""


class TestUpgrade(unittest.TestCase):

    def setUp(self):
        self.state = uc.State()
        self.state.fetch_date = datetime.date(2004,1,1)
        self.state.next_fetch = datetime.date(2005,1,1)


    def test_fetch(self):
        status, date, uinfo = uc._fetch('')
        self.assert_(not status)
        self.assert_(not date)
        self.assert_(not uinfo)

        status, date, uinfo = uc._fetch(TEST_FEED0)
        self.assertEqual(status,        'n/a')
        self.assertEqual(date,          '2005-02-21T17:00:00Z')
        self.assertEqual(uinfo.version, '0.4.2')
        self.assertEqual(uinfo.title,   'Version 0.4.2')
        self.assertEqual(uinfo.summary, 'Maintenance release with minor enhancement (2005-02-21)')
        self.assertEqual(uinfo.url,     'https://developer.berlios.de/project/showfiles.php?group_id=2905&release_id=4867')


    def test_checkUpgrade_failed_fetch(self):
        st = self.state
        today = datetime.date(2005,1,1)

        def _assert_failed_fetch(self, state):
            """ helper function """
            self.assertEqual(st.fetch_date, today)
            self.assertEqual(st.next_fetch, datetime.date(2005,1,2))
            self.assert_(not st.last_entry_date)
            self.assert_(not st.upgrade_info)

        uc._checkUpgrade(st, today, '')
        _assert_failed_fetch(self, st)

        uc._checkUpgrade(st, today, 'zz://xx/yy')   # bad URL
        _assert_failed_fetch(self, st)

        uc._checkUpgrade(st, today, '<?xml version="1.0" encoding="utf-8"?><a>aaa</a>')     #  irrelevant XML
        _assert_failed_fetch(self, st)

        uc._checkUpgrade(st, today, '<?xml version="1.0" encoding="utf-8"?><feed>x</wrong_feed>')     #  non-wellform XML
        _assert_failed_fetch(self, st)


    def test_checkUpgrade(self):
        st = self.state
        today = datetime.date(2005,1,1)

        # version 0.0
        st.current_version = '0.0'
        st.last_entry_date = ''
        st.feed_url = TEST_FEED0

        uc._checkUpgrade(st, today)             # got upgrade 0.4.2

        self.assertEqual(st.fetch_date, today)
        self.assertEqual(st.next_fetch, datetime.date(2005,1,11))
        self.assertEqual(st.last_entry_date, '2005-02-21T17:00:00Z')
        self.assert_(st.upgrade_info)

        uinfo = st.upgrade_info
        self.assertEqual(uinfo.version, '0.4.2')
        self.assertEqual(uinfo.title,   'Version 0.4.2')
        self.assertEqual(uinfo.summary, 'Maintenance release with minor enhancement (2005-02-21)')
        self.assertEqual(uinfo.url,     'https://developer.berlios.de/project/showfiles.php?group_id=2905&release_id=4867')

        uc.set_config(st, dismiss=True)         # reset upgrade_info

        # still version 0.0
        uc._checkUpgrade(st, today)             # got old news

        self.assertEqual(st.last_entry_date, '2005-02-21T17:00:00Z')
        self.assert_(not st.upgrade_info)

        # version 0.4.2
        st.current_version = '0.4.2'
        st.last_entry_date = ''
        st.feed_url = TEST_FEED0

        uc._checkUpgrade(st, today)             # no new version

        self.assertEqual(st.last_entry_date, '2005-02-21T17:00:00Z')
        self.assert_(not st.upgrade_info)

        # found latest 0.8.0
        st.current_version = '0.4.0'
        st.last_entry_date = ''
        st.feed_url = TEST_FEED1

        uc._checkUpgrade(st, today)             # new version 0.8.0 available!
        self.assertEqual(st.last_entry_date, '2006-01-18T17:00:00Z')
        self.assert_(st.upgrade_info)

        uinfo = st.upgrade_info
        self.assertEqual(uinfo.version, '0.8.0')
        self.assertEqual(uinfo.title,   'Version 0.8.0')
        self.assertEqual(uinfo.summary, 'New features added: web library, tag based categorization, etc (2006-01-18)')
        self.assertEqual(uinfo.url,     'https://developer.berlios.de/project/showfiles.php?group_id=2905&release_id=8737')


    def _test_poll(self, _date_func, expect_fetched, expected_version, force_check=False):
        st = self.state
        old_date = st.fetch_date

        # the main test
        print '%s current %s fetch -->' % (st.current_version, str(_date_func()))
        r = uc.pollUpgradeInfo(st, _date_func, force_check=force_check)

        if expect_fetched:
            self.assertNotEqual(st.fetch_date, old_date)    # expect fetched
        else:
            self.assertEqual(st.fetch_date, old_date)       # expect not fetched

        if expected_version:
            self.assertEqual(r.version, expected_version)   # expect has upgrade
        else:
            self.assert_(not r)                             # expect no upgrade


    def test_pollUpgradeInfo(self):

        def _date_func(y,m,d):
            # Helper to return a functional object
            # >>> date_func(2005,1,1)()
            # datetime.date(2005, 1, 1, 0, 0)
            return lambda: datetime.date(y,m,d)

        st = self.state
        st.current_version = '0.0'
        st.feed_url = TEST_FEED0

        self._test_poll(_date_func(2004,12,31), False, '')      # no fetch
        self._test_poll(_date_func(2005, 1, 1), True,  '0.4.2') # fetch 0.4.2
        self._test_poll(_date_func(2005, 1, 2), False, '0.4.2') # no fetch but still have upgrade 0.4.2

        uc.set_config(st, dismiss=True)                         # reset upgrade_info
        self._test_poll(_date_func(2005, 1, 3), False, '')      # dismissed, no fetch
        self._test_poll(_date_func(2005, 1,11), True,  '')      # fetch again, but nothing new

        st.feed_url = TEST_FEED1
        self._test_poll(_date_func(2005, 1,21), True,  '0.8.0') # fetch again, got 0.8.0

        uc.set_config(st, frequency=0)
        self._test_poll(_date_func(2005, 1,31), False, '')      # upgrade is off

        self._test_poll(_date_func(2005, 1,22), True,  '0.8.0', force_check=True)  # force_check

        uc.set_config(st, dismiss=True)                         # reset upgrade_info

        st.current_version = '9.9'
        self._test_poll(_date_func(2005, 1,23), True,  '', force_check=True)  # force_check but no new version

        self._test_poll(_date_func(2005, 2,10), False, '')      # regular feed after force feed (still disabled)

        uc.set_config(st, frequency=10)
        self._test_poll(_date_func(2005, 2,10), True, '')       # regular feed made after force feed


    def test_set_config(self):
        st = self.state
        st.upgrade_info = 'dummy'

        # set frequency
        uc.set_config(st, frequency=7)
        self.assertEqual(st.fetch_frequency, 7)
        self.assertEqual(st.next_fetch, datetime.date(2004,1,8))
        self.assert_(st.upgrade_info)

        # dismiss
        uc.set_config(st, dismiss=True)
        self.assertEqual(st.fetch_frequency, 7)
        self.assert_(not st.upgrade_info)


if __name__ =='__main__':
    unittest.main()