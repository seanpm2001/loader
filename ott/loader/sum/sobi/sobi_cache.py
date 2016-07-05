import os
import logging
log = logging.getLogger(__file__)

from ott.utils.cache_base import CacheBase


class SobiCache(CacheBase):
    """ cache a SOBI .json file
        @see http://socialbicycles.com/
    """
    url = None
    name = None
    file_name = None
    file_path = None
    solr_file_name = None
    solr_file_path = None

    def __init__(self):
        super(SobiCache, self).__init__(section='sobi')
        self.url = self.config.get('download_url')
        self.name = self.config.get('name')

        self.file_name = self.name + ".json"
        self.file_path = os.path.join(self.cache_dir, self.file_name)

        self.solr_file_name = self.name + "-solr.xml"
        self.solr_file_path = os.path.join(self.cache_dir, self.solr_file_name)

    def check_feed(self, force_update=False):
        ret_val = False
        ret_val = self.simple_cache_item_update(self.file_name, self.url, force_update)
        if ret_val:
            ret_val = self.to_solr()
        return ret_val

    def to_solr(self):
        '''
        '''
        success = False
        success = True
        return success
