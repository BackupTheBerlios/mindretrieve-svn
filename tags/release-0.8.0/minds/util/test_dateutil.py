from datetime import datetime
import unittest

from minds.util import dateutil


class TestDateUtil(unittest.TestCase):

    def test_parse(self):
        self.assertEqual(dateutil.parse_iso8601_date('1234-06-18'),           datetime(1234,6,18))
        self.assertEqual(dateutil.parse_iso8601_date('1234-06-18T12:34:56'),  datetime(1234,6,18,12,34,56))
        self.assertEqual(dateutil.parse_iso8601_date('1234-06-18T12:34:56Z'), datetime(1234,6,18,12,34,56))

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