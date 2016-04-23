""" Run build.py weekly (or daily) on the test maps servers (e.g., maps6 / maps10).  I will
    download the latest gtfs.zip file, check to see if it's newer than the last version
    I downloaded, and if so, build a new OTP Graph.

    @see deploy.py, which is a companion script that runs on the production servers, and
    deploys a new OTP graph into production.
"""

import os
import sys
import copy
import time
import logging
import datetime

from ott.utils import file_utils
from ott.utils.cache_base import CacheBase
from ott.loader.gtfs.cache import Cache
from ott.loader.osm.osm_cache import OsmCache
from ott.loader.gtfs.info  import Info
from ott.loader.otp.preflight.test_runner import TestRunner

# constants
GRAPH_NAME = "Graph.obj"
GRAPH_FAILD = GRAPH_NAME + "-failed-tests"
GRAPH_SIZE = 35000000
OSM_NAME   = "or-wa"
OSM_SIZE   = 5000000
VLOG_NAME  = "otp.v"
TEST_HTML  = "otp_report.html"
OTP_DOWNLOAD_URL="http://maven.conveyal.com.s3.amazonaws.com/org/opentripplanner/otp/0.19.0/otp-0.19.0-shaded.jar"


class Build(CacheBase):
    """ build an OTP graph
    """
    graph_path = None
    otp_path   = None
    gtfs_zip_files  = None

    graph_failed = GRAPH_FAILD
    graph_name = GRAPH_NAME
    graph_size = GRAPH_SIZE
    osm_name   = OSM_NAME
    osm_size   = OSM_SIZE
    vlog_name  = VLOG_NAME
    test_html  = TEST_HTML
    expire_days = 45

    def __init__(self, config=None, gtfs_zip_files=Cache.get_gtfs_feeds()):
        self.gtfs_zip_files = gtfs_zip_files
        file_utils.cd(self.cache_dir)
        self.graph_path = os.path.join(self.cache_dir, self.graph_name)
        self.otp_path = self.check_otp_jar()

    def build_and_test_graph(self, force_rebuild=False):
        ''' will rebuild the graph...
            :return: True for success ... fail for pass
        '''
        success = True

        # step 1: set some params
        rebuild_graph = force_rebuild

        # step 2: check graph file is fairly recent and properly sized
        if not file_utils.exists_and_sized(self.graph_path, self.graph_size, self.expire_days):
            rebuild_graph = True

        # step 3: check the cache files
        OsmCache.check_osm_file_against_cache(self.osm_name, self.cache_dir)
        if Cache.check_gtfs_files_against_cache(self.gtfs_zip_files, self.cache_dir):
            rebuild_graph = True

        # step 4: print feed info
        feed_details = self.get_gtfs_feed_details()

        # step 5: build graph is needed
        if rebuild_graph:
            success = False
            # step 5a: run the builder multiple times until we get a good looking Graph.obj
            for n in range(1, 21):
                logging.info(" build attempt {0} of a new graph ".format(n))
                self.run_graph_builder()
                time.sleep(10)
                if file_utils.exists_and_sized(self.graph_path, self.graph_size, self.expire_days):
                    success = True
                    break

            # step 5b: test the graph
            if success:
                self.deploy_test_graph()
                success = self.run_graph_te

                sts()
                if success:
                    self.update_vlog()
                    success = True
        return success

    def run_graph_builder(self):
        logging.info("building the graph")
        file_utils.rm(self.graph_path)
        file_utils.cd(self.this_module_dir)
        cmd='java -Xmx4096m -jar {} --build {} --cache {}'.format(self.otp_path, self.cache_dir, self.cache_dir)
        logging.info(cmd)
        os.system(cmd)

    def deploy_test_graph(self, port="8080"):
        ''' launch the server in a separate process ... then sleep for 75 seconds to give the server time to load the data '''
        from subprocess import Popen
        file_utils.cd(self.this_module_dir)
        cmd='java -Xmx4096m -jar {} --server --port {} --router "" --graphs {}'.format(self.otp_path, port, self.cache_dir)
        logging.info(cmd)
        try:
            Popen(cmd)
        except:
            os.system(cmd)
        time.sleep(75)

    def vizualize_graph(self):
        file_utils.cd(self.this_module_dir)
        cmd='java -Xmx4096m -jar {} --visualize --router "" --graphs {}'.format(self.otp_path, self.cache_dir)
        logging.info(cmd)
        os.system(cmd)

    def get_gtfs_feed_details(self):
        ''' returns updated [] with feed details
        '''
        ret_val = []
        try:
            for g in self.gtfs_zip_files:
                cp = copy.copy(g)
                gtfs_path = os.path.join(self.cache_dir, cp['name'])
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
        t.report(self.cache_dir)
        if t.has_errors():
            logging.info('GRAPH TESTS: There were errors!')
        else:
            logging.info('GRAPH TESTS: Nope, no errors')

    def mv_failed_graph_to_good(self):
        """ move the failed graph to prod graph name if prod graph doesn't exist and failed does exist
        """
        exists = os.path.exists(self.graph_path)
        if not exists:
            fail_path = os.path.join(self.cache_dir, self.graph_failed)
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
            vlog = os.path.join(self.cache_dir, self.vlog_name)
            f = open(vlog, 'a')
            f.write(msg)
            f.flush()
            f.close()

    def report_error(self, msg):
        ''' override me to do things like emailing error reports, etc... '''
        logging.error(msg)

    def check_otp_jar(self, jar="otp.jar", expected_size=50000000, download_url=OTP_DOWNLOAD_URL):
        """ make sure otp.jar exists ... if not, download it
            :return full-path to otp.jar
        """
        jar_path = os.path.join(self.this_module_dir, jar)
        exists = os.path.exists(jar_path)
        if not exists or file_utils.file_size(jar_path) < expected_size:
            file_utils.wget(download_url, jar_path)
        return jar_path

    @classmethod
    def factory(cls):
        return Build()

    @classmethod
    def options(cls, argv):
        b = cls.factory()
        if "mock" in argv:
            feed_details = b.get_gtfs_feed_details()
            b.update_vlog(feed_details)
            b.mv_failed_graph_to_good()
        elif "test" in argv:
            b.deploy_test_graph()
            b.run_graph_tests()
        elif "build" in argv:
            b.run_graph_builder()
            b.deploy_test_graph()
        elif "dep" in argv:
            b.deploy_test_graph()
        elif "viz" in argv:
            b.vizualize_graph()
        else:
            force = ("force" in argv or "rebuild" in argv)
            b.build_and_test_graph(force_rebuild=force)

def main(argv=sys.argv):
    import pdb; pdb.set_trace()
    Build.options(argv)

if __name__ == '__main__':
    main()
