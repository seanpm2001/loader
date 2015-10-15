""" Run build.py weekly (or daily) on the test maps servers (e.g., maps6 / maps10).  I will
    download the latest gtfs.zip file, check to see if it's newer than the last version
    I downloaded, and if so, build a new OTP Graph.

    @see deploy.py, which is a companion script that runs on the production servers, and
    deploys a new OTP graph into production.
"""

import os
import inspect
import sys
import copy
import time
import traceback
import logging
import smtplib
import subprocess
import datetime

from ott.loader.gtfs.cache import Cache
from ott.loader.gtfs.info  import Info
from ott.loader.gtfs import utils as file_utils

from ott.loader.otp.tester.test_runner import TestRunner

# constants
GRAPH_NAME = "Graph.obj"
GRAPH_FAILD = GRAPH_NAME + "-failed-tests"
GRAPH_SIZE = 50000000
VLOG_NAME  = "otp.v"
TEST_HTML  = "otp_report.html"

class Build(object):
    """ build an OTP graph
    """
    this_module_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    graph_path = None

    build_cache_dir = None
    gtfs_zip_files = None

    graph_failed = GRAPH_FAILD
    graph_name = GRAPH_NAME
    graph_size = GRAPH_SIZE
    vlog_name  = VLOG_NAME
    test_html  = TEST_HTML
    graph_expire_days = 45

    def __init__(self, config=None, gtfs_zip_files=Cache.get_gtfs_feeds()):
        self.gtfs_zip_files = gtfs_zip_files
        self.build_cache_dir = self.get_build_cache_dir()
        file_utils.cd(self.build_cache_dir)
        self.graph_path = os.path.join(self.build_cache_dir, self.graph_name)

    def build_graph(self, force_rebuild=False):
        # step 1: set some params
        rebuild_graph = force_rebuild

        # step 2: check graph file is fairly recent and properly sized
        if not file_utils.exists_and_sized(self.graph_path, self.graph_size, self.graph_expire_days):
            rebuild_graph = True

        # step 3: check the cache files
        self.check_osm_cache_file()
        if self.check_gtfs_cache_files():
            rebuild_graph = True

        # step 4: print feed info
        feed_details = self.get_gtfs_feed_details()

        # step 5: build graph is needed
        if rebuild_graph and len(feed_details) > 0:
            logging.info("rebuilding the graph")
            jar = self.check_otp_jar()
            print jar
            self.deploy_graph()

    def report_error(self, msg):
        logging.error(msg)

    def deploy_graph(self):
        print "TBD"

    def check_otp_jar(self, jar="otp.jar", download_url="http://dev.opentripplanner.org/jars/otp-0.19.0-SNAPSHOT-shaded.jar"):
        """ make sure otp.jar exists ... if not, download it
            :return full-path to otp.jar
        """
        dir = self.this_module_dir
        jar_path = os.path.join(dir, jar)
        exists = os.path.exists(jar_path)
        if not exists or file_utils.file_size(jar_path) < self.graph_size:
            file_utils.wget(download_url, jar_path)
        return jar_path

    def check_osm_cache_file(self):
        ''' check the ott.loader.osm cache for any street data updates
        '''
        ret_val = False
        try:
        except Exception, e:
            logging.warn(e)
            self.report_error("OSM files are in a questionable state")
        return ret_val


    def check_gtfs_cache_files(self):
        ''' check the ott.loader.gtfs cache for any feed updates
        '''
        ret_val = False
        try:
            for g in self.gtfs_zip_files:
                url, name = Cache.get_url_filename(g)
                diff = Cache.cmp_file_to_cached(name, self.build_cache_dir)
                if diff.is_different():
                    Cache.cp_cached_gtfs_zip(name, self.build_cache_dir)
                    ret_val = True
        except Exception, e:
            logging.warn(e)
            self.report_error("GTFS files are in a questionable state")
        return ret_val

    def get_gtfs_feed_details(self):
        ''' returns updated [] with feed details
        '''
        ret_val = []
        try:
            for g in self.gtfs_zip_files:
                cp = copy.copy(g)
                gtfs_path = os.path.join(self.build_cache_dir, cp['name'])
                info = Info(gtfs_path)
                r = info.get_feed_date_range()
                v = info.get_feed_version()
                d = info.get_days_since_stats()
                cp['start'] = r[0]
                cp['end'] = r[1]
                cp['version'] = v
                cp['since'] = d[0]
                cp['until'] = d[1]
                ret_val.append(cp)
        except Exception, e:
            logging.warn(e)
            self.report_error("GTFS files are in a questionable state")
        return ret_val

    def run_graph_tests(self):
        ''' returns updated [] with feed details
        '''
        t = TestRunner()
        t.run()
        t.report(self.build_cache_dir)
        if t.has_errors():
            logging.info('GRAPH TESTS: There were errors!')
        else:
            logging.info('GRAPH TESTS: Nope, no errors')

    def mv_failed_graph_to_good(self):
        """ move the failed graph to prod graph name if prod graph doesn't exist and failed does exist
        """
        exists = os.path.exists(self.graph_path)
        if not exists:
            fail_path = os.path.join(self.build_cache_dir, self.graph_failed)
            exists = os.path.exists(fail_path)
            if exists:
                file_utils.mv(fail_path, self.graph_path)

    def update_vlog(self, feeds_details):
        """ print out gtfs feed(s) version numbers and dates to the otp.v log file
        """
        if feeds_details and len(feeds_details) > 0:
            msg = "\nUpdated graph on {} with GTFS feed(s):\n".format(datetime.datetime.now().strftime("%B %d, %Y @ %I:%M %p"))
            for f in feeds_details:
                msg += "  {} - date range {} to {} ({:>3} more calendar days), version {}\n".format(f['name'], f['start'], f['end'], f['until'], f['version'])
            vlog = os.path.join(self.build_cache_dir, self.vlog_name)
            f = open(vlog, 'a')
            f.write(msg)
            f.flush()
            f.close()

    def get_build_cache_dir(self, def_name="cache"):
        ''' returns either dir
        '''
        ret_val = os.path.join(self.this_module_dir, def_name)
        file_utils.mkdir(ret_val)
        return ret_val

    @classmethod
    def factory(cls):
        return Build()

    @classmethod
    def options(cls, argv):
        b = cls.factory()
        if "mock" in argv:
            #import pdb; pdb.set_trace()
            feed_details = b.get_gtfs_feed_details()
            b.update_vlog(feed_details)
            b.mv_failed_graph_to_good()
        elif "tests" in argv:
            b.run_graph_tests()
        else:
            b.build_graph()

def main(argv):
    Build.options(argv)

if __name__ == '__main__':
    main(sys.argv)
