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
        self.state.current_version = '0.4.2'


    def test_fetch(self):
        status, date, uinfo = uc._fetch(TEST_FEED0)
        self.assertEqual(status,        'n/a')
        self.assertEqual(date,          '2005-02-21T17:00:00Z')
        self.assertEqual(uinfo.version, '0.4.2')
        self.assertEqual(uinfo.title,   'Version 0.4.2')
        self.assertEqual(uinfo.summary, 'Maintenance release with minor enhancement')
        self.assertEqual(uinfo.url,     'https://developer.berlios.de/project/showfiles.php?group_id=2905&release_id=4867')


    def test_checkUpgrade_failed_fetch(self):
        st = self.state
        today = datetime.date(2005,1,1)

        uc._checkUpgrade(st, today, None)   # None simulate a failed feed

        self.assertEqual(st.fetch_date, today)
        self.assertEqual(st.next_fetch, datetime.date(2005,1,2))
        self.assert_(not st.last_entry_date)
        self.assert_(not st.upgrade_info)


    def test_checkUpgrade(self):
        st = self.state
        today = datetime.date(2005,1,1)

        uc._checkUpgrade(st, today, TEST_FEED0) # expect nothing newer than 0.4.0

        self.assertEqual(st.fetch_date, today)
        self.assertEqual(st.next_fetch, datetime.date(2005,1,11))
        self.assertEqual(st.last_entry_date, '2005-02-21T17:00:00Z')
        self.assert_(not st.upgrade_info)

        st.current_version = '0.0'
        st.last_entry_date = ''

        uc._checkUpgrade(st, today, TEST_FEED0) # rewind & retry

        self.assertEqual(st.fetch_date, today)
        self.assertEqual(st.next_fetch, datetime.date(2005,1,11))
        self.assertEqual(st.last_entry_date, '2005-02-21T17:00:00Z')
        self.assert_(st.upgrade_info)           # got an upgrade!

        uinfo = st.upgrade_info
        self.assertEqual(uinfo.version, '0.4.2')
        self.assertEqual(uinfo.title,   'Version 0.4.2')
        self.assertEqual(uinfo.summary, 'Maintenance release with minor enhancement')
        self.assertEqual(uinfo.url,     'https://developer.berlios.de/project/showfiles.php?group_id=2905&release_id=4867')

        uc.set_config(st, dismiss=True)         # reset upgrade_info
        self.assert_(not st.upgrade_info)

        uc._checkUpgrade(st, today, TEST_FEED0) # expect no newer entry

        self.assertEqual(st.last_entry_date, '2005-02-21T17:00:00Z')
        self.assert_(not st.upgrade_info)

        uc._checkUpgrade(st, today, TEST_FEED1) # new version 0.8.0 available!
        self.assertEqual(st.last_entry_date, '2006-01-18T17:00:00Z')
        self.assert_(st.upgrade_info)

        uinfo = st.upgrade_info
        self.assertEqual(uinfo.version, '0.8.0')
        self.assertEqual(uinfo.title,   'Version 0.8.0')
        self.assertEqual(uinfo.summary, 'New features added: web library, tag based categorization, etc')
        self.assertEqual(uinfo.url,     'https://developer.berlios.de/project/showfiles.php?group_id=2905&release_id=8737')


    def test_pollUpgradeInfo(self):

        st = self.state
        st.current_version = '0.0'

        def _date_func(y,m,d):
            # Helper to return a functional object
            # >>> date_func(2005,1,1)()
            # datetime.date(2005, 1, 1, 0, 0)
            return lambda: datetime.date(y,m,d)

        old_date = st.fetch_date
        r = uc.pollUpgradeInfo(st, _date_func(2004,12,31), TEST_FEED0)  # no fetch
        self.assertEqual(st.fetch_date, old_date)
        self.assert_(not r)

        r = uc.pollUpgradeInfo(st, _date_func(2005,1,1), TEST_FEED0)    # fetch 0.4.2
        self.assert_(st.fetch_date > old_date)
        self.assertEqual(r.version, '0.4.2')

        old_date = st.fetch_date
        r = uc.pollUpgradeInfo(st, _date_func(2005,1,2), TEST_FEED0)    # no fetch but still have upgrade 0.4.2
        self.assertEqual(st.fetch_date, old_date)
        self.assertEqual(r.version, '0.4.2')

        uc.set_config(st, dismiss=True)         # reset upgrade_info

        r = uc.pollUpgradeInfo(st, _date_func(2005,1,11), TEST_FEED0)   # fetch again, but nothing new
        self.assert_(st.fetch_date > old_date)
        self.assert_(not r)

        r = uc.pollUpgradeInfo(st, _date_func(2005,1,21), TEST_FEED1)   # fetch again, got 0.8.0
        self.assert_(st.fetch_date > old_date)
        self.assertEqual(r.version, '0.8.0')

        st.fetch_frequency = 0
        old_date = st.fetch_date
        r = uc.pollUpgradeInfo(st, _date_func(2005,1,31), TEST_FEED1)   # upgrade is off
        self.assertEqual(st.fetch_date, old_date)
        self.assert_(not r)


    def test_set_config(self):
        st = self.state
        st.upgrade_info = 'dummy'

        uc.set_config(st, frequency=7)
        self.assertEqual(st.fetch_frequency, 7)
        self.assert_(st.upgrade_info)

        uc.set_config(st, dismiss=True)
        self.assertEqual(st.fetch_frequency, 7)
        self.assert_(not st.upgrade_info)


    def test_persistence(self):
        self.fail()



if __name__ =='__main__':
    unittest.main()