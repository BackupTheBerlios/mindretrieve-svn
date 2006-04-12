from datetime import datetime
import unittest

from minds.util import dateutil


class TestDateUtil(unittest.TestCase):

    def test_parse(self):
        self.assertEqual(dateutil.parse_iso8601_date('2003-09-15T10:34:54Z'), datetime(2003,9,15,10,34,54))
        self.assertEqual(dateutil.parse_iso8601_date('2003-09-15 10:34:54Z'), datetime(2003,9,15,10,34,54))
        self.assertEqual(dateutil.parse_iso8601_date('2003-09-15T10:34:54' ), datetime(2003,9,15,10,34,54))
        self.assertEqual(dateutil.parse_iso8601_date('20030915T103454'     ), datetime(2003,9,15,10,34,54))
        self.assertEqual(dateutil.parse_iso8601_date('2003-09-15'          ), datetime(2003,9,15, 0, 0, 0))
        self.assertEqual(dateutil.parse_iso8601_date('20030915'            ), datetime(2003,9,15, 0, 0, 0))

        self.assertRaises( ValueError, dateutil.parse_iso8601_date, '')
        self.assertRaises( ValueError, dateutil.parse_iso8601_date, '1234-06-18 12:34:56..')
        self.assertRaises( ValueError, dateutil.parse_iso8601_date, '1234/06/18 12:34:56')
        self.assertRaises( ValueError, dateutil.parse_iso8601_date, '1234-06-18 12.34.56')
        self.assertRaises( ValueError, dateutil.parse_iso8601_date, 'abcd-06-18 12:34:56')
        self.assertRaises( ValueError, dateutil.parse_iso8601_date, '9999-99-99 99:99:99')


    def test_isoformat(self):
        self.assertEqual(dateutil.isoformat(datetime(1234,6,18)),             '1234-06-18T00:00:00')
        self.assertEqual(dateutil.isoformat(datetime(1234,6,18,12,34,56)),    '1234-06-18T12:34:56')
        self.assertEqual(dateutil.isoformat(datetime(1234,6,18,12,34,56,78)), '1234-06-18T12:34:56')


if __name__ == '__main__':
    unittest.main()