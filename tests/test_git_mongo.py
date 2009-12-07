from datetime import datetime

from citools.git import get_last_revision, store_repository_metadata

from copy import deepcopy
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

class TestLastStoreRetrieval(MongoTestCase):

    def setUp(self):
        super(TestLastStoreRetrieval, self).setUp()
        self.collection = self.database['repository_information']
        hash = '5ae35ebcbb0adc3660f0af891058e4e46dbdc14c'
        self.changeset = {
            "hash_abbrev" : hash[0:16],
            "hash" : hash,
            "author_name" : "author_name",
            "author_email" : "author_email",
            "author_date" : datetime.now(),
            "commiter_name" : "commiter_name",
            "commiter_email" : "commiter_email",
            "commiter_date" : datetime.now(),
            "subject" : "subject",
        }

    def test_proper_changeset_stored(self):
        store_repository_metadata(self.collection, [self.changeset])

        self.assertEquals(self.changeset['hash_abbrev'], self.collection.find_one({
            'hash_abbrev' : self.changeset['hash_abbrev']
        })['hash_abbrev'])

    def test_storing_without_hash_fails(self):
        del self.changeset['hash']
        self.assertRaises(ValueError, store_repository_metadata, self.collection, [self.changeset])

    def test_storing_one_changeset_two_times_updates_data(self):
        self.new_changeset = deepcopy(self.changeset)
        self.new_changeset['commiter_name'] = 'overrulled'

        store_repository_metadata(self.collection, [self.changeset])
        store_repository_metadata(self.collection, [self.new_changeset])

        self.assertEquals('overrulled', self.collection.find_one({
            'hash_abbrev' : self.changeset['hash_abbrev']
        })['commiter_name'])
