import os
import inspect
import unittest

from ott.loader.gtfs.cache import Cache
from ott.loader.gtfs.info import Info
from ott.loader.gtfs.diff import Diff

class TestGtfsDiff(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_diff_calendar(self):
        #import pdb; pdb.set_trace()
        this_module_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        gtfsA = os.path.join(this_module_dir, "gtfsA.zip")
        gtfsB = os.path.join(this_module_dir, "gtfsB.zip")
        d = Diff(gtfsA, gtfsB)
        self.assertTrue(d.is_different())
        pass

    def test_diff_info(self):
        this_module_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        gtfsA = os.path.join(this_module_dir, "gtfsB.zip")
        gtfsB = os.path.join(this_module_dir, "gtfsC.zip")
        d = Diff(gtfsA, gtfsB)
        self.assertTrue(d.is_different())
        pass

    def test_same(self):
        this_module_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        gtfsA = os.path.join(this_module_dir, "gtfsB.zip")
        gtfsB = os.path.join(this_module_dir, "gtfsB.zip")
        d = Diff(gtfsA, gtfsB)
        self.assertFalse(d.is_different())
        pass


class TestGtfsCache(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_cache(self):
        url="https://developers.google.com/transit/gtfs/examples/sample-feed.zip"
        name="google.zip"
        c = Cache(url, name)
        self.assertTrue(os.path.exists(c.file_path))

        i = c.get_info()
        fi = i.get_feed_date_range()
        fi_match = ('20070101', '20101231')
        self.assertEqual(fi, fi_match)


class TestGtfsInfo(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_basic_info(self):
        this_module_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        gtfsA = os.path.join(this_module_dir, "gtfsB.zip")

        i = Info(gtfsA)

        fi = i.get_feed_info()
        fi_match = ('20150927', '20160305', 'TriMet', '20150927-20151006-0140')
        self.assertEqual(fi, fi_match)

        fi = i.get_feed_date_range()
        fi_match = ('20070101', '20101231')
        self.assertEqual(fi, fi_match)

        fi = i.get_feed_version()
        fi_match = "20150927-20151006-0140"
        self.assertEqual(fi, fi_match)

        r = i.get_days_since_stats()
        self.assertTrue(r[0] > 3200)
        self.assertTrue(r[1] < -1750)
        self.assertTrue(i.is_gtfs_out_of_date())