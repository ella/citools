from unittest import TestCase

from datetime import datetime

from citools.mongo import get_database_connection
from citools.git import get_last_revision

from helpers import MongoTestCase

class TestLastStoreRetrieval(MongoTestCase):

    def setUp(self):
        super(TestLastStoreRetrieval, self).setUp()
        self.collection = self.database['repository_information']

    def test_none_where_no_data_yet(self):
        self.assertEquals(None, get_last_revision(self.collection))

    def test_last_repository_retrieved(self):
        hash = '5ae35ebcbb0adc3660f0af891058e4e46dbdc14c'

        self.collection.insert({
            "hash_abbrev" : hash[0:16],
            "hash" : hash,
            "author_name" : "author_name",
            "author_email" : "author_email",
            "author_date" : datetime.now(),
            "commiter_name" : "commiter_name",
            "commiter_email" : "commiter_email",
            "commiter_date" : datetime.now(),
            "subject" : "subject",
        })
        self.assertEquals(hash, get_last_revision(self.collection))

